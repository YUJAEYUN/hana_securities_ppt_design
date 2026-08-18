#!/usr/bin/env python3
"""승인된 brand.json/voice.json 규칙을 PPTX에 적용합니다.

restyle-only: 테마 파트(색상·폰트)만 바꾸고 슬라이드 XML은 전혀 읽지 않는다.
hana-refine: 에이전트가 미리 작성한 edits.json으로 슬라이드 텍스트 런을 교체하되,
반드시 verify_evidence_preserved로 수치·비교 기준 보존을 확인한 뒤에만 적용한다.
검증에 실패하면 어떤 슬라이드도 수정하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

import text_units
import verify_evidence_preserved

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


def load_approved_json(path: Path, kind: str) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("status") != "approved":
        raise ValueError(f"승인되지 않은 {kind}은(는) 실행에 사용할 수 없습니다.")
    return data


def _write_pptx(original: dict[str, bytes], updated: dict[str, bytes], out_path: Path) -> list[str]:
    changed_parts = sorted(name for name, data in updated.items() if data != original[name])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in updated.items():
            archive.writestr(name, data)
    return changed_parts


def restyle_theme_only(pptx_path: Path, brand_path: Path, out_path: Path) -> dict[str, object]:
    brand = load_approved_json(brand_path, "brand.json")
    with zipfile.ZipFile(pptx_path) as archive:
        original = {name: archive.read(name) for name in archive.namelist()}
    updated = restyle_theme_parts(original, brand)
    changed_parts = _write_pptx(original, updated, out_path)
    return {"mode": "restyle-only", "theme_parts_changed": changed_parts}


def load_edits(edits_path: Path) -> dict[int, dict[int, str]]:
    raw = json.loads(edits_path.read_text(encoding="utf-8"))
    return {
        int(slide_number): {int(run_index): text for run_index, text in slide_edits.items()}
        for slide_number, slide_edits in raw.items()
    }


def refine(
    pptx_path: Path, brand_path: Path, voice_path: Path, edits_path: Path, out_path: Path
) -> dict[str, object]:
    brand = load_approved_json(brand_path, "brand.json")
    voice = load_approved_json(voice_path, "voice.json")
    edits_by_slide = load_edits(edits_path)
    if not edits_by_slide:
        raise ValueError("edits 파일에 수정할 슬라이드가 없습니다.")
    with zipfile.ZipFile(pptx_path) as archive:
        original = {name: archive.read(name) for name in archive.namelist()}
        errors: list[str] = []
        updated = dict(original)
        for slide_number, slide_edits in edits_by_slide.items():
            try:
                part = text_units.slide_part_for_number(archive, slide_number)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            slide_xml = original[part].decode("utf-8")
            slide_units = text_units.extract_text_units(slide_xml)
            slide_errors = verify_evidence_preserved.verify(slide_units, slide_edits)
            if slide_errors:
                errors.extend(f"슬라이드 {slide_number}: {error}" for error in slide_errors)
                continue
            updated[part] = text_units.apply_text_edits(slide_xml, slide_edits).encode("utf-8")
    if errors:
        raise ValueError("hana-refine 검증 실패로 어떤 슬라이드도 수정하지 않았습니다:\n" + "\n".join(errors))
    updated = restyle_theme_parts(updated, brand)
    changed_parts = _write_pptx(original, updated, out_path)
    return {
        "mode": "hana-refine",
        "policy": voice["mode_policy"]["hana-refine"],
        "edited_slides": sorted(edits_by_slide),
        "changed_parts": changed_parts,
    }


def restyle(
    pptx_path: Path,
    brand_path: Path,
    out_path: Path,
    mode: str,
    *,
    voice_path: Path | None = None,
    edits_path: Path | None = None,
) -> dict[str, object]:
    if mode == "restyle-only":
        return restyle_theme_only(pptx_path, brand_path, out_path)
    if mode == "hana-refine":
        if voice_path is None or edits_path is None:
            raise ValueError("hana-refine 모드는 voice_path와 edits_path가 모두 필요합니다.")
        return refine(pptx_path, brand_path, voice_path, edits_path, out_path)
    raise ValueError(f"알 수 없는 모드: {mode}")


def main() -> None:
    parser = argparse.ArgumentParser(description="brand.json/voice.json 규칙을 PPTX에 적용합니다.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--brand", type=Path, required=True)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["restyle-only", "hana-refine"], default="restyle-only")
    parser.add_argument("--voice", type=Path, help="hana-refine에 필요한 승인된 voice.json")
    parser.add_argument("--edits", type=Path, help="hana-refine에 필요한 슬라이드별 텍스트 수정안 JSON")
    args = parser.parse_args()
    try:
        result = restyle(
            args.input, args.brand, args.output, args.mode, voice_path=args.voice, edits_path=args.edits
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if result["mode"] == "restyle-only":
        print(f"테마 적용 완료: {args.output} (변경된 테마 파트 {len(result['theme_parts_changed'])}개)")
    else:
        print(
            f"hana-refine 적용 완료: {args.output} "
            f"(수정 슬라이드 {len(result['edited_slides'])}개, 변경 파트 {len(result['changed_parts'])}개)"
        )


if __name__ == "__main__":
    main()
