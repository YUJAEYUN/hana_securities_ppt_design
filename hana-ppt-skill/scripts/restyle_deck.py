#!/usr/bin/env python3
"""승인된 brand.json의 색상·폰트를 PPTX 테마 파트에 적용합니다.

슬라이드 XML은 전혀 읽거나 쓰지 않으므로 원문·수치·데이터는 항상 보존됩니다.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

THEME_PART_RE = re.compile(r"^ppt/theme/theme\d+\.xml$")

# OOXML 테마 색상 슬롯은 dk1/lt1/dk2/lt2/accent1-6/hlink/folHlink로 고정되어 있고,
# brand.json의 색상 role(제목, KPI 등)과 이름이 다르므로 여기서 한 번만 연결한다.
COLOR_SLOT_ROLE = {
    "lt1": "background",
    "dk1": "deep_teal",
    "dk2": "deep_teal",
    "lt2": "pale_mint",
    "accent1": "primary_green",
    "accent2": "deep_teal",
    "accent3": "pale_mint",
    "accent4": "alert_red",
    "accent5": "primary_green",
    "accent6": "deep_teal",
}


def brand_theme_color_map(brand: dict) -> dict[str, str]:
    colors = brand["colors"]
    return {
        slot: colors[role]["value"].lstrip("#").upper()
        for slot, role in COLOR_SLOT_ROLE.items()
        if role in colors
    }


def brand_theme_fonts(brand: dict) -> tuple[str, str]:
    typography = brand["typography"]
    return typography["heading"]["families"][0], typography["body"]["families"][0]


def apply_theme_colors(theme_xml: str, color_map: dict[str, str]) -> str:
    for slot, hex_value in color_map.items():
        pattern = re.compile(rf"(<a:{slot}>).*?(</a:{slot}>)", re.DOTALL)
        theme_xml = pattern.sub(rf'\1<a:srgbClr val="{hex_value}"/>\2', theme_xml)
    return theme_xml


def apply_theme_fonts(theme_xml: str, major: str, minor: str) -> str:
    for tag, family in (("majorFont", major), ("minorFont", minor)):
        pattern = re.compile(rf'(<a:{tag}>.*?<a:latin typeface=")[^"]*(".*?</a:{tag}>)', re.DOTALL)
        theme_xml = pattern.sub(lambda m: f"{m.group(1)}{family}{m.group(2)}", theme_xml)
    return theme_xml


def restyle_theme_parts(parts: dict[str, bytes], brand: dict) -> dict[str, bytes]:
    color_map = brand_theme_color_map(brand)
    major, minor = brand_theme_fonts(brand)
    updated = dict(parts)
    for name, data in parts.items():
        if not THEME_PART_RE.match(name):
            continue
        text = data.decode("utf-8")
        text = apply_theme_colors(text, color_map)
        text = apply_theme_fonts(text, major, minor)
        updated[name] = text.encode("utf-8")
    return updated


def restyle(pptx_path: Path, brand_path: Path, out_path: Path, mode: str) -> dict[str, object]:
    if mode != "restyle-only":
        raise NotImplementedError(
            "hana-refine 모드의 콘텐츠 수준 변경은 아직 구현되지 않았습니다. 현재는 restyle-only(테마 색상·폰트)만 지원합니다."
        )
    brand = json.loads(brand_path.read_text(encoding="utf-8"))
    if brand.get("status") != "approved":
        raise ValueError("승인되지 않은 brand.json은 실행에 사용할 수 없습니다.")
    with zipfile.ZipFile(pptx_path) as archive:
        original = {name: archive.read(name) for name in archive.namelist()}
    updated = restyle_theme_parts(original, brand)
    changed_parts = sorted(name for name, data in updated.items() if data != original[name])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in updated.items():
            archive.writestr(name, data)
    return {"mode": mode, "theme_parts_changed": changed_parts}


def main() -> None:
    parser = argparse.ArgumentParser(description="brand.json 색상·폰트를 PPTX 테마에 적용합니다.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--brand", type=Path, required=True)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["restyle-only", "hana-refine"], default="restyle-only")
    args = parser.parse_args()
    try:
        result = restyle(args.input, args.brand, args.output, args.mode)
    except (OSError, ValueError, NotImplementedError) as exc:
        parser.error(str(exc))
    print(f"테마 적용 완료: {args.output} (변경된 테마 파트 {len(result['theme_parts_changed'])}개)")


if __name__ == "__main__":
    main()
