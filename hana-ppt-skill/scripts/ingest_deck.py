#!/usr/bin/env python3
"""Create a loss-aware deck_spec inventory from an OOXML PowerPoint file."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}
UNSUPPORTED = {
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/oleObject": "OLE object",
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/package": "embedded package",
}


def _xml(archive: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        return ET.fromstring(archive.read(name))
    except KeyError as exc:
        raise ValueError(f"PPTX 필수 파트가 없습니다: {name}") from exc
    except ET.ParseError as exc:
        raise ValueError(f"XML을 해석할 수 없습니다: {name}") from exc


def _relationships(archive: zipfile.ZipFile, part: str) -> dict[str, tuple[str, str]]:
    rels_name = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
    try:
        root = _xml(archive, rels_name)
    except ValueError:
        return {}
    base = posixpath.dirname(part)
    return {
        rel.attrib["Id"]: (posixpath.normpath(posixpath.join(base, rel.attrib["Target"])), rel.attrib["Type"])
        for rel in root.findall("pr:Relationship", NS)
        if rel.attrib.get("TargetMode") != "External"
    }


def _slide_parts(archive: zipfile.ZipFile) -> list[str]:
    presentation = _xml(archive, "ppt/presentation.xml")
    rels = _relationships(archive, "ppt/presentation.xml")
    parts: list[str] = []
    for slide_id in presentation.findall("p:sldIdLst/p:sldId", NS):
        rel_id = slide_id.attrib.get(f"{{{NS['r']}}}id")
        if rel_id not in rels:
            raise ValueError(f"슬라이드 관계를 찾을 수 없습니다: {rel_id}")
        parts.append(rels[rel_id][0])
    return parts


def _element_inventory(slide: ET.Element) -> list[dict[str, object]]:
    elements: list[dict[str, object]] = []
    shape_tree = slide.find("p:cSld/p:spTree", NS)
    if shape_tree is None:
        return elements
    for node in shape_tree:
        kind = node.tag.rsplit("}", 1)[-1]
        if kind in {"nvGrpSpPr", "grpSpPr"}:
            continue
        name_node = node.find(".//p:cNvPr", NS)
        text = "\n".join(t.text or "" for t in node.findall(".//a:t", NS))
        item: dict[str, object] = {
            "kind": {"sp": "shape", "pic": "image", "graphicFrame": "graphic", "grpSp": "group"}.get(kind, kind),
            "name": name_node.attrib.get("name", "") if name_node is not None else "",
        }
        if text:
            item["text"] = text
        table = node.find(".//a:tbl", NS)
        if table is not None:
            item["kind"] = "table"
            item["rows"] = [
                ["".join(t.text or "" for t in cell.findall(".//a:t", NS)) for cell in row.findall("a:tc", NS)]
                for row in table.findall("a:tr", NS)
            ]
        graphic_data = node.find(".//a:graphicData", NS)
        if graphic_data is not None and table is None:
            item["graphic_uri"] = graphic_data.attrib.get("uri", "")
        elements.append(item)
    return elements


def ingest(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    slides: list[dict[str, object]] = []
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            for number, part in enumerate(_slide_parts(archive), 1):
                slide = _xml(archive, part)
                slide_warnings: list[str] = []
                for _, rel_type in _relationships(archive, part).values():
                    if rel_type in UNSUPPORTED:
                        slide_warnings.append(f"미지원 요소: {UNSUPPORTED[rel_type]}")
                if slide.findall(".//a:extLst", NS):
                    slide_warnings.append("확장 XML이 있어 일부 요소를 해석하지 못할 수 있습니다.")
                slides.append({"number": number, "part": part, "elements": _element_inventory(slide), "warnings": slide_warnings})
                warnings.extend(f"슬라이드 {number}: {warning}" for warning in slide_warnings)
    except zipfile.BadZipFile as exc:
        raise ValueError("입력 파일이 유효한 PPTX(OOXML ZIP)가 아닙니다.") from exc
    return {
        "schema_version": 1,
        "source": {"path": str(path), "sha256": hashlib.sha256(data).hexdigest()},
        "slides": slides,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="PPTX를 deck_spec.json 인벤토리로 변환합니다.")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        spec = ingest(args.input)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"deck_spec 생성: {args.output} ({len(spec['slides'])}개 슬라이드)")


if __name__ == "__main__":
    main()
