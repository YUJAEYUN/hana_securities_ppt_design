#!/usr/bin/env python3
"""deck_spec.json과 승인된 brand.json/layouts.json으로 새 PPTX를 생성합니다.

deck_spec.json은 텍스트·표 인벤토리만 담고 있어(위치·이미지 데이터 없음) 원본을 그대로
재현할 수 없다. `--layouts`/`--layout-plan`을 주지 않으면 슬라이드마다 제목 + (불릿 또는 표)
하나짜리 기본(data-body) 레이아웃만 만든다. `--layout-plan`으로 슬라이드별 역할(승인된
layouts.json의 패턴 키)을 지정하면 cover/section-divider/disclaimer/data-body 역할별로
다르게 배치하고 브랜드 색상으로 장식을 그린다. cover/section-divider는 실제 하나증권
배포 자료(hana-securities-2025-profile) 대조로 전체 배경을 primary_green으로 채우고
흰 제목을 놓는 방식으로 확정했다(references/hana-securities-cover-pattern-correction.md).
data-body는 제목 밑줄을, 표는 진한 헤더 행과 옅은 줄무늬 행을 brand.json 색상으로 그린다
(재무 현황 페이지 대조 근거). 역할 판단(어떤 슬라이드가 표지인지 등)은 에이전트/사람이
하고, 이 스크립트는 그 판단을 기계적으로 실행만 한다 — hana-refine의 edits.json과 같은
원칙이다. strategic-kpi, executive-summary, closing 역할별 배치는 아직 없다. 로고는
보호영역이 미확정이라(brand.json.logo.placement_status) 자동 배치하지 않고 경고로만
보고한다. 이미지·그래픽·그룹 요소도 재현하지 않고 build 결과의 warnings로 보고한다.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import restyle_deck

EMU_PER_INCH = 914400
MARGIN = 457200  # 0.5in
TITLE_HEIGHT = 838200  # ~0.9in

XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'

CONTENT_TYPES_TEMPLATE = (
    XML_HEADER
    + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/ppt/presentation.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
    '<Override PartName="/ppt/slideMasters/slideMaster1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
    '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
    '<Override PartName="/ppt/theme/theme1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
    "{slide_overrides}"
    '<Override PartName="/docProps/core.xml" '
    'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
    '<Override PartName="/docProps/app.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
    "</Types>"
)

ROOT_RELS = (
    XML_HEADER
    + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="ppt/presentation.xml"/>'
    '<Relationship Id="rId2" '
    'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
    'Target="docProps/core.xml"/>'
    '<Relationship Id="rId3" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
    'Target="docProps/app.xml"/>'
    "</Relationships>"
)

CORE_XML = (
    XML_HEADER
    + "<cp:coreProperties "
    'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/">'
    "<dc:title>Hana Securities Deck</dc:title>"
    "</cp:coreProperties>"
)

APP_XML = (
    XML_HEADER
    + "<Properties "
    'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
    "<Application>hana-ppt-skill build_deck.py</Application>"
    "</Properties>"
)

PRESENTATION_TEMPLATE = (
    XML_HEADER
    + '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
    '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rIdMaster1"/></p:sldMasterIdLst>'
    "<p:sldIdLst>{slide_ids}</p:sldIdLst>"
    '<p:sldSz cx="{cx}" cy="{cy}"/>'
    '<p:notesSz cx="6858000" cy="9144000"/>'
    "</p:presentation>"
)

PRESENTATION_RELS_TEMPLATE = (
    XML_HEADER
    + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rIdMaster1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
    'Target="slideMasters/slideMaster1.xml"/>'
    "{slide_rels}"
    "</Relationships>"
)

SLIDE_MASTER_XML = (
    XML_HEADER
    + '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
    "<p:cSld><p:bg><p:bgRef idx=\"1001\"><a:schemeClr val=\"bg1\"/></p:bgRef></p:bg>"
    "<p:spTree><p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
    "<p:grpSpPr/></p:spTree></p:cSld>"
    '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" '
    'accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" '
    'hlink="hlink" folHlink="folHlink"/>'
    '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rIdLayout1"/></p:sldLayoutIdLst>'
    "</p:sldMaster>"
)

SLIDE_MASTER_RELS = (
    XML_HEADER
    + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rIdLayout1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
    'Target="../slideLayouts/slideLayout1.xml"/>'
    '<Relationship Id="rIdTheme1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" '
    'Target="../theme/theme1.xml"/>'
    "</Relationships>"
)

SLIDE_LAYOUT_TEMPLATE = (
    XML_HEADER
    + '<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="obj" preserve="1">'
    '<p:cSld name="Title and Content">'
    '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
    "<p:grpSpPr/>"
    '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
    '<p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>'
    '<p:spPr><a:xfrm><a:off x="{margin}" y="{margin}"/>'
    '<a:ext cx="{title_cx}" cy="{title_cy}"/></a:xfrm></p:spPr>'
    "<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>제목</a:t></a:r></a:p></p:txBody></p:sp>"
    '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Content"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
    '<p:nvPr><p:ph idx="1"/></p:nvPr></p:nvSpPr>'
    '<p:spPr><a:xfrm><a:off x="{margin}" y="{body_y}"/>'
    '<a:ext cx="{body_cx}" cy="{body_cy}"/></a:xfrm></p:spPr>'
    "<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>본문</a:t></a:r></a:p></p:txBody></p:sp>"
    "</p:spTree></p:cSld></p:sldLayout>"
)

SLIDE_LAYOUT_RELS = (
    XML_HEADER
    + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
    'Target="../slideMasters/slideMaster1.xml"/>'
    "</Relationships>"
)

SLIDE_RELS_TEMPLATE = (
    XML_HEADER
    + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
    'Target="../slideLayouts/slideLayout1.xml"/>'
    "</Relationships>"
)

FMT_SCHEME = (
    '<a:fmtScheme name="Office">'
    "<a:fillStyleLst>"
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"><a:lumMod val="110000"/></a:schemeClr></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"><a:lumMod val="105000"/></a:schemeClr></a:solidFill>'
    "</a:fillStyleLst>"
    "<a:lnStyleLst>"
    '<a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    '<a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    '<a:ln w="19050"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    "</a:lnStyleLst>"
    "<a:effectStyleLst>"
    "<a:effectStyle><a:effectLst/></a:effectStyle>"
    "<a:effectStyle><a:effectLst/></a:effectStyle>"
    "<a:effectStyle><a:effectLst/></a:effectStyle>"
    "</a:effectStyleLst>"
    "<a:bgFillStyleLst>"
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"><a:lumMod val="110000"/></a:schemeClr></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"><a:lumMod val="105000"/></a:schemeClr></a:solidFill>'
    "</a:bgFillStyleLst>"
    "</a:fmtScheme>"
)

THEME_TEMPLATE = (
    XML_HEADER
    + '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Hana Securities">'
    "<a:themeElements>"
    '<a:clrScheme name="Hana Securities">'
    "<a:dk1><a:srgbClr val=\"{dk1}\"/></a:dk1>"
    "<a:lt1><a:srgbClr val=\"{lt1}\"/></a:lt1>"
    "<a:dk2><a:srgbClr val=\"{dk2}\"/></a:dk2>"
    "<a:lt2><a:srgbClr val=\"{lt2}\"/></a:lt2>"
    "<a:accent1><a:srgbClr val=\"{accent1}\"/></a:accent1>"
    "<a:accent2><a:srgbClr val=\"{accent2}\"/></a:accent2>"
    "<a:accent3><a:srgbClr val=\"{accent3}\"/></a:accent3>"
    "<a:accent4><a:srgbClr val=\"{accent4}\"/></a:accent4>"
    "<a:accent5><a:srgbClr val=\"{accent5}\"/></a:accent5>"
    "<a:accent6><a:srgbClr val=\"{accent6}\"/></a:accent6>"
    "<a:hlink><a:srgbClr val=\"{hlink}\"/></a:hlink>"
    "<a:folHlink><a:srgbClr val=\"{folHlink}\"/></a:folHlink>"
    "</a:clrScheme>"
    '<a:fontScheme name="Hana Securities">'
    '<a:majorFont><a:latin typeface="{major}"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
    '<a:minorFont><a:latin typeface="{minor}"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>'
    "</a:fontScheme>"
    "{fmt_scheme}"
    "</a:themeElements>"
    "</a:theme>"
)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _run_pr(*, bold: bool = False, color: str | None = None, size: int | None = None) -> str:
    """<a:rPr>를 만든다. size는 포인트(예: 12pt=1200 하는 OOXML 방식이 아니라 실제 pt 정수,
    내부에서 100배해 sz 속성으로 바꾼다)."""
    if not (bold or color or size):
        return ""
    attrs = ' b="1"' if bold else ""
    attrs += f' sz="{size * 100}"' if size else ""
    fill = f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>' if color else ""
    return f"<a:rPr{attrs}>{fill}</a:rPr>"


def _paragraph(
    text: str,
    *,
    align: str | None = None,
    color: str | None = None,
    bold: bool = False,
    size: int | None = None,
) -> str:
    pPr = f'<a:pPr algn="{align}"/>' if align else ""
    rPr = _run_pr(bold=bold, color=color, size=size)
    return f"<a:p>{pPr}<a:r>{rPr}<a:t>{_escape(text)}</a:t></a:r></a:p>"


def _bullets_body(bullets: list[str]) -> str:
    if not bullets:
        return "<a:p/>"
    return "".join(_paragraph(text) for text in bullets)


def _content_placeholder(inner_xml: str) -> str:
    return (
        '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Content"/><p:cNvSpPr/>'
        '<p:nvPr><p:ph idx="1"/></p:nvPr></p:nvSpPr><p:spPr/>'
        f"<p:txBody><a:bodyPr/><a:lstStyle/>{inner_xml}</p:txBody></p:sp>"
    )


def _role_hex(brand: dict, role: str) -> str | None:
    color = brand.get("colors", {}).get(role)
    return color["value"].lstrip("#").upper() if color else None


def _decoration_shape(
    shape_id: int,
    name: str,
    prst: str,
    x: int,
    y: int,
    cx: int,
    cy: int,
    hex_color: str,
    *,
    alpha: int | None = None,
) -> str:
    """장식용 도형(<p:sp>) 하나를 그린다. 텍스트가 없는 순수 배경 장식이라 spTree에서
    제목·본문보다 먼저 와야 뒤에 깔린다(문서 순서 = 쌓임 순서)."""
    alpha_xml = f'<a:alpha val="{alpha}"/>' if alpha is not None else ""
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="{prst}"><a:avLst/></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="{hex_color}">{alpha_xml}</a:srgbClr></a:solidFill>'
        "<a:ln><a:noFill/></a:ln></p:spPr>"
        "<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>"
    )


def _decorations_for_role(role: str, brand: dict, cx: int, cy: int, body_cx: int) -> tuple[str, list[str]]:
    """cover/section-divider/data-body 장식을 brand.json 색상 역할로 그린다.

    cover와 section-divider는 처음에 layouts.json의 HFG IR 기반 추정(적색 강조선,
    원형 모티프)으로 그렸으나, 실제 하나증권 배포 자료(hana-securities-2025-profile,
    표지 1p·섹션 구분 3p/10p)를 대조한 결과 원형 모티프는 없고 대신 전체 배경을
    primary_green으로 채운 위에 흰 제목만 놓는 것으로 확인돼 이 근거로 다시 그린다
    (references/hana-securities-cover-pattern-correction.md 참고). 로고처럼 보호영역이
    없는 요소는 그리지 않고 경고로만 남긴다(brand.json.logo.policy와 동일한 원칙)."""
    shapes: list[str] = []
    warnings: list[str] = []
    shape_id = 90

    def add(prst: str, name: str, x: int, y: int, w: int, h: int, role_name: str, *, alpha: int | None = None) -> None:
        nonlocal shape_id
        hex_color = _role_hex(brand, role_name)
        if hex_color is None:
            return
        shapes.append(_decoration_shape(shape_id, name, prst, x, y, w, h, hex_color, alpha=alpha))
        shape_id += 1

    if role in {"cover", "section-divider"}:
        add("rect", "Decoration Full Background", 0, 0, cx, cy, "primary_green")
        if role == "cover":
            warnings.append("표지 로고는 보호영역 미확정으로 자동 배치하지 않음(brand.json.logo.placement_status)")
    elif role == "data-body":
        add("rect", "Decoration Divider Rule", MARGIN, MARGIN + TITLE_HEIGHT, body_cx, 25400, "pale_mint")

    return "".join(shapes), warnings


def _title_shape(title: str, *, color: str | None = None) -> str:
    return (
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/>'
        '<p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:spPr/>'
        f"<p:txBody><a:bodyPr/><a:lstStyle/>{_paragraph(title, color=color)}</p:txBody></p:sp>"
    )


def _table_cell(text: str, *, fill: str | None = None, color: str | None = None, bold: bool = False) -> str:
    """표 셀 하나. 재무 현황(5p)의 헤더 진한 배경·흰 글씨, 부분합 줄무늬 배경을 근거로
    header/band 색을 brand.json 색상 역할로 채운다(layouts.json의 table_colors.header와
    같은 지정)."""
    rPr = _run_pr(bold=bold, color=color)
    tcPr = f'<a:tcPr><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill></a:tcPr>' if fill else "<a:tcPr/>"
    return (
        f"<a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r>{rPr}"
        f"<a:t>{_escape(text)}</a:t></a:r></a:p></a:txBody>{tcPr}</a:tc>"
    )


def _table_xml(rows: list[list[str]], cx: int, cy: int, brand: dict) -> str:
    column_count = max((len(row) for row in rows), default=1)
    column_width = cx // column_count if column_count else cx
    row_height = cy // len(rows) if rows else cy
    grid_cols = "".join(f'<a:gridCol w="{column_width}"/>' for _ in range(column_count))
    header_hex = _role_hex(brand, "deep_teal")
    band_hex = _role_hex(brand, "pale_mint")
    body_rows = []
    for row_index, row in enumerate(rows):
        is_header = row_index == 0
        fill = header_hex if is_header else (band_hex if row_index % 2 == 1 else None)
        color = "FFFFFF" if is_header else None
        cells = "".join(_table_cell(cell, fill=fill, color=color, bold=is_header) for cell in row)
        padding = "".join(
            _table_cell("", fill=fill) for _ in range(column_count - len(row))
        )
        body_rows.append(f'<a:tr h="{row_height}">{cells}{padding}</a:tr>')
    return (
        '<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="4" name="Table"/>'
        "<p:cNvGraphicFramePr><a:graphicFrameLocks noGrp=\"1\"/></p:cNvGraphicFramePr><p:nvPr/>"
        "</p:nvGraphicFramePr>"
        f'<p:xfrm><a:off x="{MARGIN}" y="{MARGIN + TITLE_HEIGHT}"/><a:ext cx="{cx}" cy="{cy}"/></p:xfrm>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
        f'<a:tbl><a:tblPr firstRow="1" bandRow="1"/><a:tblGrid>{grid_cols}</a:tblGrid>'
        f"{''.join(body_rows)}</a:tbl>"
        "</a:graphicData></a:graphic></p:graphicFrame>"
    )


def _parse_slide(slide: dict) -> tuple[str, list[str], list[list[str]] | None, list[str]]:
    """요소를 (제목, 나머지 텍스트, 표 행, 경고)로 나눈다. 제목은 첫 텍스트 요소다."""
    warnings: list[str] = []
    title = ""
    extra_texts: list[str] = []
    table_rows: list[list[str]] | None = None
    for element in slide.get("elements", []):
        kind = element.get("kind")
        if kind == "table" and table_rows is None:
            table_rows = element.get("rows", [])
            continue
        text = element.get("text")
        if not text:
            if kind in {"image", "graphic", "group"}:
                warnings.append(f"{kind} 요소는 재현하지 않음 ({element.get('name', '')})")
            continue
        if not title:
            title = text
        else:
            extra_texts.append(text)
    return title, extra_texts, table_rows, warnings


# TITLE_COLOR: cover/section-divider는 실제 하나증권 자료 대조 결과 전체 배경이
# primary_green이라 제목을 흰색으로 그려야 읽힌다. 왼쪽 정렬은 두 역할 모두 기본값과
# 같아 별도 처리가 필요 없다(실제 자료에 가운데 정렬 제목은 없었다).
TITLE_COLOR = {"cover": "FFFFFF", "section-divider": "FFFFFF"}


def _render_cover(extra_texts: list[str]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    subtitle = extra_texts[0] if extra_texts else ""
    if len(extra_texts) > 1:
        warnings.append("표지 레이아웃은 제목·부제만 배치하며 나머지 텍스트는 생략됨")
    inner = _paragraph(subtitle, color="FFFFFF") if subtitle else "<a:p/>"
    return _content_placeholder(inner), warnings


def _render_section_divider(extra_texts: list[str], table_rows: list[list[str]] | None) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if extra_texts or table_rows:
        warnings.append("섹션 구분 레이아웃은 본문을 배치하지 않는다(layouts.json 금지 규칙) — 본문/표 생략됨")
    return _content_placeholder("<a:p/>"), warnings


def _text_box(shape_id: int, name: str, x: int, y: int, cx: int, cy: int, inner_xml: str) -> str:
    """placeholder가 아닌 독립 텍스트 상자. strategic-kpi/executive-summary처럼 한 슬라이드에
    여러 개를 나란히 놓아야 하는 요소에 쓴다(placeholder는 슬라이드당 하나만 의미가 있다)."""
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm></p:spPr>'
        f"<p:txBody><a:bodyPr/><a:lstStyle/>{inner_xml}</p:txBody></p:sp>"
    )


def _chunk_even(items: list[str], columns: int, *, per_column: int | None = None) -> list[list[str]]:
    """텍스트를 columns개 열로 나눈다. 어떤 텍스트가 어느 열에 속하는지는 deck_spec의
    순서만으로 정하며(내용을 보고 추측하지 않음), 개수가 맞지 않으면 조용히 잘라내거나
    채우지 않고 바로 오류로 막는다."""
    if columns < 1:
        raise ValueError("columns는 1 이상이어야 합니다.")
    expected_total = columns * per_column if per_column is not None else None
    if expected_total is not None and len(items) != expected_total:
        raise ValueError(
            f"columns={columns}에 각 열당 {per_column}개씩 총 {expected_total}개 텍스트가 필요한데 "
            f"{len(items)}개를 받았습니다."
        )
    if per_column is None:
        if len(items) % columns != 0 or len(items) // columns < 1:
            raise ValueError(
                f"columns={columns}으로 고르게 나눌 수 없는 텍스트 개수({len(items)})입니다. "
                "열마다 같은 개수의 텍스트(첫 번째는 카드 제목)를 주세요."
            )
        per_column = len(items) // columns
    return [items[i * per_column : (i + 1) * per_column] for i in range(columns)]


def _column_geometry(columns: int, cx: int) -> tuple[int, int]:
    gap = 228600  # 0.25in
    total_width = cx - 2 * MARGIN
    col_width = (total_width - (columns - 1) * gap) // columns
    return col_width, gap


def _render_strategic_kpi(extra_texts: list[str], columns: int, brand: dict, cx: int) -> tuple[str, list[str]]:
    """국내·외 네트워크(7p)의 통계 블록(레이블 위·얇은 선·큰 숫자)을 근거로 한 열 배치.
    각 열은 정확히 [레이블, 값] 두 텍스트가 필요하다 — 어느 텍스트가 레이블이고 값인지
    추측하지 않고 deck_spec 순서 그대로 받는다."""
    groups = _chunk_even(extra_texts, columns, per_column=2)
    col_width, gap = _column_geometry(columns, cx)
    top = MARGIN + TITLE_HEIGHT + MARGIN // 3
    label_hex = _role_hex(brand, "deep_teal")
    value_hex = _role_hex(brand, "primary_green")
    rule_hex = _role_hex(brand, "pale_mint")
    shapes: list[str] = []
    shape_id = 150
    for index, (label, value) in enumerate(groups):
        x = MARGIN + index * (col_width + gap)
        shapes.append(_text_box(shape_id, "Stat Label", x, top, col_width, 320000, _paragraph(label, color=label_hex, size=12)))
        shape_id += 1
        if rule_hex:
            shapes.append(_decoration_shape(shape_id, "Decoration Stat Rule", "rect", x, top + 330000, col_width, 25400, rule_hex))
            shape_id += 1
        shapes.append(
            _text_box(
                shape_id,
                "Stat Value",
                x,
                top + 400000,
                col_width,
                700000,
                _paragraph(value, color=value_hex, bold=True, size=32),
            )
        )
        shape_id += 1
    return "".join(shapes), []


def _render_executive_summary(extra_texts: list[str], columns: int, brand: dict, cx: int) -> tuple[str, list[str]]:
    """주요 사업영역(11p)의 3열 카드(상단 컬러 바 + 옅은 헤더 블록 + 구분선 + 불릿)를 근거로
    한 카드 배치. 각 열의 첫 텍스트를 카드 제목으로, 나머지를 불릿으로 쓴다 — 어떤 텍스트가
    제목인지 추측하지 않고 deck_spec 순서(열마다 같은 개수) 그대로 받는다."""
    groups = _chunk_even(extra_texts, columns)
    col_width, gap = _column_geometry(columns, cx)
    top = MARGIN + TITLE_HEIGHT + MARGIN // 2
    bar_hex = _role_hex(brand, "deep_teal")
    header_hex = _role_hex(brand, "pale_mint")
    heading_color = _role_hex(brand, "deep_teal")
    bar_h, header_h, rule_h = 45720, 750000, 25400
    card_h = 4200000
    shapes: list[str] = []
    shape_id = 150
    for index, group in enumerate(groups):
        heading, bullets = group[0], group[1:]
        x = MARGIN + index * (col_width + gap)
        y = top
        if bar_hex:
            shapes.append(_decoration_shape(shape_id, "Decoration Card Top Bar", "rect", x, y, col_width, bar_h, bar_hex))
            shape_id += 1
        y += bar_h
        if header_hex:
            shapes.append(_decoration_shape(shape_id, "Decoration Card Header", "rect", x, y, col_width, header_h, header_hex))
            shape_id += 1
        shapes.append(
            _text_box(
                shape_id,
                "Card Heading",
                x,
                y,
                col_width,
                header_h,
                _paragraph(heading, align="ctr", color=heading_color, bold=True, size=20),
            )
        )
        shape_id += 1
        y += header_h
        if bar_hex:
            shapes.append(_decoration_shape(shape_id, "Decoration Card Divider", "rect", x, y, col_width, rule_h, bar_hex))
            shape_id += 1
        y += rule_h + 91440
        shapes.append(_text_box(shape_id, "Card Bullets", x, y, col_width, card_h - (y - top), _bullets_body(bullets)))
        shape_id += 1
        if bar_hex:
            shapes.append(_decoration_shape(shape_id, "Decoration Card Bottom Rule", "rect", x, top + card_h, col_width, rule_h, bar_hex))
            shape_id += 1
    return "".join(shapes), []


def _render_disclaimer(extra_texts: list[str]) -> tuple[str, list[str]]:
    paragraphs = "".join(_paragraph(text) for text in extra_texts) or "<a:p/>"
    return _content_placeholder(paragraphs), []


def _render_data_body(
    extra_texts: list[str], table_rows: list[list[str]] | None, body_cx: int, body_cy: int, brand: dict
) -> tuple[str, list[str]]:
    if table_rows:
        return _table_xml(table_rows, body_cx, body_cy, brand), []
    return _content_placeholder(_bullets_body(extra_texts)), []


def _require_columns(role: str, params: dict) -> int:
    columns = params.get("columns")
    if not isinstance(columns, int) or columns < 1:
        raise ValueError(
            f"'{role}' 역할은 layout-plan에 정수 columns가 필요합니다. "
            f'예: {{"role": "{role}", "columns": 3}}'
        )
    return columns


def _render_slide(
    role: str,
    params: dict,
    slide: dict,
    brand: dict,
    cx: int,
    cy: int,
    body_cx: int,
    body_cy: int,
) -> tuple[str, list[str]]:
    title, extra_texts, table_rows, warnings = _parse_slide(slide)
    if role == "cover":
        body_xml, role_warnings = _render_cover(extra_texts)
    elif role == "section-divider":
        body_xml, role_warnings = _render_section_divider(extra_texts, table_rows)
    elif role == "disclaimer":
        body_xml, role_warnings = _render_disclaimer(extra_texts)
    elif role == "strategic-kpi":
        body_xml, role_warnings = _render_strategic_kpi(extra_texts, _require_columns(role, params), brand, cx)
    elif role == "executive-summary":
        body_xml, role_warnings = _render_executive_summary(extra_texts, _require_columns(role, params), brand, cx)
    else:
        body_xml, role_warnings = _render_data_body(extra_texts, table_rows, body_cx, body_cy, brand)
    warnings.extend(role_warnings)
    decoration_xml, decoration_warnings = _decorations_for_role(role, brand, cx, cy, body_cx)
    warnings.extend(decoration_warnings)
    title_xml = _title_shape(title, color=TITLE_COLOR.get(role))
    slide_xml = (
        XML_HEADER
        + '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        "<p:grpSpPr/>"
        f"{decoration_xml}{title_xml}{body_xml}"
        "</p:spTree></p:cSld></p:sld>"
    )
    return slide_xml, [f"슬라이드 {slide['number']}: {warning}" for warning in warnings]


def build(deck_spec: dict, brand: dict, layout_plan: dict[int, str] | None = None) -> dict[str, object]:
    layout_plan = layout_plan or {}
    color_map = restyle_deck.brand_theme_color_map(brand)
    major, minor = restyle_deck.brand_theme_fonts(brand)
    scheme_defaults = {
        "dk1": "000000",
        "lt1": "FFFFFF",
        "dk2": "000000",
        "lt2": "FFFFFF",
        "accent1": "000000",
        "accent2": "000000",
        "accent3": "000000",
        "accent4": "000000",
        "accent5": "000000",
        "accent6": "000000",
        "hlink": "0563C1",
        "folHlink": "954F72",
    }
    scheme = {**scheme_defaults, **color_map}

    aspect_ratio = brand.get("canvas", {}).get("aspect_ratio", 1.444)
    cy = 6858000
    cx = round(cy * aspect_ratio)
    title_cx = cx - 2 * MARGIN
    body_y = MARGIN + TITLE_HEIGHT + MARGIN // 2
    body_cx = cx - 2 * MARGIN
    body_cy = cy - body_y - MARGIN

    slides = deck_spec.get("slides", [])
    slide_ids_xml = "".join(
        f'<p:sldId id="{256 + index}" r:id="rIdSlide{number}"/>'
        for index, number in enumerate(s["number"] for s in slides)
    )
    slide_rels_xml = "".join(
        f'<Relationship Id="rIdSlide{s["number"]}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
        f'Target="slides/slide{s["number"]}.xml"/>'
        for s in slides
    )
    slide_overrides_xml = "".join(
        f'<Override PartName="/ppt/slides/slide{s["number"]}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for s in slides
    )

    parts: dict[str, bytes] = {
        "[Content_Types].xml": CONTENT_TYPES_TEMPLATE.format(slide_overrides=slide_overrides_xml).encode(
            "utf-8"
        ),
        "_rels/.rels": ROOT_RELS.encode("utf-8"),
        "docProps/core.xml": CORE_XML.encode("utf-8"),
        "docProps/app.xml": APP_XML.encode("utf-8"),
        "ppt/presentation.xml": PRESENTATION_TEMPLATE.format(
            slide_ids=slide_ids_xml, cx=cx, cy=cy
        ).encode("utf-8"),
        "ppt/_rels/presentation.xml.rels": PRESENTATION_RELS_TEMPLATE.format(
            slide_rels=slide_rels_xml
        ).encode("utf-8"),
        "ppt/slideMasters/slideMaster1.xml": SLIDE_MASTER_XML.encode("utf-8"),
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": SLIDE_MASTER_RELS.encode("utf-8"),
        "ppt/slideLayouts/slideLayout1.xml": SLIDE_LAYOUT_TEMPLATE.format(
            margin=MARGIN,
            title_cx=title_cx,
            title_cy=TITLE_HEIGHT,
            body_y=body_y,
            body_cx=body_cx,
            body_cy=body_cy,
        ).encode("utf-8"),
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": SLIDE_LAYOUT_RELS.encode("utf-8"),
        "ppt/theme/theme1.xml": THEME_TEMPLATE.format(
            fmt_scheme=FMT_SCHEME, major=major, minor=minor, **scheme
        ).encode("utf-8"),
    }

    warnings: list[str] = []
    for slide in slides:
        params = layout_plan.get(slide["number"], {"role": "data-body"})
        slide_xml, slide_warnings = _render_slide(params["role"], params, slide, brand, cx, cy, body_cx, body_cy)
        warnings.extend(slide_warnings)
        parts[f"ppt/slides/slide{slide['number']}.xml"] = slide_xml.encode("utf-8")
        parts[f"ppt/slides/_rels/slide{slide['number']}.xml.rels"] = SLIDE_RELS_TEMPLATE.encode("utf-8")

    return {"parts": parts, "warnings": warnings}


def load_layout_plan(path: Path) -> dict[int, dict]:
    """슬라이드별 역할 JSON을 읽는다. 값은 문자열 역할("cover") 또는
    {"role": "executive-summary", "columns": 3}처럼 역할에 필요한 추가 인자를 담은 객체다.
    columns 같은 추가 인자는 에이전트/사람이 명시적으로 정하며, 이 스크립트는 그 값을
    그대로 기계적으로 실행만 한다."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    plan: dict[int, dict] = {}
    for slide_number, value in raw.items():
        if isinstance(value, str):
            plan[int(slide_number)] = {"role": value}
        elif isinstance(value, dict) and "role" in value:
            plan[int(slide_number)] = value
        else:
            raise ValueError(f'layout-plan의 슬라이드 {slide_number} 값이 올바르지 않습니다: {value!r}')
    return plan


def build_deck(
    deck_spec_path: Path,
    brand_path: Path,
    out_path: Path,
    *,
    layouts_path: Path | None = None,
    layout_plan_path: Path | None = None,
) -> dict[str, object]:
    deck_spec = json.loads(deck_spec_path.read_text(encoding="utf-8"))
    brand = restyle_deck.load_approved_json(brand_path, "brand.json")
    layout_plan: dict[int, dict] = {}
    if layouts_path is not None or layout_plan_path is not None:
        if layouts_path is None or layout_plan_path is None:
            raise ValueError("역할별 레이아웃 배치를 쓰려면 --layouts와 --layout-plan을 모두 지정해야 합니다.")
        layouts = restyle_deck.load_approved_json(layouts_path, "layouts.json")
        layout_plan = load_layout_plan(layout_plan_path)
        slide_numbers = {slide["number"] for slide in deck_spec.get("slides", [])}
        unknown_slides = set(layout_plan) - slide_numbers
        if unknown_slides:
            raise ValueError(f"deck_spec에 없는 슬라이드 번호: {sorted(unknown_slides)}")
        unknown_roles = {params["role"] for params in layout_plan.values()} - set(layouts["patterns"])
        if unknown_roles:
            raise ValueError(f"layouts.json에 없는 역할: {sorted(unknown_roles)}")
    result = build(deck_spec, brand, layout_plan)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in result["parts"].items():
            archive.writestr(name, data)
    return {"slide_count": len(deck_spec.get("slides", [])), "warnings": result["warnings"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="deck_spec.json과 brand.json/layouts.json으로 새 PPTX를 생성합니다.")
    parser.add_argument("deck_spec", type=Path)
    parser.add_argument("--brand", type=Path, required=True)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--layouts", type=Path, help="역할별 배치에 필요한 승인된 layouts.json")
    parser.add_argument(
        "--layout-plan", type=Path, help='슬라이드별 역할 JSON, 예: {"1": "cover", "3": "disclaimer"}'
    )
    args = parser.parse_args()
    try:
        result = build_deck(
            args.deck_spec,
            args.brand,
            args.output,
            layouts_path=args.layouts,
            layout_plan_path=args.layout_plan,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"생성 완료: {args.output} (슬라이드 {result['slide_count']}개, 경고 {len(result['warnings'])}건)")
    for warning in result["warnings"]:
        print(f"경고: {warning}")


if __name__ == "__main__":
    main()
