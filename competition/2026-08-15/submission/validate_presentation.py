#!/usr/bin/env python3
"""Validate the AgentFit preliminary presentation deliverables."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pptx import Presentation
from pypdf import PdfReader


EXPECTED_SLIDES = 17
REQUIRED_TERMS = (
    "AgentFit",
    "AgentTeams",
    "EngagementLead",
    "BusinessEngineer",
    "AgentArchitect",
    "ValidationEngineer",
    "GovernanceAuditor",
    "Agentless",
    "Agent Architecture Search",
    "Human",
    "Skill",
    "MCP",
    "上下文",
    "验证",
    "安全",
    "开放",
    "未实现",
    "证据待补",
    "用户反馈定位",
    "官网参考案例",
    "零人工运维",
    "智能客服自主闭环",
    "软件研发全流程协同",
    "金融风控与理赔自动化",
    "设计模拟",
    "非运行证据",
    "requires_runtime_trial",
    "https://goaihz.com/tracks?track=infra",
    "Sample",
    "TaskSample",
    "Episode",
    "七层 ML 映射",
    "同一冻结样本集",
)
FORBIDDEN_TERMS = (
    "TODO",
    "TBD",
    "已验证 Meta-learning",
    "ImageNet 75%",
    "90%+",
    "超越人工设计 1.2%",
    "methodology §13",
    "首个真实项目案例与五元 Agent 在 AgentTeams 上的闭环正在实施",
    "六层 ML 映射",
)


def _shape_text(shape: object) -> list[str]:
    texts: list[str] = []
    if getattr(shape, "has_text_frame", False):
        texts.append(shape.text)
    if getattr(shape, "has_table", False):
        for row in shape.table.rows:
            for cell in row.cells:
                texts.append(cell.text)
    return texts


def _slide_text(slide: object) -> str:
    return "\n".join(
        text
        for shape in slide.shapes
        for text in _shape_text(shape)
        if text.strip()
    )


def validate(pptx_path: Path, pdf_path: Path | None = None) -> list[str]:
    """Return human-readable validation errors; an empty list means success."""

    errors: list[str] = []
    if not pptx_path.is_file():
        return [f"PPTX file does not exist: {pptx_path}"]

    try:
        presentation = Presentation(pptx_path)
    except Exception as exc:  # pragma: no cover - parser diagnostics vary
        return [f"Unable to read PPTX {pptx_path}: {exc}"]

    slide_count = len(presentation.slides)
    if slide_count != EXPECTED_SLIDES:
        errors.append(
            f"PPTX must contain exactly {EXPECTED_SLIDES} slides; found {slide_count}"
        )

    slide_texts = [_slide_text(slide) for slide in presentation.slides]
    for index, text in enumerate(slide_texts, start=1):
        if not text.strip():
            errors.append(f"PPTX slide {index} is empty")

    deck_text = "\n".join(slide_texts)
    for term in REQUIRED_TERMS:
        if term not in deck_text:
            errors.append(f"PPTX is missing required term: {term}")
    for term in FORBIDDEN_TERMS:
        if term in deck_text:
            errors.append(f"PPTX contains forbidden term: {term}")

    if pdf_path is not None:
        if not pdf_path.is_file():
            errors.append(f"PDF file does not exist: {pdf_path}")
        else:
            try:
                pdf_pages = len(PdfReader(pdf_path).pages)
            except Exception as exc:  # pragma: no cover - parser diagnostics vary
                errors.append(f"Unable to read PDF {pdf_path}: {exc}")
            else:
                if pdf_pages != EXPECTED_SLIDES:
                    errors.append(
                        f"PDF must contain exactly {EXPECTED_SLIDES} pages; found {pdf_pages}"
                    )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate AgentFit preliminary PPTX and optional PDF."
    )
    parser.add_argument("pptx", type=Path, help="Path to the PPTX file")
    parser.add_argument("pdf", type=Path, nargs="?", help="Optional PDF export")
    args = parser.parse_args()

    errors = validate(args.pptx, args.pdf)
    if errors:
        print("VALIDATION_FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    presentation = Presentation(args.pptx)
    print(f"pptx_pages={len(presentation.slides)}")
    if args.pdf is not None:
        print(f"pdf_pages={len(PdfReader(args.pdf).pages)}")
    print("content_checks=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
