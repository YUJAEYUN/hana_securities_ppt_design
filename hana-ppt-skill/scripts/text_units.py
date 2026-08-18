#!/usr/bin/env python3
"""슬라이드 텍스트 런(run)을 추출하고, 같은 순서 주소로 안전하게 다시 써 넣습니다.

원본 XML을 파싱해서 재직렬화하지 않고 <a:t> 요소만 문자열 치환하므로
런 서식(rPr), 문단 구조, 네임스페이스가 항상 보존됩니다.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}

# <a:t>content</a:t> 또는 <a:t/>. 속성(xml:space="preserve" 등)을 그대로 보존하기 위해
# 여는 태그의 속성 문자열을 캡처해 두었다가 교체할 때 그대로 다시 쓴다.
T_TAG_RE = re.compile(r"<a:t([^>]*)>(.*?)</a:t>|<a:t([^>]*)/>", re.DOTALL)


def _relationships(archive: zipfile.ZipFile, part: str) -> dict[str, str]:
    rels_name = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
    try:
        root = ET.fromstring(archive.read(rels_name))
    except KeyError:
        return {}
    base = posixpath.dirname(part)
    return {
        rel.attrib["Id"]: posixpath.normpath(posixpath.join(base, rel.attrib["Target"]))
        for rel in root.findall("pr:Relationship", NS)
        if rel.attrib.get("TargetMode") != "External"
    }


def slide_part_for_number(archive: zipfile.ZipFile, slide_number: int) -> str:
    presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
    rels = _relationships(archive, "ppt/presentation.xml")
    slide_ids = presentation.findall("p:sldIdLst/p:sldId", NS)
    if not 1 <= slide_number <= len(slide_ids):
        raise ValueError(f"슬라이드 번호가 범위를 벗어났습니다: {slide_number} (전체 {len(slide_ids)}장)")
    rel_id = slide_ids[slide_number - 1].attrib[f"{{{NS['r']}}}id"]
    if rel_id not in rels:
        raise ValueError(f"슬라이드 관계를 찾을 수 없습니다: {rel_id}")
    return rels[rel_id]


def _build_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def _enclosing_shape(node: ET.Element, parent_map: dict[ET.Element, ET.Element]) -> ET.Element | None:
    current = parent_map.get(node)
    while current is not None:
        if current.tag.rsplit("}", 1)[-1] in {"sp", "graphicFrame", "pic", "grpSp"}:
            return current
        current = parent_map.get(current)
    return None


def _shape_name(shape: ET.Element) -> str:
    name_node = shape.find(".//p:cNvPr", NS)
    return name_node.attrib.get("name", "") if name_node is not None else ""


def _placeholder_type(shape: ET.Element) -> str | None:
    ph = shape.find(".//p:ph", NS)
    if ph is None:
        return None
    return ph.attrib.get("type", "body")


def extract_text_units(slide_xml: str) -> list[dict[str, object]]:
    """텍스트 런을 문서 순서대로 추출한다.

    shape_name/placeholder_type은 에이전트가 역할(제목/본문 등)을 가늠하는 참고용 힌트일 뿐이다.
    이 저장소의 레퍼런스 덱에서 면책 문구는 placeholder 없이 자유 텍스트 상자로 그려지므로,
    placeholder_type만으로 면책 문구를 걸러낼 수는 없다. 최종 판단은 항상 내용을 읽고 내린다.
    """
    root = ET.fromstring(slide_xml)
    parent_map = _build_parent_map(root)
    units: list[dict[str, object]] = []
    for index, node in enumerate(root.findall(".//a:t", NS)):
        shape = _enclosing_shape(node, parent_map)
        is_shape = shape is not None and shape.tag.rsplit("}", 1)[-1] == "sp"
        units.append(
            {
                "index": index,
                "text": node.text or "",
                "shape_name": _shape_name(shape) if is_shape else "",
                "placeholder_type": _placeholder_type(shape) if is_shape else None,
            }
        )
    return units


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def apply_text_edits(slide_xml: str, edits: dict[int, str]) -> str:
    """edits={run_index: 새 텍스트}. extract_text_units와 같은 문서 순서로 <a:t>를 센다."""
    state = {"index": -1}

    def _replace(match: re.Match[str]) -> str:
        state["index"] += 1
        attrs = match.group(1) if match.group(1) is not None else match.group(3)
        if state["index"] not in edits:
            return match.group(0)
        return f"<a:t{attrs}>{_escape(edits[state['index']])}</a:t>"

    return T_TAG_RE.sub(_replace, slide_xml)


def main() -> None:
    parser = argparse.ArgumentParser(description="PPTX 슬라이드의 텍스트 런을 추출합니다.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--slide", type=int, required=True)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    with zipfile.ZipFile(args.input) as archive:
        part = slide_part_for_number(archive, args.slide)
        slide_xml = archive.read(part).decode("utf-8")
    units = extract_text_units(slide_xml)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(units, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"텍스트 단위 추출 완료: {args.output} ({len(units)}개)")


if __name__ == "__main__":
    main()
