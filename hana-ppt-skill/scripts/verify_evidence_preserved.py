#!/usr/bin/env python3
"""hana-refine로 재작성된 텍스트가 수치·비교 기준을 보존했는지 검증합니다."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

NUMBER_RE = re.compile(r"\d[\d,\.]*\s*(?:%|원|조|억|만|bp|pt|년|월|일|배)?")
COMPARISON_MARKERS = ["전년동기 대비", "전분기 대비", "전년 대비", "YoY", "QoQ"]


def numeric_tokens(text: str) -> list[str]:
    return [match.group(0).replace(" ", "") for match in NUMBER_RE.finditer(text)]


def comparison_markers(text: str) -> set[str]:
    return {marker for marker in COMPARISON_MARKERS if marker in text}


def check_unit(original: str, edited: str) -> list[str]:
    errors: list[str] = []
    original_numbers = sorted(numeric_tokens(original))
    edited_numbers = sorted(numeric_tokens(edited))
    if original_numbers != edited_numbers:
        errors.append(f"수치 불일치: 원문={original_numbers} 수정={edited_numbers}")
    dropped_markers = comparison_markers(original) - comparison_markers(edited)
    if dropped_markers:
        errors.append(f"비교 기준 누락: {sorted(dropped_markers)}")
    return errors


def verify(original_units: list[dict[str, object]], edits: dict[int, str]) -> list[str]:
    errors: list[str] = []
    by_index = {unit["index"]: unit["text"] for unit in original_units}
    for index, edited_text in edits.items():
        if index not in by_index:
            errors.append(f"원문에 없는 인덱스에 대한 수정: {index}")
            continue
        errors.extend(f"[unit {index}] {error}" for error in check_unit(by_index[index], edited_text))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="hana-refine 수정안의 수치·비교 기준 보존 여부를 검증합니다.")
    parser.add_argument("original_units", type=Path, help="text_units.py extract 출력 JSON")
    parser.add_argument("edits", type=Path, help='{"인덱스": "새 텍스트"} 형식 JSON')
    args = parser.parse_args()
    original_units = json.loads(args.original_units.read_text(encoding="utf-8"))
    raw_edits = json.loads(args.edits.read_text(encoding="utf-8"))
    edits = {int(key): value for key, value in raw_edits.items()}
    errors = verify(original_units, edits)
    if errors:
        for error in errors:
            print(f"오류: {error}")
        raise SystemExit(1)
    print(f"검증 통과: {len(edits)}개 수정 단위의 수치·비교 기준이 보존되었습니다.")


if __name__ == "__main__":
    main()
