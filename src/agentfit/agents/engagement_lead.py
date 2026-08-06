"""EngagementLead — Agent project delivery lead.

Responsibilities: user interaction, project state, task decomposition,
coordination, and approval gate management.

Does NOT: design candidate solutions, modify evaluation results.
"""

from __future__ import annotations

from typing import Any


class EngagementLead:
    name = "EngagementLead"
    role = "Agent Project Delivery Lead"

    def intake(self, materials: list[dict], problem: str, dossier) -> dict:
        registered = []
        for m in materials:
            entry = {
                "ref": f"material-{len(dossier.get('materials')) + 1}",
                "type": m.get("type", "document"),
                "description": m.get("description", ""),
                "content_ref": m.get("content_ref", ""),
            }
            registered.append(entry)

        dossier.write("intake", self.name, "register_materials", {
            "materials": registered,
            "problem": problem,
        })

        gaps = self._identify_gaps(materials, problem)
        if gaps:
            dossier.write("intake", self.name, "identify_gaps", {"gaps": gaps})

        return {"registered": len(registered), "gaps": gaps}

    def approve_trial(self, trial_spec, dossier) -> bool:
        complexity = trial_spec.complexity_budget
        fault_count = len(trial_spec.fault_plan)
        risk_level = "low" if complexity < 20 and fault_count == 0 else "moderate"

        dossier.write("approve", self.name, "trial_approval", {
            "approved": True,
            "risk_level": risk_level,
            "complexity_budget": complexity,
        })
        return True

    def confirm_delivery(self, recommendation: str, dossier) -> str:
        decision = "accepted" if "Select" in recommendation or "deploy" in recommendation.lower() else "rejected"
        dossier.write("deliver", self.name, "write_decision", {
            "decision": decision,
            "recommendation": recommendation,
        })
        return decision

    def _identify_gaps(self, materials: list[dict], problem: str) -> list[str]:
        gaps = []
        has_examples = any(m.get("type") == "examples" for m in materials)
        has_policy = any(m.get("type") == "policy" for m in materials)
        if not has_examples:
            gaps.append("Missing labeled examples for evaluation")
        if not has_policy:
            gaps.append("Missing policy/rules documentation")
        return gaps
