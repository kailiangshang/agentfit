"""Project Dossier — append-only project state.

The single source of truth. Chat is not state; only structured writes
to the Dossier are formal state. (Design doc principle #6)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import copy
import json


@dataclass
class DossierEntry:
    timestamp: str
    stage: str
    agent: str
    action: str
    data: dict[str, Any]


class ProjectDossier:
    def __init__(self, project_id: str, domain: str = "general"):
        self.project_id = project_id
        self.domain = domain
        self.version = 0
        self.log: list[DossierEntry] = []
        self.snapshot: dict[str, Any] = {
            "project_id": project_id,
            "domain": domain,
            "materials": [],
            "facts": [],
            "automation_boundary": {},
            "candidates": [],
            "trial_spec": None,
            "trial_results": {},
            "evaluation_report": None,
            "final_decision": None,
            "assets_produced": [],
        }

    def write(self, stage: str, agent: str, action: str, data: dict[str, Any]) -> None:
        self.version += 1
        entry = DossierEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage=stage,
            agent=agent,
            action=action,
            data=copy.deepcopy(data),
        )
        self.log.append(entry)

        if action == "register_materials":
            self.snapshot["materials"].extend(data.get("materials", []))
        elif action == "write_facts":
            self.snapshot["facts"].extend(data.get("facts", []))
        elif action == "write_boundary":
            self.snapshot["automation_boundary"] = data.get("boundary", {})
        elif action == "write_candidates":
            self.snapshot["candidates"] = data.get("candidates", [])
        elif action == "write_trial_spec":
            self.snapshot["trial_spec"] = data.get("trial_spec")
        elif action == "write_trial_results":
            self.snapshot["trial_results"].update(data.get("results", {}))
        elif action == "write_evaluation":
            self.snapshot["evaluation_report"] = data.get("report")
        elif action == "write_decision":
            self.snapshot["final_decision"] = data.get("decision")
        elif action == "write_assets":
            self.snapshot["assets_produced"].extend(data.get("assets", []))

    def get(self, key: str) -> Any:
        return self.snapshot.get(key)

    def summary(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "domain": self.domain,
            "version": self.version,
            "entries": len(self.log),
            "materials_count": len(self.snapshot["materials"]),
            "facts_count": len(self.snapshot["facts"]),
            "candidates_count": len(self.snapshot["candidates"]),
            "has_trial_spec": self.snapshot["trial_spec"] is not None,
            "trial_results_count": len(self.snapshot["trial_results"]),
            "has_evaluation": self.snapshot["evaluation_report"] is not None,
            "final_decision": self.snapshot["final_decision"],
        }

    def trace_dump(self) -> list[dict]:
        return [
            {
                "ts": e.timestamp,
                "stage": e.stage,
                "agent": e.agent,
                "action": e.action,
            }
            for e in self.log
        ]
