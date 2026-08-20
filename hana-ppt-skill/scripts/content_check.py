#!/usr/bin/env python3
"""콘텐츠 QA: 텍스트 누락과 플레이스홀더 잔존을 검사합니다.

구조 QA(quality_check.py)가 PPTX 파일 구조를, 시각 QA(visual_check.py)가 렌더 이미지를
보는 것과 달리, 이 검사는 슬라이드의 실제 텍스트 내용만 본다 — text_units.py로 각
슬라이드의 <a:t> 런을 문서 순서대로 뽑아 두 가지를 확인한다.

1. 누락 검사: deck_spec.json의 각 텍스트 요소가 결과 PPTX 어딘가에 그대로 남아 있는가.
   restyle-only처럼 슬라이드 XML을 전혀 건드리지 않는 모드의 결과물을 검사할 때 가장
   의미가 있다(모든 원문이 그대로 있어야 정상). build_deck.py처럼 역할별로 일부 텍스트를
   의도적으로 생략하는 산출물은 그 생략이 build_deck.py 자체의 warnings로 이미 보고되므로,
   여기서는 "생략을 허용할 슬라이드 번호" 집합을 받아 그 슬라이드는 건너뛴다.
2. 플레이스홀더 잔존 검사: "제목을 입력하세요"류의 흔한 PowerPoint 기본 안내 문구가
   실제 콘텐츠인 것처럼 남아 있는지 슬라이드 전체에서 훑는다.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import text_units

# 한국어/영어 PowerPoint 템플릿에서 흔히 남는 기본 안내 문구. 실제 콘텐츠에 이 문구가
# 그대로 쓰일 가능성은 낮다고 보고 목록으로 관리한다 — 새로 발견하면 여기에 추가한다.
PLACEHOLDER_PATTERNS = [
    "제목을 입력",
    "부제목을 입력",
    "텍스트를 입력",
    "본문을 입력",
    "클릭하여 텍스트 추가",
    "Click to add title",
    "Click to add text",
    "Click to add subtitle",
    "Lorem ipsum",
]


def load_parts(pptx_path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(pptx_path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _slide_texts(slide_xml_bytes: bytes) -> list[str]:
    return [unit["text"] for unit in text_units.extract_text_units(slide_xml_bytes.decode("utf-8")) if unit["text"]]


def check_missing_text(deck_spec: dict, parts: dict[str, bytes], *, skip_slides: set[int] = frozenset()) -> list[str]:
    errors: list[str] = []
    for slide in deck_spec.get("slides", []):
        number = slide["number"]
        if number in skip_slides:
            continue
        slide_xml = parts.get(slide["part"])
        if slide_xml is None:
            continue  # 파트 자체가 없는 건 quality_check.py의 몫
        actual_texts = set(_slide_texts(slide_xml))
        for element in slide.get("elements", []):
            text = element.get("text")
            if text and text not in actual_texts:
                errors.append(f"슬라이드 {number}: 원문 텍스트가 결과물에서 사라짐: {text!r}")
    return errors


def check_placeholder_leftovers(parts: dict[str, bytes]) -> list[str]:
    errors: list[str] = []
    for name, data in sorted(parts.items()):
        if not (name.startswith("ppt/slides/slide") and name.endswith(".xml")):
            continue
        for text in _slide_texts(data):
            for pattern in PLACEHOLDER_PATTERNS:
                if pattern in text:
                    errors.append(f"{name}: 플레이스홀더로 보이는 텍스트가 남아 있음: {text!r}")
    return errors


def run(
    pptx_path: Path, *, deck_spec_path: Path | None = None, skip_slides: set[int] = frozenset()
) -> dict[str, object]:
    parts = load_parts(pptx_path)
    errors: list[str] = []
    errors.extend(check_placeholder_leftovers(parts))
    if deck_spec_path is not None:
        deck_spec = json.loads(deck_spec_path.read_text(encoding="utf-8"))
        errors.extend(check_missing_text(deck_spec, parts, skip_slides=skip_slides))
    return {"status": "pass" if not errors else "fail", "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description="PPTX의 콘텐츠 QA(텍스트 누락·플레이스홀더)를 검사합니다.")
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--deck-spec", type=Path, help="누락 검사에 쓸 deck_spec.json")
    parser.add_argument(
        "--skip-slides",
        type=str,
        default="",
        help="의도적으로 텍스트를 생략하는 슬라이드 번호(쉼표 구분). 예: 1,3",
    )
    parser.add_argument("-o", "--output", type=Path, help="결과를 저장할 JSON 경로(생략하면 표준출력만)")
    args = parser.parse_args()
    skip_slides = {int(n) for n in args.skip_slides.split(",") if n.strip()}
    result = run(args.pptx, deck_spec_path=args.deck_spec, skip_slides=skip_slides)
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"콘텐츠 QA: {result['status']} ({len(result['errors'])}건 오류)")
    for error in result["errors"]:
        print(f"오류: {error}")
    if result["status"] == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
