#!/usr/bin/env python3
"""render_slides.py의 render manifest를 시각 QA용 검수 패킷으로 정리합니다.

이 스크립트는 "예쁜가"를 판단하지 않는다. layouts.json의 승인된 패턴(elements,
evidence_pages)과 brand.json의 색상 수치를 슬라이드별 체크리스트로 기계적으로
바꿔줄 뿐이다. 실제 렌더 이미지를 보고 체크리스트 항목을 하나씩 맞는지 판단하는
일은 이 결과물을 받는 별도의(가능하면 이 슬라이드를 만들지 않은) 비전 가능한
에이전트 세션이 한다 — 절차는 references/visual-qa-rubric.md를 따른다.

Pillow(PIL)가 설치돼 있으면 cover/section-divider처럼 전체 배경이 단색인 역할에
한해 배경색 픽셀을 하나 찍어 brand.json 색상과의 거리를 기계적으로 계산해준다.
Pillow가 없으면 그 항목은 생략하고 비전 판단에만 맡긴다(이 저장소는 아직
표준 라이브러리만 의존하므로 Pillow를 필수로 만들지 않는다).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_deck
import restyle_deck

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:  # pragma: no cover - 환경에 따라 갈리는 경로
    PIL_AVAILABLE = False

# cover/section-divider는 build_deck.py가 (0,0)-(cx,cy) 전체를 primary_green
# 단색 사각형으로 채운다. 텍스트나 다른 도형과 겹치지 않는 안전한 표본 지점을
# 슬라이드 비율로 하나 고정해둔다(우측 상단 15% 지점 — 표지 부제/본문 텍스트가
# 왼쪽에 몰려 있어 겹치지 않는다).
FULL_BLEED_SAMPLE_POINT = (0.9, 0.15)
FULL_BLEED_ROLES = {"cover": "primary_green", "section-divider": "primary_green"}


def _role_hex(brand: dict, role: str) -> str | None:
    color = brand.get("colors", {}).get(role)
    return color["value"].lstrip("#").upper() if color else None


def _color_distance(hex_a: str, hex_b: str) -> float:
    a = tuple(int(hex_a[i : i + 2], 16) for i in (0, 2, 4))
    b = tuple(int(hex_b[i : i + 2], 16) for i in (0, 2, 4))
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def sample_background_hex(image_path: Path, point: tuple[float, float]) -> str | None:
    if not PIL_AVAILABLE or not image_path.is_file():
        return None
    with Image.open(image_path) as img:
        rgb = img.convert("RGB")
        x = min(rgb.width - 1, max(0, round(rgb.width * point[0])))
        y = min(rgb.height - 1, max(0, round(rgb.height * point[1])))
        r, g, b = rgb.getpixel((x, y))
    return f"{r:02X}{g:02X}{b:02X}"


def _format_element(element: dict, brand: dict) -> str:
    parts = []
    for key, value in element.items():
        if key == "color" and isinstance(value, str):
            hex_value = _role_hex(brand, value)
            value = f"{value}({hex_value})" if hex_value else value
        parts.append(f"{key}={value}")
    return ", ".join(parts)


def checklist_for_role(role: str, layouts: dict, brand: dict) -> tuple[list[str], str, str]:
    """(체크리스트, 신뢰도, 참고 메모)를 만든다. 신뢰도는 이 패턴이 실제 하나증권
    자료로 확인됐는지(evidence_pages에 하나증권 소속 source_id가 있는지)로 정한다 —
    임의 판단이 아니라 layouts.json에 이미 적힌 사실을 그대로 읽는다."""
    pattern = layouts.get("patterns", {}).get(role)
    if pattern is None:
        return (["이 역할은 layouts.json에 정의돼 있지 않아 근거 없이 검수할 수 없다."], "undefined-role", "")

    items = [_format_element(el, brand) for el in pattern.get("elements", [])]
    prohibited = pattern.get("prohibited_content")
    if prohibited:
        items.append(f"금지: {', '.join(prohibited)}가 있으면 안 됨")

    evidence_pages = pattern.get("evidence_pages", {})
    hana_secu_sources = [source for source in evidence_pages if "hana-securities" in source]
    confidence = "hana-securities-evidenced" if hana_secu_sources else "hfg-group-estimate-only"
    note = pattern.get("note", "")
    return items, confidence, note


def build_review_packet(
    render_manifest: dict, layout_plan: dict[int, dict], layouts: dict, brand: dict
) -> dict:
    slides = []
    for slide in render_manifest.get("slides", []):
        number = slide["number"]
        role = layout_plan.get(number, {}).get("role", "data-body")
        checklist, confidence, note = checklist_for_role(role, layouts, brand)
        entry: dict[str, object] = {
            "number": number,
            "role": role,
            "confidence": confidence,
            "note": note,
            "image_path": slide.get("path"),
            "checklist": checklist,
            "unlisted_issues_hint": (
                "체크리스트에 없는 문제(텍스트 잘림, 겹침, 정렬 어긋남 등)는 "
                "references/general-ppt-design-principles.md의 CRAP 원칙을 참고해 "
                "별도 unlisted_issues로 남기고 checklist 판정과 섞지 않는다."
            ),
        }
        if role in FULL_BLEED_ROLES and slide.get("path"):
            expected_role = FULL_BLEED_ROLES[role]
            expected_hex = _role_hex(brand, expected_role)
            measured_hex = sample_background_hex(Path(slide["path"]), FULL_BLEED_SAMPLE_POINT)
            if expected_hex and measured_hex:
                distance = _color_distance(expected_hex, measured_hex)
                entry["mechanical_background_check"] = {
                    "expected_role": expected_role,
                    "expected_hex": expected_hex,
                    "measured_hex": measured_hex,
                    "distance": round(distance, 1),
                    "verdict": "match" if distance <= 12 else "mismatch",
                }
            else:
                entry["mechanical_background_check"] = None  # Pillow 미설치 등으로 생략
        slides.append(entry)

    return {
        "schema_version": 1,
        "instructions": "references/visual-qa-rubric.md",
        "brand_colors": {
            role: color["value"] for role, color in brand.get("colors", {}).items()
        },
        "pillow_available": PIL_AVAILABLE,
        "slides": slides,
    }


def build_check(
    render_manifest_path: Path,
    layouts_path: Path,
    brand_path: Path,
    out_path: Path,
    *,
    layout_plan_path: Path | None = None,
) -> dict:
    render_manifest = json.loads(render_manifest_path.read_text(encoding="utf-8"))
    layouts = restyle_deck.load_approved_json(layouts_path, "layouts.json")
    brand = restyle_deck.load_approved_json(brand_path, "brand.json")
    layout_plan = build_deck.load_layout_plan(layout_plan_path) if layout_plan_path else {}
    packet = build_review_packet(render_manifest, layout_plan, layouts, brand)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="render manifest를 시각 QA 검수 패킷으로 정리합니다.")
    parser.add_argument("render_manifest", type=Path)
    parser.add_argument("--layouts", type=Path, required=True)
    parser.add_argument("--brand", type=Path, required=True)
    parser.add_argument("--layout-plan", type=Path, help='슬라이드별 역할 JSON(build_deck.py와 같은 형식)')
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        packet = build_check(
            args.render_manifest, args.layouts, args.brand, args.output, layout_plan_path=args.layout_plan
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"검수 패킷 생성: {args.output} (슬라이드 {len(packet['slides'])}개, Pillow={'사용' if packet['pillow_available'] else '미사용'})")


if __name__ == "__main__":
    main()
