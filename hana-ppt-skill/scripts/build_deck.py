#!/usr/bin/env python3
"""deck_spec.json과 승인된 brand.json으로 새 PPTX를 생성합니다.

deck_spec.json은 텍스트·표 인벤토리만 담고 있어(위치·이미지 데이터 없음) 원본을 그대로
재현할 수 없다. 이 v1은 슬라이드마다 제목 하나 + (불릿 목록 또는 표 하나)만 배치하는
단일 레이아웃만 만든다. 이미지·그래픽·그룹 요소는 재현하지 않고 build 결과의 warnings로
보고한다. 표지·목차·비교 같은 문서군별 레이아웃은 여기 포함하지 않는다
(레이아웃 근거가 사람 승인 전이라 ROADMAP.md에서 별도로 미룬 범위다).
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


def _bullets_body(bullets: list[str]) -> str:
    if not bullets:
        return "<a:p/>"
    return "".join(f"<a:p><a:r><a:t>{_escape(text)}</a:t></a:r></a:p>" for text in bullets)


def _table_xml(rows: list[list[str]], cx: int, cy: int) -> str:
    column_count = max((len(row) for row in rows), default=1)
    column_width = cx // column_count if column_count else cx
    row_height = cy // len(rows) if rows else cy
    grid_cols = "".join(f'<a:gridCol w="{column_width}"/>' for _ in range(column_count))
    body_rows = []
    for row in rows:
        cells = "".join(
            "<a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r>"
            f"<a:t>{_escape(cell)}</a:t></a:r></a:p></a:txBody><a:tcPr/></a:tc>"
            for cell in row
        )
        padding = "".join(
            "<a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p/></a:txBody><a:tcPr/></a:tc>"
            for _ in range(column_count - len(row))
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


def _slide_content(slide: dict, body_cx: int, body_cy: int) -> tuple[str, list[str]]:
    warnings: list[str] = []
    title = ""
    bullets: list[str] = []
    table_rows: list[list[str]] | None = None
    for element in slide.get("elements", []):
        kind = element.get("kind")
        if kind == "table" and table_rows is None:
            table_rows = element.get("rows", [])
            continue
        text = element.get("text")
        if not text:
            if kind in {"image", "graphic", "group"}:
                warnings.append(f"슬라이드 {slide['number']}: {kind} 요소는 재현하지 않음 ({element.get('name', '')})")
            continue
        if not title:
            title = text
        else:
            bullets.append(text)
    body_xml = (
        _table_xml(table_rows, body_cx, body_cy)
        if table_rows
        else (
            '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Content"/><p:cNvSpPr/>'
            '<p:nvPr><p:ph idx="1"/></p:nvPr></p:nvSpPr><p:spPr/>'
            f"<p:txBody><a:bodyPr/><a:lstStyle/>{_bullets_body(bullets)}</p:txBody></p:sp>"
        )
    )
    slide_xml = (
        XML_HEADER
        + '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        "<p:grpSpPr/>"
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/>'
        '<p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:spPr/>'
        f"<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>{_escape(title)}</a:t></a:r></a:p></p:txBody></p:sp>"
        f"{body_xml}"
        "</p:spTree></p:cSld></p:sld>"
    )
    return slide_xml, warnings


def build(deck_spec: dict, brand: dict) -> dict[str, bytes]:
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
        slide_xml, slide_warnings = _slide_content(slide, body_cx, body_cy)
        warnings.extend(slide_warnings)
        parts[f"ppt/slides/slide{slide['number']}.xml"] = slide_xml.encode("utf-8")
        parts[f"ppt/slides/_rels/slide{slide['number']}.xml.rels"] = SLIDE_RELS_TEMPLATE.encode("utf-8")

    return {"parts": parts, "warnings": warnings}


def build_deck(deck_spec_path: Path, brand_path: Path, out_path: Path) -> dict[str, object]:
    deck_spec = json.loads(deck_spec_path.read_text(encoding="utf-8"))
    brand = json.loads(brand_path.read_text(encoding="utf-8"))
    if brand.get("status") != "approved":
        raise ValueError("승인되지 않은 brand.json은 실행에 사용할 수 없습니다.")
    result = build(deck_spec, brand)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in result["parts"].items():
            archive.writestr(name, data)
    return {"slide_count": len(deck_spec.get("slides", [])), "warnings": result["warnings"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="deck_spec.json과 brand.json으로 새 PPTX를 생성합니다.")
    parser.add_argument("deck_spec", type=Path)
    parser.add_argument("--brand", type=Path, required=True)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build_deck(args.deck_spec, args.brand, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"생성 완료: {args.output} (슬라이드 {result['slide_count']}개, 경고 {len(result['warnings'])}건)")
    for warning in result["warnings"]:
        print(f"경고: {warning}")


if __name__ == "__main__":
    main()
