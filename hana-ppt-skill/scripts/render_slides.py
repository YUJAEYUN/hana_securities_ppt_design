#!/usr/bin/env python3
"""PPTX를 PDF와 슬라이드별 이미지로 렌더링하고 render manifest를 만듭니다."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def convert_to_pdf(pptx_path: Path, out_dir: Path) -> Path:
    if shutil.which("soffice") is None:
        raise RuntimeError("soffice 실행 파일을 찾을 수 없습니다. LibreOffice를 설치하세요.")
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx_path)],
        check=True,
        capture_output=True,
    )
    pdf_path = out_dir / f"{pptx_path.stem}.pdf"
    if not pdf_path.is_file():
        raise RuntimeError(f"PDF 변환 결과를 찾을 수 없습니다: {pdf_path}")
    return pdf_path


def convert_to_images(pdf_path: Path, out_dir: Path, dpi: int) -> list[Path]:
    if shutil.which("pdftoppm") is None:
        raise RuntimeError("pdftoppm 실행 파일을 찾을 수 없습니다. poppler-utils를 설치하세요.")
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / pdf_path.stem
    for stale in out_dir.glob(f"{pdf_path.stem}-*.jpg"):
        stale.unlink()
    subprocess.run(
        ["pdftoppm", "-jpeg", "-r", str(dpi), str(pdf_path), str(prefix)],
        check=True,
        capture_output=True,
    )
    return sorted(out_dir.glob(f"{pdf_path.stem}-*.jpg"))


def build_manifest(pptx_path: Path, pdf_path: Path, image_paths: list[Path], dpi: int) -> dict[str, object]:
    return {
        "schema_version": 1,
        "source": {
            "path": str(pptx_path),
            "sha256": hashlib.sha256(pptx_path.read_bytes()).hexdigest() if pptx_path.is_file() else None,
        },
        "renderer": {"engine": "libreoffice+poppler", "dpi": dpi},
        "pdf": str(pdf_path),
        "slides": [
            {"number": number, "path": str(image_path)}
            for number, image_path in enumerate(image_paths, 1)
        ],
        "status": "complete" if image_paths else "partial",
    }


def render(pptx_path: Path, out_dir: Path, dpi: int = 150) -> dict[str, object]:
    pdf_path = convert_to_pdf(pptx_path, out_dir)
    image_paths = convert_to_images(pdf_path, out_dir, dpi)
    manifest = build_manifest(pptx_path, pdf_path, image_paths, dpi)
    manifest_path = out_dir / "render_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="PPTX를 PDF와 슬라이드별 이미지로 렌더링합니다.")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()
    try:
        manifest = render(args.input, args.output, args.dpi)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    print(f"렌더 완료: {args.output} ({len(manifest['slides'])}개 슬라이드, status={manifest['status']})")


if __name__ == "__main__":
    main()
