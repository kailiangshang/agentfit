#!/usr/bin/env python3
"""Compile the HTML-first AgentFit scoreline-v2 deck into editable PPTX shapes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches


ROOT = Path(__file__).resolve().parent
SLIDES_DIR = ROOT / "slides"
OUTPUT_PATH = ROOT / "agentfit-scoreline-v2.pptx"
EXPECTED_SLIDES = 17
DEFAULT_DECK_SKILL = Path.home() / "workspace/.codex-home/skills/hands-on-deck"
DECK_SKILL = Path(os.environ.get("HANDS_ON_DECK_DIR", DEFAULT_DECK_SKILL))
HTML2PATCH = DECK_SKILL / "scripts/html2patch.py"
DECK = DECK_SKILL / "scripts/deck.py"


def _run(*args: str | Path) -> None:
    subprocess.run([str(arg) for arg in args], check=True, cwd=ROOT.parents[3])


def _make_base(path: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)
    presentation.save(path)


def build_deck(output_path: Path = OUTPUT_PATH) -> None:
    slide_files = sorted(SLIDES_DIR.glob("[0-9][0-9]-*.html"))
    if len(slide_files) != EXPECTED_SLIDES:
        raise RuntimeError(
            f"expected {EXPECTED_SLIDES} HTML slides, found {len(slide_files)}"
        )
    for tool in (HTML2PATCH, DECK):
        if not tool.is_file():
            raise FileNotFoundError(
                f"missing hands-on-deck tool: {tool}; set HANDS_ON_DECK_DIR to its skill directory"
            )

    with tempfile.TemporaryDirectory(prefix="scoreline-v2-pptx-") as temp_dir:
        temp = Path(temp_dir)
        base = temp / "base.pptx"
        patch = temp / "slides.patch.json"
        _make_base(base)

        _run(
            sys.executable,
            HTML2PATCH,
            *slide_files,
            "--deck",
            base,
            "--layout",
            "Blank",
            "--strict",
            "-o",
            patch,
        )

        payload = json.loads(patch.read_text(encoding="utf-8"))
        payload["ops"].append(
            {
                "op": "set-props",
                "title": "AgentFit 评分主线版（scoreline-v2）",
                "subject": "OpsPilot baseline 作首个 ProjectCase 的方案选择路演",
                "author": "AgentFit Team",
                "keywords": "AgentFit, AgentTeams, OpsPilot, scoreline-v2, HTML-first",
                "comments": "Alternative comparison deck. OpsPilot baseline is a code-level audited reference and first ProjectCase input, not AgentFit runtime evidence.",
            }
        )
        patch.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        _run(sys.executable, DECK, base, "apply", patch, "-o", output_path)

    print(f"generated={output_path}")


if __name__ == "__main__":
    build_deck()
