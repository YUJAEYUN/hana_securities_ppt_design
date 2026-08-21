#!/usr/bin/env python3
"""생성되거나 후처리된 PPTX의 구조 QA(스키마·관계·자산 정합성)를 검사합니다.

콘텐츠 QA(텍스트 누락)나 시각 QA(렌더 이미지를 보고 판단)와 달리, 이 검사는 PPTX
파일 자체에서 기계적으로 확인 가능한 것만 본다 — 파일을 열지 않고도 파이썬
표준 라이브러리(zipfile, xml.etree)만으로 판정할 수 있는 사실이다.

- [Content_Types].xml의 Override가 가리키는 파트가 실제로 존재하는가
- 모든 .rels 파일의 Relationship Target이 실제 파트로 풀리는가(TargetMode="External"은 제외)
- 슬라이드 화면비가 brand.json의 canvas.aspect_ratio와 맞는가
- deck_spec.json을 함께 주면 슬라이드 수가 일치하는가
- 명시적 좌표(xfrm)를 가진 텍스트 도형이 슬라이드 경계 밖으로 나가거나(장식용
  Decoration* 도형은 의도적으로 화면 밖으로 걸치는 경우가 있어 제외한다) 서로 겹치는가

무엇을 검사하지 않는지도 분명히 한다: placeholder(제목/본문)처럼 xfrm이 없어
slideLayout의 상속 좌표를 쓰는 도형은 이 스크립트가 좌표를 모르므로 겹침 검사에서
제외한다. 렌더링 없이는 텍스트가 실제로 잘리는지 알 수 없어 그건 시각 QA
(scripts/visual_check.py)의 몫이다.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "r": "http://schemas.openxmlformats.org/package/2006/relationships",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def load_parts(pptx_path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(pptx_path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def check_content_types(parts: dict[str, bytes]) -> list[str]:
    errors: list[str] = []
    ct_bytes = parts.get("[Content_Types].xml")
    if ct_bytes is None:
        return ["[Content_Types].xml이 없습니다."]
    root = ET.fromstring(ct_bytes)
    for override in root.findall("ct:Override", NS):
        part_name = override.get("PartName", "").lstrip("/")
        if part_name and part_name not in parts:
            errors.append(f"[Content_Types].xml Override가 없는 파트를 가리킵니다: {part_name}")
    return errors


def _resolve_target(rels_path: str, target: str) -> str:
    # rels 파일은 항상 {디렉터리}/_rels/{파일명}.rels 형태고, Target은 그 {디렉터리} 기준
    # 상대 경로다. zip 안의 가상 경로끼리 문자열로만 계산한다 — 실제 파일시스템(cwd)은
    # 절대 건드리지 않는다(이 스크립트를 어디서 실행하든 결과가 같아야 한다).
    rels_dir = posixpath.dirname(rels_path)  # .../_rels
    base_dir = posixpath.dirname(rels_dir)
    return posixpath.normpath(posixpath.join(base_dir, target))


def check_relationships(parts: dict[str, bytes]) -> list[str]:
    errors: list[str] = []
    for name, data in parts.items():
        if not name.endswith(".rels"):
            continue
        root = ET.fromstring(data)
        for rel in root.findall("r:Relationship", NS):
            if rel.get("TargetMode") == "External":
                continue
            target = rel.get("Target", "")
            resolved = _resolve_target(name, target)
            if resolved not in parts:
                errors.append(f"{name}의 관계 Target이 존재하지 않는 파트를 가리킵니다: {target} (해석: {resolved})")
    return errors


def _slide_size(parts: dict[str, bytes]) -> tuple[int, int] | None:
    presentation = parts.get("ppt/presentation.xml")
    if presentation is None:
        return None
    root = ET.fromstring(presentation)
    sld_sz = root.find("p:sldSz", NS)
    if sld_sz is None:
        return None
    return int(sld_sz.get("cx")), int(sld_sz.get("cy"))


def check_aspect_ratio(parts: dict[str, bytes], brand: dict, *, tolerance: float = 0.01) -> list[str]:
    size = _slide_size(parts)
    if size is None:
        return ["ppt/presentation.xml에 슬라이드 크기(sldSz)가 없습니다."]
    cx, cy = size
    actual_ratio = cx / cy
    expected_ratio = brand.get("canvas", {}).get("aspect_ratio")
    if expected_ratio is None:
        return []
    if abs(actual_ratio - expected_ratio) > tolerance:
        return [f"화면비 불일치: 실제 {actual_ratio:.4f} vs brand.json 기대값 {expected_ratio:.4f}"]
    return []


def check_slide_count(parts: dict[str, bytes], deck_spec: dict) -> list[str]:
    actual = len([name for name in parts if name.startswith("ppt/slides/slide") and name.endswith(".xml")])
    expected = len(deck_spec.get("slides", []))
    if actual != expected:
        return [f"슬라이드 수 불일치: 생성된 파일 {actual}개 vs deck_spec.json {expected}개"]
    return []


def _shape_bounds(sp: ET.Element) -> tuple[int, int, int, int] | None:
    xfrm = sp.find("./p:spPr/a:xfrm", NS)
    if xfrm is None:
        return None
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    if off is None or ext is None:
        return None
    x, y = int(off.get("x")), int(off.get("y"))
    w, h = int(ext.get("cx")), int(ext.get("cy"))
    return x, y, w, h


def _overlap_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ox = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    oy = max(0, min(ay + ah, by + bh) - max(ay, by))
    return ox * oy


def check_shape_bounds(parts: dict[str, bytes]) -> list[str]:
    """xfrm이 명시된 텍스트 도형만 검사한다(placeholder는 좌표를 모르므로 대상 밖).
    이름이 "Decoration"으로 시작하는 도형은 의도적으로 화면 밖까지 걸치는 배경 장식이라
    경계·겹침 검사에서 제외한다."""
    errors: list[str] = []
    size = _slide_size(parts)
    if size is None:
        return errors
    cx, cy = size
    slide_names = sorted(name for name in parts if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
    for slide_name in slide_names:
        root = ET.fromstring(parts[slide_name])
        shapes: list[tuple[str, tuple[int, int, int, int]]] = []
        for sp in root.findall(".//p:sp", NS):
            name_el = sp.find(".//p:cNvPr", NS)
            shape_name = name_el.get("name", "") if name_el is not None else ""
            if shape_name.startswith("Decoration"):
                continue
            bounds = _shape_bounds(sp)
            if bounds is None:
                continue
            x, y, w, h = bounds
            if x < 0 or y < 0 or x + w > cx or y + h > cy:
                errors.append(f"{slide_name}: 도형 '{shape_name}'이(가) 슬라이드 경계를 벗어남 ({x},{y},{w},{h})")
            shapes.append((shape_name, bounds))
        for i in range(len(shapes)):
            for j in range(i + 1, len(shapes)):
                name_a, bounds_a = shapes[i]
                name_b, bounds_b = shapes[j]
                overlap = _overlap_area(bounds_a, bounds_b)
                smaller_area = min(bounds_a[2] * bounds_a[3], bounds_b[2] * bounds_b[3])
                if smaller_area and overlap / smaller_area > 0.1:
                    errors.append(f"{slide_name}: 도형 '{name_a}'와(과) '{name_b}'가 많이 겹침")
    return errors


def run(
    pptx_path: Path, *, brand_path: Path | None = None, deck_spec_path: Path | None = None
) -> dict[str, object]:
    parts = load_parts(pptx_path)
    errors: list[str] = []
    errors.extend(check_content_types(parts))
    errors.extend(check_relationships(parts))
    errors.extend(check_shape_bounds(parts))
    if brand_path is not None:
        brand = json.loads(brand_path.read_text(encoding="utf-8"))
        errors.extend(check_aspect_ratio(parts, brand))
    if deck_spec_path is not None:
        deck_spec = json.loads(deck_spec_path.read_text(encoding="utf-8"))
        errors.extend(check_slide_count(parts, deck_spec))
    return {"status": "pass" if not errors else "fail", "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description="PPTX의 구조 QA(스키마·관계·자산 정합성)를 검사합니다.")
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--brand", type=Path, help="화면비 검사에 쓸 brand.json")
    parser.add_argument("--deck-spec", type=Path, help="슬라이드 수 검사에 쓸 deck_spec.json")
    parser.add_argument("-o", "--output", type=Path, help="결과를 저장할 JSON 경로(생략하면 표준출력만)")
    args = parser.parse_args()
    result = run(args.pptx, brand_path=args.brand, deck_spec_path=args.deck_spec)
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"구조 QA: {result['status']} ({len(result['errors'])}건 오류)")
    for error in result["errors"]:
        print(f"오류: {error}")
    if result["status"] == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
