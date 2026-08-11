#!/usr/bin/env python3
"""Validate the AgentFit preliminary presentation deliverables."""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from xml.etree import ElementTree
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pypdf import PdfReader


EXPECTED_SLIDES = 17
EXPECTED_PAGE_TITLES = (
    "Agent 架构不该靠猜。",
    "企业不知道的，不只是“用几个 Agent”",
    "平台提供砖块，但企业仍缺一位建筑师",
    "AgentFit 先定义样本，再编译任务和方案",
    "无、单、多 Agent 是同一个搜索空间",
    "最简单的合格者获胜",
    "五个元 Agent 把方案选择变成责任闭环",
    "AgentTeams 让团队运行，AgentFit 负责选对方案",
    "不同行业，共用一种方案决策方法",
    "最终交付的不是 Prompt，而是可验收方案包",
    "方法已经收敛，真实运行证据仍待补",
    "Fit：刚刚好，不多不少",
    "七层 ML 映射把“方案设计”变成可优化对象",
    "五个 Agent 各自拥有判断权、状态边界与责任产物",
    "七个 Skill 固化方案工程；MCP 只承接确定性接口",
    "高风险动作先审批；异常必须能停止、降级和回滚",
    "开放计划与当前事实分开披露",
)
SLIDE_REQUIRED_TERMS = {
    4: (
        "AgentFit 先定义样本，再编译任务和方案",
        "同一冻结样本集",
    ),
    6: (
        "同一冻结 SampleSetManifest",
        "同一版本化 TaskSample",
    ),
    7: (
        "候选冻结后，仅 GovernanceAuditor 消费 sealed-holdout 结果",
        "候选前冻结 Sample/Task · 候选后批准 TrialSpec",
        "TaskSample",
        "Episode",
    ),
    13: (
        "L1 样本语义",
        "L7 跨项目学习",
    ),
}
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

PRESENTATIONML_NAMESPACE = "http://schemas.openxmlformats.org/presentationml/2006/main"
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


def _iter_shapes(shapes: object):
    for shape in shapes:
        yield shape
        nested_shapes = getattr(shape, "shapes", None)
        if nested_shapes is not None:
            yield from _iter_shapes(nested_shapes)


def _slide_text(slide: object) -> str:
    return "\n".join(
        text
        for shape in _iter_shapes(slide.shapes)
        for text in _shape_text(shape)
        if text.strip()
    )


def _normalized(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _has_visible_native_content(
    slide: object, slide_width: int, slide_height: int
) -> bool:
    for shape in _iter_shapes(slide.shapes):
        if shape.shape_type in (MSO_SHAPE_TYPE.PICTURE, MSO_SHAPE_TYPE.MEDIA):
            continue
        left = getattr(shape, "left", 0)
        top = getattr(shape, "top", 0)
        width = getattr(shape, "width", 0)
        height = getattr(shape, "height", 0)
        if width <= 0 or height <= 0:
            continue
        if left >= slide_width or top >= slide_height:
            continue
        if left + width <= 0 or top + height <= 0:
            continue
        if any(_normalized(text) for text in _shape_text(shape)):
            return True
    return False


def _package_editability_errors(pptx_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        with zipfile.ZipFile(pptx_path) as package:
            media = sorted(
                name
                for name in package.namelist()
                if name.startswith("ppt/media/") and not name.endswith("/")
            )
            for name in media:
                errors.append(f"PPTX package contains embedded media: {name}")

            for slide_number in range(1, EXPECTED_SLIDES + 1):
                member = f"ppt/slides/slide{slide_number}.xml"
                if member not in package.namelist():
                    continue
                root = ElementTree.fromstring(package.read(member))
                transition = root.find(
                    f"{{{PRESENTATIONML_NAMESPACE}}}transition"
                )
                if transition is not None:
                    errors.append(f"PPTX slide {slide_number} contains a transition")
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        errors.append(f"Unable to inspect PPTX package {pptx_path}: {exc}")
    return errors


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
    for index, (slide, text) in enumerate(
        zip(presentation.slides, slide_texts), start=1
    ):
        if not text.strip():
            errors.append(f"PPTX slide {index} is empty")
        if not _has_visible_native_content(
            slide, presentation.slide_width, presentation.slide_height
        ):
            errors.append(
                f"PPTX slide {index} has no visible native text/content shape"
            )
        for shape in _iter_shapes(slide.shapes):
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                errors.append(f"PPTX slide {index} contains a picture/raster shape")
            elif shape.shape_type == MSO_SHAPE_TYPE.MEDIA:
                errors.append(f"PPTX slide {index} contains a media shape")

        if index <= len(EXPECTED_PAGE_TITLES):
            title = EXPECTED_PAGE_TITLES[index - 1]
            if _normalized(title) not in _normalized(text):
                errors.append(
                    f"PPTX slide {index} is missing expected title: {title}"
                )
        for term in SLIDE_REQUIRED_TERMS.get(index, ()):
            if _normalized(term) not in _normalized(text):
                errors.append(
                    f"PPTX slide {index} is missing required term: {term}"
                )

    errors.extend(_package_editability_errors(pptx_path))

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
                pdf_reader = PdfReader(pdf_path)
                pdf_pages = len(pdf_reader.pages)
            except Exception as exc:  # pragma: no cover - parser diagnostics vary
                errors.append(f"Unable to read PDF {pdf_path}: {exc}")
            else:
                if pdf_pages != EXPECTED_SLIDES:
                    errors.append(
                        f"PDF must contain exactly {EXPECTED_SLIDES} pages; found {pdf_pages}"
                    )
                for index, page in enumerate(pdf_reader.pages, start=1):
                    try:
                        page_text = page.extract_text() or ""
                    except Exception as exc:  # pragma: no cover - parser diagnostics vary
                        errors.append(f"Unable to extract PDF page {index} text: {exc}")
                        continue
                    if index <= len(EXPECTED_PAGE_TITLES):
                        title = EXPECTED_PAGE_TITLES[index - 1]
                        if _normalized(title) not in _normalized(page_text):
                            errors.append(
                                f"PDF page {index} is missing expected title: {title}"
                            )
                    for term in SLIDE_REQUIRED_TERMS.get(index, ()):
                        if _normalized(term) not in _normalized(page_text):
                            errors.append(
                                f"PDF page {index} is missing required term: {term}"
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
    print("native_editability_checks=PASS")
    if args.pdf is not None:
        print("pdf_page_text_checks=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
