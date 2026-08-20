from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "hana-ppt-skill" / "scripts"
# restyle_deck.py는 "import text_units"처럼 형제 스크립트를 일반 import로 불러온다.
# 직접 실행할 때는 파이썬이 스크립트 폴더를 자동으로 sys.path에 넣어주지만, 이 테스트처럼
# 파일 경로로 동적 로드할 때는 그 자동 추가가 없으므로 여기서 한 번 등록해 준다.
sys.path.insert(0, str(SCRIPTS_DIR))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


HARNESS = load_module("task_harness", ROOT / "tools" / "task_harness.py")
INGEST = load_module("ingest_deck", SCRIPTS_DIR / "ingest_deck.py")
RENDER = load_module("render_slides", SCRIPTS_DIR / "render_slides.py")
TEXT_UNITS = load_module("text_units", SCRIPTS_DIR / "text_units.py")
VERIFY_EVIDENCE = load_module("verify_evidence_preserved", SCRIPTS_DIR / "verify_evidence_preserved.py")
RESTYLE = load_module("restyle_deck", SCRIPTS_DIR / "restyle_deck.py")
BUILD = load_module("build_deck", SCRIPTS_DIR / "build_deck.py")
VISUAL_CHECK = load_module("visual_check", SCRIPTS_DIR / "visual_check.py")
QUALITY_CHECK = load_module("quality_check", SCRIPTS_DIR / "quality_check.py")


class DocumentValidationTests(unittest.TestCase):
    def test_repository_documents_are_valid(self):
        self.assertEqual([], HARNESS.validate_document_structure())

    def test_control_character_is_rejected(self):
        target = ROOT / "tests" / "temporary-invalid.md"
        target.write_bytes(b"valid\ninvalid\x1e\n")
        try:
            errors = HARNESS.validate_document_structure()
            self.assertTrue(any("제어 문자" in error for error in errors))
        finally:
            target.unlink()

    def test_approved_brand_has_traceable_non_excluded_sources(self):
        brand = json.loads((ROOT / "hana-ppt-skill" / "assets" / "brand.json").read_text())
        sources = json.loads((ROOT / "hana-ppt-skill" / "assets" / "reference-decks" / "sources.json").read_text())
        excluded = {item["id"] for item in sources["documents"] if item.get("style_status") == "excluded-by-user"}
        self.assertEqual("approved", brand["status"])
        self.assertTrue(brand["approval"]["record"])
        self.assertFalse(set(brand["provenance"]["source_ids"]) & excluded)
        self.assertFalse(brand["official_ci_specification"])

    def test_voice_profile_is_scoped_and_preserves_content_by_mode(self):
        voice = json.loads((ROOT / "hana-ppt-skill" / "assets" / "voice.json").read_text())
        sources = json.loads((ROOT / "hana-ppt-skill" / "assets" / "reference-decks" / "sources.json").read_text())
        excluded = {item["id"] for item in sources["documents"] if item.get("style_status") == "excluded-by-user"}
        self.assertEqual("approved", voice["status"])
        self.assertFalse(voice["official_hana_securities_voice"])
        self.assertFalse(set(voice["provenance"]["source_ids"]) & excluded)
        self.assertIn("원문", voice["mode_policy"]["restyle-only"])
        self.assertIn("새 사실", voice["mode_policy"]["hana-refine"])
        self.assertTrue(voice["roles"]["disclaimer"]["must_preserve_verbatim_in_restyle_only"])

    def test_approved_layouts_are_traceable_and_non_excluded(self):
        layouts = json.loads((ROOT / "hana-ppt-skill" / "assets" / "layouts.json").read_text())
        sources = json.loads((ROOT / "hana-ppt-skill" / "assets" / "reference-decks" / "sources.json").read_text())
        excluded = {item["id"] for item in sources["documents"] if item.get("style_status") == "excluded-by-user"}
        self.assertEqual("approved", layouts["status"])
        self.assertTrue(layouts["approval"]["record"])
        self.assertFalse(set(layouts["provenance"]["source_ids"]) & excluded)
        self.assertFalse(layouts["official_hana_securities_layout"])
        self.assertTrue(layouts["patterns"]["disclaimer"]["must_preserve_verbatim_in_restyle_only"])

    def test_inline_svg_is_allowed_in_markdown(self):
        target = ROOT / "tests" / "temporary-inline-svg.md"
        target.write_text('<svg aria-label="diagram"><text>valid</text></svg>\n', encoding="utf-8")
        try:
            errors = HARNESS.validate_document_structure()
            self.assertFalse(any("temporary-inline-svg.md" in error for error in errors))
        finally:
            target.unlink()


class IngestDeckTests(unittest.TestCase):
    def _fixture(self, path: Path) -> None:
        files = {
            "ppt/presentation.xml": '''<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst></p:presentation>''',
            "ppt/_rels/presentation.xml.rels": '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/></Relationships>''',
            "ppt/slides/slide1.xml": '''<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr/><p:grpSpPr/><p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/></p:nvSpPr><p:txBody><a:p><a:r><a:t>테스트 제목</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>''',
        }
        with zipfile.ZipFile(path, "w") as archive:
            for name, value in files.items():
                archive.writestr(name, value)

    def test_ingests_slide_text_and_source_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.pptx"
            self._fixture(source)
            result = INGEST.ingest(source)
        self.assertEqual(1, result["schema_version"])
        self.assertEqual(1, len(result["slides"]))
        self.assertEqual("테스트 제목", result["slides"][0]["elements"][0]["text"])
        self.assertEqual(64, len(result["source"]["sha256"]))

    def test_schema_is_parseable(self):
        schema = json.loads((ROOT / "hana-ppt-skill" / "schemas" / "deck_spec.schema.json").read_text())
        self.assertEqual(1, schema["properties"]["schema_version"]["const"])


class RenderSlidesTests(unittest.TestCase):
    def test_manifest_is_partial_without_images(self):
        with tempfile.TemporaryDirectory() as directory:
            pptx_path = Path(directory) / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")
            pdf_path = Path(directory) / "deck.pdf"
            manifest = RENDER.build_manifest(pptx_path, pdf_path, [], dpi=150)
        self.assertEqual("partial", manifest["status"])
        self.assertEqual(64, len(manifest["source"]["sha256"]))
        self.assertEqual([], manifest["slides"])

    def test_manifest_is_complete_with_ordered_images(self):
        with tempfile.TemporaryDirectory() as directory:
            pptx_path = Path(directory) / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")
            pdf_path = Path(directory) / "deck.pdf"
            images = [Path(directory) / "deck-1.jpg", Path(directory) / "deck-2.jpg"]
            manifest = RENDER.build_manifest(pptx_path, pdf_path, images, dpi=150)
        self.assertEqual("complete", manifest["status"])
        self.assertEqual([1, 2], [slide["number"] for slide in manifest["slides"]])


class RestyleDeckTests(unittest.TestCase):
    THEME_XML = (
        '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office">'
        "<a:themeElements>"
        '<a:clrScheme name="Office">'
        '<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
        '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>'
        '<a:dk2><a:srgbClr val="44546A"/></a:dk2>'
        '<a:lt2><a:srgbClr val="E7E6E6"/></a:lt2>'
        '<a:accent1><a:srgbClr val="4472C4"/></a:accent1>'
        '<a:accent2><a:srgbClr val="ED7D31"/></a:accent2>'
        '<a:accent3><a:srgbClr val="A5A5A5"/></a:accent3>'
        '<a:accent4><a:srgbClr val="FFC000"/></a:accent4>'
        '<a:accent5><a:srgbClr val="5B9BD5"/></a:accent5>'
        '<a:accent6><a:srgbClr val="70AD47"/></a:accent6>'
        '<a:hlink><a:srgbClr val="0563C1"/></a:hlink>'
        '<a:folHlink><a:srgbClr val="954F72"/></a:folHlink>'
        "</a:clrScheme>"
        '<a:fontScheme name="Office">'
        '<a:majorFont><a:latin typeface="Calibri Light" panose="020F0302020204030204"/>'
        '<a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
        '<a:minorFont><a:latin typeface="Calibri" panose="020F0502020204030204"/>'
        '<a:ea typeface=""/><a:cs typeface=""/></a:minorFont>'
        "</a:fontScheme>"
        "</a:themeElements>"
        "</a:theme>"
    )

    SLIDE_XML = (
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        "<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r>"
        "<a:t>핵심이익의 견조한 성장에 힘입어 당기순이익 전년동기 대비 7.3% 증가</a:t>"
        "</a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
    )

    def _fixture(self, path: Path) -> None:
        files = {
            "ppt/presentation.xml": (
                '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst></p:presentation>'
            ),
            "ppt/_rels/presentation.xml.rels": (
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
                'Target="slides/slide1.xml"/></Relationships>'
            ),
            "ppt/theme/theme1.xml": self.THEME_XML,
            "ppt/slides/slide1.xml": self.SLIDE_XML,
        }
        with zipfile.ZipFile(path, "w") as archive:
            for name, value in files.items():
                archive.writestr(name, value)

    def test_restyle_applies_brand_colors_and_fonts_without_touching_slides(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.pptx"
            self._fixture(source)
            out_path = Path(directory) / "out.pptx"
            result = RESTYLE.restyle(source, brand_path, out_path, "restyle-only")
            with zipfile.ZipFile(source) as original, zipfile.ZipFile(out_path) as restyled:
                self.assertEqual(
                    original.read("ppt/slides/slide1.xml"), restyled.read("ppt/slides/slide1.xml")
                )
                theme_xml = restyled.read("ppt/theme/theme1.xml").decode("utf-8")
        self.assertIn('<a:dk1><a:srgbClr val="006060"/></a:dk1>', theme_xml)
        self.assertIn('<a:accent1><a:srgbClr val="009070"/></a:accent1>', theme_xml)
        self.assertIn('<a:latin typeface="하나2.0 H"', theme_xml)
        self.assertIn('<a:latin typeface="하나2.0 R"', theme_xml)
        self.assertEqual(["ppt/theme/theme1.xml"], result["theme_parts_changed"])

    def test_rejects_unapproved_brand(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.pptx"
            self._fixture(source)
            brand_path = Path(directory) / "brand.candidate.json"
            brand_path.write_text(
                json.dumps(
                    {
                        "status": "candidate",
                        "colors": {},
                        "typography": {"heading": {"families": ["x"]}, "body": {"families": ["y"]}},
                    }
                ),
                encoding="utf-8",
            )
            out_path = Path(directory) / "out.pptx"
            with self.assertRaises(ValueError):
                RESTYLE.restyle(source, brand_path, out_path, "restyle-only")

    def test_hana_refine_requires_voice_and_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.pptx"
            self._fixture(source)
            brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
            out_path = Path(directory) / "out.pptx"
            with self.assertRaises(ValueError):
                RESTYLE.restyle(source, brand_path, out_path, "hana-refine")

    def test_refine_applies_edits_that_preserve_numbers_and_updates_theme(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        voice_path = ROOT / "hana-ppt-skill" / "assets" / "voice.json"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.pptx"
            self._fixture(source)
            edits_path = Path(directory) / "edits.json"
            edits_path.write_text(
                json.dumps({"1": {"0": "핵심이익 성장에 따라 당기순이익이 전년동기 대비 7.3% 확대"}}),
                encoding="utf-8",
            )
            out_path = Path(directory) / "out.pptx"
            result = RESTYLE.restyle(
                source, brand_path, out_path, "hana-refine", voice_path=voice_path, edits_path=edits_path
            )
            with zipfile.ZipFile(out_path) as restyled:
                slide_xml = restyled.read("ppt/slides/slide1.xml").decode("utf-8")
                theme_xml = restyled.read("ppt/theme/theme1.xml").decode("utf-8")
        self.assertIn("당기순이익이 전년동기 대비 7.3% 확대", slide_xml)
        self.assertIn('<a:dk1><a:srgbClr val="006060"/></a:dk1>', theme_xml)
        self.assertEqual([1], result["edited_slides"])
        self.assertIn("새 사실을 만들지 않고", result["policy"])

    def test_refine_rejects_edits_that_invent_a_number_and_writes_nothing(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        voice_path = ROOT / "hana-ppt-skill" / "assets" / "voice.json"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.pptx"
            self._fixture(source)
            edits_path = Path(directory) / "edits.json"
            edits_path.write_text(
                json.dumps({"1": {"0": "당기순이익 전년동기 대비 8.3% 증가"}}),
                encoding="utf-8",
            )
            out_path = Path(directory) / "out.pptx"
            with self.assertRaises(ValueError):
                RESTYLE.restyle(
                    source, brand_path, out_path, "hana-refine", voice_path=voice_path, edits_path=edits_path
                )
            self.assertFalse(out_path.exists())

    def test_refine_rejects_edits_that_drop_comparison_basis(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        voice_path = ROOT / "hana-ppt-skill" / "assets" / "voice.json"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.pptx"
            self._fixture(source)
            edits_path = Path(directory) / "edits.json"
            edits_path.write_text(
                json.dumps({"1": {"0": "당기순이익 7.3% 증가"}}),
                encoding="utf-8",
            )
            out_path = Path(directory) / "out.pptx"
            with self.assertRaises(ValueError):
                RESTYLE.restyle(
                    source, brand_path, out_path, "hana-refine", voice_path=voice_path, edits_path=edits_path
                )


class TextUnitsTests(unittest.TestCase):
    def test_extract_and_apply_round_trip_preserves_run_formatting(self):
        slide_xml = (
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            "<p:cSld><p:spTree><p:sp><p:txBody>"
            '<a:p><a:r><a:rPr b="1"/><a:t xml:space="preserve">굵은 제목 </a:t></a:r></a:p>'
            "<a:p><a:r><a:t>본문 불릿</a:t></a:r></a:p>"
            "</p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
        )
        units = TEXT_UNITS.extract_text_units(slide_xml)
        self.assertEqual(["굵은 제목 ", "본문 불릿"], [unit["text"] for unit in units])
        self.assertEqual([None, None], [unit["placeholder_type"] for unit in units])

        updated_xml = TEXT_UNITS.apply_text_edits(slide_xml, {1: "새 불릿 내용"})
        self.assertIn('<a:rPr b="1"/><a:t xml:space="preserve">굵은 제목 </a:t>', updated_xml)
        self.assertIn("<a:t>새 불릿 내용</a:t>", updated_xml)

    def test_extract_reports_placeholder_type_and_shape_name_as_hints(self):
        slide_xml = (
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            "<p:cSld><p:spTree>"
            "<p:sp><p:nvSpPr><p:cNvPr id=\"2\" name=\"제목 1\"/><p:nvPr>"
            '<p:ph type="title"/></p:nvPr></p:nvSpPr>'
            "<p:txBody><a:p><a:r><a:t>2026년 1분기 Highlights</a:t></a:r></a:p></p:txBody></p:sp>"
            '<p:sp><p:nvSpPr><p:cNvPr id="3" name="TextBox 2"/><p:nvPr/></p:nvSpPr>'
            "<p:txBody><a:p><a:r><a:t>면책 문구 원문</a:t></a:r></a:p></p:txBody></p:sp>"
            "</p:spTree></p:cSld></p:sld>"
        )
        units = TEXT_UNITS.extract_text_units(slide_xml)
        self.assertEqual("title", units[0]["placeholder_type"])
        self.assertEqual("제목 1", units[0]["shape_name"])
        self.assertIsNone(units[1]["placeholder_type"])
        self.assertEqual("TextBox 2", units[1]["shape_name"])

    def test_apply_text_edits_escapes_special_characters(self):
        slide_xml = (
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            "<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r>"
            "<a:t>원문</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
        )
        updated_xml = TEXT_UNITS.apply_text_edits(slide_xml, {0: "A&B <C>"})
        self.assertIn("<a:t>A&amp;B &lt;C&gt;</a:t>", updated_xml)


class VerifyEvidencePreservedTests(unittest.TestCase):
    def test_check_unit_allows_rewording_that_keeps_numbers_and_markers(self):
        original = "당기순이익 전년동기 대비 7.3% 증가"
        edited = "전년동기 대비 당기순이익이 7.3% 확대"
        self.assertEqual([], VERIFY_EVIDENCE.check_unit(original, edited))

    def test_check_unit_flags_invented_number(self):
        errors = VERIFY_EVIDENCE.check_unit("7.3% 증가", "8.3% 증가")
        self.assertTrue(any("수치 불일치" in error for error in errors))

    def test_check_unit_flags_dropped_comparison_marker(self):
        errors = VERIFY_EVIDENCE.check_unit("전년동기 대비 7.3% 증가", "7.3% 증가")
        self.assertTrue(any("비교 기준 누락" in error for error in errors))


class BuildDeckTests(unittest.TestCase):
    DECK_SPEC = {
        "schema_version": 1,
        "source": {"path": "x.pptx", "sha256": "0" * 64},
        "slides": [
            {
                "number": 1,
                "part": "ppt/slides/slide1.xml",
                "elements": [
                    {"kind": "shape", "name": "Title", "text": "2026년 1분기 경영실적 Highlights"},
                    {"kind": "shape", "name": "Bullet1", "text": "당기순이익 전년동기 대비 7.3% 증가"},
                ],
                "warnings": [],
            },
            {
                "number": 2,
                "part": "ppt/slides/slide2.xml",
                "elements": [
                    {"kind": "shape", "name": "Title", "text": "실적 요약 표"},
                    {"kind": "table", "name": "Table1", "rows": [["구분", "1Q26"], ["순이익", "1,234억"]]},
                ],
                "warnings": [],
            },
            {
                "number": 3,
                "part": "ppt/slides/slide3.xml",
                "elements": [
                    {"kind": "shape", "name": "Title", "text": "이미지 포함 슬라이드"},
                    {"kind": "image", "name": "Picture1"},
                ],
                "warnings": [],
            },
        ],
        "warnings": [],
    }

    def _write_deck_spec(self, directory: Path) -> Path:
        path = Path(directory) / "deck_spec.json"
        path.write_text(json.dumps(self.DECK_SPEC, ensure_ascii=False), encoding="utf-8")
        return path

    def test_build_produces_well_formed_xml_for_every_part(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = self._write_deck_spec(directory)
            out_path = Path(directory) / "out.pptx"
            BUILD.build_deck(deck_spec_path, brand_path, out_path)
            with zipfile.ZipFile(out_path) as archive:
                for name in archive.namelist():
                    if name.endswith(".xml") or name.endswith(".rels"):
                        ET.fromstring(archive.read(name))  # 예외 없이 파싱되면 정상 XML

    def test_build_places_title_bullets_table_and_reports_unreproduced_image(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = self._write_deck_spec(directory)
            out_path = Path(directory) / "out.pptx"
            result = BUILD.build_deck(deck_spec_path, brand_path, out_path)
            with zipfile.ZipFile(out_path) as archive:
                slide1 = archive.read("ppt/slides/slide1.xml").decode("utf-8")
                slide2 = archive.read("ppt/slides/slide2.xml").decode("utf-8")
                slide3 = archive.read("ppt/slides/slide3.xml").decode("utf-8")
        self.assertIn("2026년 1분기 경영실적 Highlights", slide1)
        self.assertIn("당기순이익 전년동기 대비 7.3% 증가", slide1)
        self.assertIn("<a:tbl>", slide2)
        self.assertIn("1,234억", slide2)
        self.assertIn("이미지 포함 슬라이드", slide3)
        self.assertEqual(3, result["slide_count"])
        self.assertTrue(any("image 요소는 재현하지 않음" in warning for warning in result["warnings"]))

    def test_build_applies_brand_theme_colors(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        brand = json.loads(brand_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = self._write_deck_spec(directory)
            out_path = Path(directory) / "out.pptx"
            BUILD.build_deck(deck_spec_path, brand_path, out_path)
            with zipfile.ZipFile(out_path) as archive:
                theme_xml = archive.read("ppt/theme/theme1.xml").decode("utf-8")
        color_map = RESTYLE.brand_theme_color_map(brand)
        self.assertIn(f'<a:accent1><a:srgbClr val="{color_map["accent1"]}"/></a:accent1>', theme_xml)
        self.assertIn(f'<a:dk1><a:srgbClr val="{color_map["dk1"]}"/></a:dk1>', theme_xml)

    def test_build_rejects_unapproved_brand(self):
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = self._write_deck_spec(directory)
            brand_path = Path(directory) / "brand.candidate.json"
            brand_path.write_text(
                json.dumps({"status": "candidate", "colors": {}, "typography": {}}), encoding="utf-8"
            )
            out_path = Path(directory) / "out.pptx"
            with self.assertRaises(ValueError):
                BUILD.build_deck(deck_spec_path, brand_path, out_path)

    ROLE_DECK_SPEC = {
        "schema_version": 1,
        "source": {"path": "x.pptx", "sha256": "0" * 64},
        "slides": [
            {
                "number": 1,
                "part": "ppt/slides/slide1.xml",
                "elements": [
                    {"kind": "shape", "name": "Title", "text": "2026년 1분기 경영실적 Highlights"},
                    {"kind": "shape", "name": "Date", "text": "2026.08.18"},
                    {"kind": "shape", "name": "Extra", "text": "무시되는 셋째 텍스트"},
                ],
                "warnings": [],
            },
            {
                "number": 2,
                "part": "ppt/slides/slide2.xml",
                "elements": [
                    {"kind": "shape", "name": "Title", "text": "수익성"},
                    {"kind": "shape", "name": "Body", "text": "금지된 본문 텍스트"},
                ],
                "warnings": [],
            },
            {
                "number": 3,
                "part": "ppt/slides/slide3.xml",
                "elements": [
                    {"kind": "shape", "name": "Title", "text": "DISCLAIMER"},
                    {"kind": "shape", "name": "P1", "text": "본 자료는 정보 제공 목적으로만 작성되었습니다."},
                    {"kind": "shape", "name": "P2", "text": "투자 판단의 최종 책임은 투자자 본인에게 있습니다."},
                ],
                "warnings": [],
            },
        ],
        "warnings": [],
    }

    def _write_role_deck_spec(self, directory: Path) -> Path:
        path = Path(directory) / "deck_spec.json"
        path.write_text(json.dumps(self.ROLE_DECK_SPEC, ensure_ascii=False), encoding="utf-8")
        return path

    def test_layout_plan_renders_cover_section_divider_and_disclaimer(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        layouts_path = ROOT / "hana-ppt-skill" / "assets" / "layouts.json"
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = self._write_role_deck_spec(directory)
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(
                json.dumps({"1": "cover", "2": "section-divider", "3": "disclaimer"}), encoding="utf-8"
            )
            out_path = Path(directory) / "out.pptx"
            result = BUILD.build_deck(
                deck_spec_path, brand_path, out_path, layouts_path=layouts_path, layout_plan_path=plan_path
            )
            with zipfile.ZipFile(out_path) as archive:
                cover = archive.read("ppt/slides/slide1.xml").decode("utf-8")
                divider = archive.read("ppt/slides/slide2.xml").decode("utf-8")
                disclaimer = archive.read("ppt/slides/slide3.xml").decode("utf-8")

        self.assertIn("2026.08.18", cover)
        self.assertNotIn("무시되는 셋째 텍스트", cover)
        self.assertTrue(any("표지 레이아웃은 제목·부제만 배치" in warning for warning in result["warnings"]))

        self.assertNotIn("금지된 본문 텍스트", divider)
        self.assertTrue(any("섹션 구분 레이아웃은 본문을 배치하지 않는다" in warning for warning in result["warnings"]))

    def test_layout_plan_draws_layouts_json_decorations_per_role(self):
        """cover/section-divider 장식은 실제 하나증권 배포 자료(hana-securities-2025-profile)를
        대조해 전체 배경을 primary_green으로 채우고 제목을 흰색으로 그리는 것으로 확정했다
        (references/hana-securities-cover-pattern-correction.md)."""
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        layouts_path = ROOT / "hana-ppt-skill" / "assets" / "layouts.json"
        brand = json.loads(brand_path.read_text(encoding="utf-8"))
        primary_green = brand["colors"]["primary_green"]["value"].lstrip("#").upper()
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = self._write_role_deck_spec(directory)
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(
                json.dumps({"1": "cover", "2": "section-divider", "3": "disclaimer"}), encoding="utf-8"
            )
            out_path = Path(directory) / "out.pptx"
            result = BUILD.build_deck(
                deck_spec_path, brand_path, out_path, layouts_path=layouts_path, layout_plan_path=plan_path
            )
            with zipfile.ZipFile(out_path) as archive:
                cover = archive.read("ppt/slides/slide1.xml").decode("utf-8")
                divider = archive.read("ppt/slides/slide2.xml").decode("utf-8")
                disclaimer = archive.read("ppt/slides/slide3.xml").decode("utf-8")

        for slide_xml in (cover, divider):
            self.assertIn('"Decoration Full Background"', slide_xml)
            self.assertIn(f'<a:srgbClr val="{primary_green}">', slide_xml)
            self.assertIn('<a:off x="0" y="0"/>', slide_xml)
            self.assertIn('<a:srgbClr val="FFFFFF"/>', slide_xml)  # 흰 제목
            self.assertLess(slide_xml.index("Decoration Full Background"), slide_xml.index('name="Title"'))
        self.assertTrue(
            any("표지 로고는 보호영역 미확정으로 자동 배치하지 않음" in warning for warning in result["warnings"])
        )

        self.assertNotIn("Decoration", disclaimer)
        self.assertIn("본 자료는 정보 제공 목적으로만 작성되었습니다.", disclaimer)
        self.assertIn("투자 판단의 최종 책임은 투자자 본인에게 있습니다.", disclaimer)

    def test_data_body_role_draws_divider_rule_under_title(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        brand = json.loads(brand_path.read_text(encoding="utf-8"))
        pale_mint = brand["colors"]["pale_mint"]["value"].lstrip("#").upper()
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = self._write_deck_spec(directory)
            out_path = Path(directory) / "out.pptx"
            BUILD.build_deck(deck_spec_path, brand_path, out_path)
            with zipfile.ZipFile(out_path) as archive:
                slide1 = archive.read("ppt/slides/slide1.xml").decode("utf-8")
        self.assertIn('"Decoration Divider Rule"', slide1)
        self.assertIn(f'<a:srgbClr val="{pale_mint}">', slide1)
        # 장식 도형이 제목/본문보다 spTree에서 먼저 나와야 뒤에 깔린다.
        self.assertLess(slide1.index("Decoration Divider Rule"), slide1.index('name="Title"'))

    CLOSING_DECK_SPEC = {
        "schema_version": 1,
        "source": {"path": "x.pptx", "sha256": "0" * 64},
        "slides": [
            {
                "number": 1,
                "part": "ppt/slides/slide1.xml",
                "elements": [
                    {"kind": "shape", "name": "Intro", "text": "본 자료의 세부 내용이나 하나증권 관련 문의는 아래로 연락 주시기 바랍니다"},
                    {"kind": "shape", "name": "Addr", "text": "주소 : 서울특별시 영등포구 의사당대로 82"},
                    {"kind": "shape", "name": "Tel", "text": "대표 전화 : 02-1588-3111"},
                ],
                "warnings": [],
            }
        ],
        "warnings": [],
    }

    def test_closing_role_draws_full_background_and_contact_box_without_standard_title(self):
        """실제 하나증권 자료(28p, 마지막 장) 근거: 전체 초록 배경 + 하단 좌측 안내문 +
        얇은 테두리 연락처 박스, 표준 큰 제목 placeholder는 없음."""
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        layouts_path = ROOT / "hana-ppt-skill" / "assets" / "layouts.json"
        brand = json.loads(brand_path.read_text(encoding="utf-8"))
        primary_green = brand["colors"]["primary_green"]["value"].lstrip("#").upper()
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = Path(directory) / "deck_spec.json"
            deck_spec_path.write_text(json.dumps(self.CLOSING_DECK_SPEC, ensure_ascii=False), encoding="utf-8")
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(json.dumps({"1": "closing"}), encoding="utf-8")
            out_path = Path(directory) / "out.pptx"
            BUILD.build_deck(
                deck_spec_path, brand_path, out_path, layouts_path=layouts_path, layout_plan_path=plan_path
            )
            with zipfile.ZipFile(out_path) as archive:
                slide1 = archive.read("ppt/slides/slide1.xml").decode("utf-8")
        self.assertIn(f'<a:srgbClr val="{primary_green}">', slide1)  # 전체 배경
        self.assertIn('"Decoration Closing Box"', slide1)
        self.assertIn("<a:noFill/>", slide1)  # 박스는 채우지 않고 테두리만
        self.assertIn("본 자료의 세부 내용이나", slide1)
        self.assertIn("주소 : 서울특별시 영등포구 의사당대로 82", slide1)
        self.assertNotIn('name="Title"', slide1)  # 표준 제목 placeholder는 안 씀

    def test_table_header_and_band_rows_use_brand_colors(self):
        """재무 현황(5p) 실제 자료의 진한 헤더·옅은 줄무늬를 근거로 한 표 스타일."""
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        brand = json.loads(brand_path.read_text(encoding="utf-8"))
        deep_teal = brand["colors"]["deep_teal"]["value"].lstrip("#").upper()
        pale_mint = brand["colors"]["pale_mint"]["value"].lstrip("#").upper()
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = self._write_deck_spec(directory)
            out_path = Path(directory) / "out.pptx"
            BUILD.build_deck(deck_spec_path, brand_path, out_path)
            with zipfile.ZipFile(out_path) as archive:
                slide2 = archive.read("ppt/slides/slide2.xml").decode("utf-8")
        bold_family = brand["typography"]["heading"]["families"][1]
        self.assertIn(f'<a:tcPr><a:solidFill><a:srgbClr val="{deep_teal}"/></a:solidFill></a:tcPr>', slide2)
        self.assertIn(
            f'<a:rPr b="1"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>'
            f'<a:latin typeface="{bold_family}"/></a:rPr>',
            slide2,
        )
        self.assertIn(f'<a:tcPr><a:solidFill><a:srgbClr val="{pale_mint}"/></a:solidFill></a:tcPr>', slide2)

    STAT_DECK_SPEC = {
        "schema_version": 1,
        "source": {"path": "x.pptx", "sha256": "0" * 64},
        "slides": [
            {
                "number": 1,
                "part": "ppt/slides/slide1.xml",
                "elements": [
                    {"kind": "shape", "name": "Title", "text": "국내·외 네트워크"},
                    {"kind": "shape", "name": "L1", "text": "전국 영업점 수"},
                    {"kind": "shape", "name": "V1", "text": "54개"},
                    {"kind": "shape", "name": "L2", "text": "복합 점포"},
                    {"kind": "shape", "name": "V2", "text": "44개"},
                ],
                "warnings": [],
            }
        ],
        "warnings": [],
    }

    def test_strategic_kpi_renders_label_value_columns(self):
        """국내·외 네트워크(7p)의 통계 블록 근거. columns는 layout-plan에 명시해야 한다."""
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        layouts_path = ROOT / "hana-ppt-skill" / "assets" / "layouts.json"
        brand = json.loads(brand_path.read_text(encoding="utf-8"))
        primary_green = brand["colors"]["primary_green"]["value"].lstrip("#").upper()
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = Path(directory) / "deck_spec.json"
            deck_spec_path.write_text(json.dumps(self.STAT_DECK_SPEC, ensure_ascii=False), encoding="utf-8")
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(json.dumps({"1": {"role": "strategic-kpi", "columns": 2}}), encoding="utf-8")
            out_path = Path(directory) / "out.pptx"
            BUILD.build_deck(
                deck_spec_path, brand_path, out_path, layouts_path=layouts_path, layout_plan_path=plan_path
            )
            with zipfile.ZipFile(out_path) as archive:
                slide1 = archive.read("ppt/slides/slide1.xml").decode("utf-8")
        bold_family = brand["typography"]["heading"]["families"][1]
        self.assertIn("전국 영업점 수", slide1)
        self.assertIn(f'<a:rPr b="1" sz="3200"><a:solidFill><a:srgbClr val="{primary_green}"/>', slide1)
        self.assertIn(f'<a:latin typeface="{bold_family}"/>', slide1)  # 합성 볼드 대신 실제 굵기 폰트
        self.assertIn("54개", slide1)
        self.assertIn("44개", slide1)

    def test_strategic_kpi_requires_columns_in_layout_plan(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        layouts_path = ROOT / "hana-ppt-skill" / "assets" / "layouts.json"
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = Path(directory) / "deck_spec.json"
            deck_spec_path.write_text(json.dumps(self.STAT_DECK_SPEC, ensure_ascii=False), encoding="utf-8")
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(json.dumps({"1": "strategic-kpi"}), encoding="utf-8")
            out_path = Path(directory) / "out.pptx"
            with self.assertRaises(ValueError):
                BUILD.build_deck(
                    deck_spec_path, brand_path, out_path, layouts_path=layouts_path, layout_plan_path=plan_path
                )

    def test_strategic_kpi_rejects_uneven_label_value_count(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        layouts_path = ROOT / "hana-ppt-skill" / "assets" / "layouts.json"
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = Path(directory) / "deck_spec.json"
            deck_spec_path.write_text(json.dumps(self.STAT_DECK_SPEC, ensure_ascii=False), encoding="utf-8")
            plan_path = Path(directory) / "plan.json"
            # columns=3인데 [레이블,값] 쌍 4개(8개 텍스트)뿐이라 3*2=6과 맞지 않는다.
            plan_path.write_text(json.dumps({"1": {"role": "strategic-kpi", "columns": 3}}), encoding="utf-8")
            out_path = Path(directory) / "out.pptx"
            with self.assertRaises(ValueError):
                BUILD.build_deck(
                    deck_spec_path, brand_path, out_path, layouts_path=layouts_path, layout_plan_path=plan_path
                )

    CARD_DECK_SPEC = {
        "schema_version": 1,
        "source": {"path": "x.pptx", "sha256": "0" * 64},
        "slides": [
            {
                "number": 1,
                "part": "ppt/slides/slide1.xml",
                "elements": [
                    {"kind": "shape", "name": "Title", "text": "주요 사업영역"},
                    {"kind": "shape", "name": "H1", "text": "WM"},
                    {"kind": "shape", "name": "B1", "text": "개인 또는 법인대상 금융상품 판매"},
                    {"kind": "shape", "name": "H2", "text": "IB"},
                    {"kind": "shape", "name": "B2", "text": "기업금융 업무 전반 수행"},
                ],
                "warnings": [],
            }
        ],
        "warnings": [],
    }

    def test_executive_summary_renders_card_columns(self):
        """주요 사업영역(11p)의 3열 카드(상단 바+헤더+불릿) 근거. 여기서는 2열로 검증한다."""
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        layouts_path = ROOT / "hana-ppt-skill" / "assets" / "layouts.json"
        brand = json.loads(brand_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = Path(directory) / "deck_spec.json"
            deck_spec_path.write_text(json.dumps(self.CARD_DECK_SPEC, ensure_ascii=False), encoding="utf-8")
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(json.dumps({"1": {"role": "executive-summary", "columns": 2}}), encoding="utf-8")
            out_path = Path(directory) / "out.pptx"
            BUILD.build_deck(
                deck_spec_path, brand_path, out_path, layouts_path=layouts_path, layout_plan_path=plan_path
            )
            with zipfile.ZipFile(out_path) as archive:
                slide1 = archive.read("ppt/slides/slide1.xml").decode("utf-8")
        bold_family = brand["typography"]["heading"]["families"][1]
        self.assertIn('"Decoration Card Top Bar"', slide1)
        self.assertIn('"Decoration Card Header"', slide1)
        self.assertIn('<a:pPr algn="ctr"/>', slide1)
        self.assertIn(f'<a:latin typeface="{bold_family}"/>', slide1)  # 합성 볼드 대신 실제 굵기 폰트
        self.assertIn("WM", slide1)
        self.assertIn("개인 또는 법인대상 금융상품 판매", slide1)
        self.assertIn("IB", slide1)

    def test_executive_summary_rejects_uneven_column_split(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        layouts_path = ROOT / "hana-ppt-skill" / "assets" / "layouts.json"
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = Path(directory) / "deck_spec.json"
            deck_spec_path.write_text(json.dumps(self.CARD_DECK_SPEC, ensure_ascii=False), encoding="utf-8")
            plan_path = Path(directory) / "plan.json"
            # 텍스트 4개를 columns=3으로는 고르게 나눌 수 없다.
            plan_path.write_text(json.dumps({"1": {"role": "executive-summary", "columns": 3}}), encoding="utf-8")
            out_path = Path(directory) / "out.pptx"
            with self.assertRaises(ValueError):
                BUILD.build_deck(
                    deck_spec_path, brand_path, out_path, layouts_path=layouts_path, layout_plan_path=plan_path
                )

    def test_layout_plan_requires_both_layouts_and_plan(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        layouts_path = ROOT / "hana-ppt-skill" / "assets" / "layouts.json"
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = self._write_role_deck_spec(directory)
            out_path = Path(directory) / "out.pptx"
            with self.assertRaises(ValueError):
                BUILD.build_deck(deck_spec_path, brand_path, out_path, layouts_path=layouts_path)

    def test_layout_plan_rejects_unknown_role(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        layouts_path = ROOT / "hana-ppt-skill" / "assets" / "layouts.json"
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = self._write_role_deck_spec(directory)
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(json.dumps({"1": "not-a-real-role"}), encoding="utf-8")
            out_path = Path(directory) / "out.pptx"
            with self.assertRaises(ValueError):
                BUILD.build_deck(
                    deck_spec_path, brand_path, out_path, layouts_path=layouts_path, layout_plan_path=plan_path
                )

    def test_layout_plan_rejects_unknown_slide_number(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        layouts_path = ROOT / "hana-ppt-skill" / "assets" / "layouts.json"
        with tempfile.TemporaryDirectory() as directory:
            deck_spec_path = self._write_role_deck_spec(directory)
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(json.dumps({"99": "cover"}), encoding="utf-8")
            out_path = Path(directory) / "out.pptx"
            with self.assertRaises(ValueError):
                BUILD.build_deck(
                    deck_spec_path, brand_path, out_path, layouts_path=layouts_path, layout_plan_path=plan_path
                )


class VisualCheckTests(unittest.TestCase):
    def _brand(self):
        return json.loads((ROOT / "hana-ppt-skill" / "assets" / "brand.json").read_text(encoding="utf-8"))

    def _layouts(self):
        return json.loads((ROOT / "hana-ppt-skill" / "assets" / "layouts.json").read_text(encoding="utf-8"))

    def test_checklist_resolves_element_colors_to_brand_hex(self):
        brand, layouts = self._brand(), self._layouts()
        checklist, confidence, note = VISUAL_CHECK.checklist_for_role("cover", layouts, brand)
        self.assertTrue(any("primary_green(009070)" in item for item in checklist))
        self.assertEqual("hana-securities-evidenced", confidence)
        self.assertTrue(note)

    def test_checklist_flags_undefined_role(self):
        brand, layouts = self._brand(), self._layouts()
        checklist, confidence, _ = VISUAL_CHECK.checklist_for_role("not-a-real-role", layouts, brand)
        self.assertEqual("undefined-role", confidence)
        self.assertTrue(checklist)

    def test_review_packet_defaults_missing_slides_to_data_body(self):
        brand, layouts = self._brand(), self._layouts()
        manifest = {"slides": [{"number": 1, "path": "/x/1.jpg"}]}
        packet = VISUAL_CHECK.build_review_packet(manifest, {}, layouts, brand)
        self.assertEqual("data-body", packet["slides"][0]["role"])
        self.assertEqual(brand["colors"]["primary_green"]["value"], packet["brand_colors"]["primary_green"])

    def test_review_packet_includes_prohibited_content_for_section_divider(self):
        brand, layouts = self._brand(), self._layouts()
        manifest = {"slides": [{"number": 1, "path": "/x/1.jpg"}]}
        packet = VISUAL_CHECK.build_review_packet(manifest, {1: {"role": "section-divider"}}, layouts, brand)
        self.assertTrue(any("금지:" in item for item in packet["slides"][0]["checklist"]))

    @unittest.skipUnless(VISUAL_CHECK.PIL_AVAILABLE, "Pillow가 설치되지 않음")
    def test_mechanical_background_check_matches_solid_primary_green_image(self):
        from PIL import Image

        brand, layouts = self._brand(), self._layouts()
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "cover.jpg"
            hex_value = brand["colors"]["primary_green"]["value"].lstrip("#")
            rgb = tuple(int(hex_value[i : i + 2], 16) for i in (0, 2, 4))
            Image.new("RGB", (200, 150), rgb).save(image_path)
            manifest = {"slides": [{"number": 1, "path": str(image_path)}]}
            packet = VISUAL_CHECK.build_review_packet(manifest, {1: {"role": "cover"}}, layouts, brand)
        check = packet["slides"][0]["mechanical_background_check"]
        self.assertEqual("match", check["verdict"])
        self.assertLessEqual(check["distance"], 12)

    @unittest.skipUnless(VISUAL_CHECK.PIL_AVAILABLE, "Pillow가 설치되지 않음")
    def test_mechanical_background_check_flags_wrong_color(self):
        from PIL import Image

        brand, layouts = self._brand(), self._layouts()
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "cover.jpg"
            Image.new("RGB", (200, 150), (255, 0, 0)).save(image_path)  # 완전히 다른 색
            manifest = {"slides": [{"number": 1, "path": str(image_path)}]}
            packet = VISUAL_CHECK.build_review_packet(manifest, {1: {"role": "cover"}}, layouts, brand)
        check = packet["slides"][0]["mechanical_background_check"]
        self.assertEqual("mismatch", check["verdict"])

    def test_build_check_writes_packet_file(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        layouts_path = ROOT / "hana-ppt-skill" / "assets" / "layouts.json"
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "render_manifest.json"
            manifest_path.write_text(
                json.dumps({"slides": [{"number": 1, "path": "/x/1.jpg"}]}), encoding="utf-8"
            )
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(json.dumps({"1": "disclaimer"}), encoding="utf-8")
            out_path = Path(directory) / "packet.json"
            packet = VISUAL_CHECK.build_check(
                manifest_path, layouts_path, brand_path, out_path, layout_plan_path=plan_path
            )
            self.assertTrue(out_path.is_file())
            reloaded = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(packet, reloaded)
        self.assertEqual("disclaimer", packet["slides"][0]["role"])


class QualityCheckTests(unittest.TestCase):
    def test_check_content_types_flags_missing_override_target(self):
        parts = {
            "[Content_Types].xml": (
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Override PartName="/ppt/presentation.xml" ContentType="x"/>'
                '<Override PartName="/ppt/slides/slide1.xml" ContentType="x"/>'
                "</Types>"
            ).encode("utf-8"),
            "ppt/presentation.xml": b"<x/>",
        }
        errors = QUALITY_CHECK.check_content_types(parts)
        self.assertTrue(any("ppt/slides/slide1.xml" in error for error in errors))

    def test_check_relationships_flags_dangling_target_and_allows_external(self):
        parts = {
            "ppt/_rels/presentation.xml.rels": (
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="x" Target="slides/slide1.xml"/>'
                '<Relationship Id="rId2" Type="x" Target="https://example.com" TargetMode="External"/>'
                "</Relationships>"
            ).encode("utf-8"),
        }
        errors = QUALITY_CHECK.check_relationships(parts)
        self.assertEqual(1, len(errors))
        self.assertIn("slides/slide1.xml", errors[0])

    def test_check_relationships_resolves_valid_target_without_touching_filesystem(self):
        parts = {
            "ppt/_rels/presentation.xml.rels": (
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="x" Target="slides/slide1.xml"/>'
                "</Relationships>"
            ).encode("utf-8"),
            "ppt/slides/slide1.xml": b"<x/>",
        }
        self.assertEqual([], QUALITY_CHECK.check_relationships(parts))

    def test_check_aspect_ratio_flags_mismatch(self):
        parts = {
            "ppt/presentation.xml": (
                '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                '<p:sldSz cx="9144000" cy="6858000"/></p:presentation>'
            ).encode("utf-8")
        }
        errors = QUALITY_CHECK.check_aspect_ratio(parts, {"canvas": {"aspect_ratio": 1.444}})
        self.assertEqual(1, len(errors))

    def test_check_slide_count_flags_mismatch(self):
        parts = {"ppt/slides/slide1.xml": b"<x/>"}
        errors = QUALITY_CHECK.check_slide_count(parts, {"slides": [1, 2]})
        self.assertTrue(errors)

    SLIDE_XML_TEMPLATE = (
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        "<p:cSld><p:spTree>{shapes}</p:spTree></p:cSld></p:sld>"
    )

    @staticmethod
    def _shape(name: str, x: int, y: int, cx: int, cy: int) -> str:
        return (
            f'<p:sp><p:nvSpPr><p:cNvPr id="1" name="{name}"/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm></p:spPr></p:sp>'
        )

    def test_check_shape_bounds_flags_out_of_bounds_and_overlap_but_ignores_decorations(self):
        cx, cy = 9144000, 6858000
        shapes = (
            self._shape("Off Slide Text", -1000, 0, 500000, 500000)
            + self._shape("Overlap A", 0, 0, 2000000, 2000000)
            + self._shape("Overlap B", 100000, 100000, 2000000, 2000000)
            + self._shape("Decoration Full Background", -500000, -500000, cx + 1000000, cy + 1000000)
        )
        parts = {
            "ppt/presentation.xml": (
                f'<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                f'<p:sldSz cx="{cx}" cy="{cy}"/></p:presentation>'
            ).encode("utf-8"),
            "ppt/slides/slide1.xml": self.SLIDE_XML_TEMPLATE.format(shapes=shapes).encode("utf-8"),
        }
        errors = QUALITY_CHECK.check_shape_bounds(parts)
        self.assertTrue(any("Off Slide Text" in e and "경계를 벗어남" in e for e in errors))
        self.assertTrue(any("Overlap A" in e and "Overlap B" in e for e in errors))
        self.assertFalse(any("Decoration" in e for e in errors))

    def test_run_passes_cleanly_on_build_deck_output_with_card_and_stat_roles(self):
        """실행 시 executive-summary/strategic-kpi 장식 도형 이름이 Decoration 접두사를
        빠뜨리면 이 테스트가 겹침 오탐으로 실패한다(회귀 방지)."""
        deck_spec = {
            "schema_version": 1,
            "source": {"path": "x.pptx", "sha256": "0" * 64},
            "slides": [
                {
                    "number": 1,
                    "part": "ppt/slides/slide1.xml",
                    "elements": [
                        {"kind": "shape", "name": "Title", "text": "국내·외 네트워크"},
                        {"kind": "shape", "name": "L1", "text": "전국 영업점 수"},
                        {"kind": "shape", "name": "V1", "text": "54개"},
                    ],
                    "warnings": [],
                },
                {
                    "number": 2,
                    "part": "ppt/slides/slide2.xml",
                    "elements": [
                        {"kind": "shape", "name": "Title", "text": "주요 사업영역"},
                        {"kind": "shape", "name": "H1", "text": "WM"},
                        {"kind": "shape", "name": "B1", "text": "개인대상 금융상품 판매"},
                    ],
                    "warnings": [],
                },
            ],
            "warnings": [],
        }
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        layouts_path = ROOT / "hana-ppt-skill" / "assets" / "layouts.json"
        with tempfile.TemporaryDirectory() as directory:
            spec_path = Path(directory) / "deck_spec.json"
            spec_path.write_text(json.dumps(deck_spec, ensure_ascii=False), encoding="utf-8")
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(
                json.dumps({"1": {"role": "strategic-kpi", "columns": 1}, "2": {"role": "executive-summary", "columns": 1}}),
                encoding="utf-8",
            )
            out_path = Path(directory) / "out.pptx"
            BUILD.build_deck(
                spec_path, brand_path, out_path, layouts_path=layouts_path, layout_plan_path=plan_path
            )
            result = QUALITY_CHECK.run(out_path, brand_path=brand_path, deck_spec_path=spec_path)
        self.assertEqual("pass", result["status"])
        self.assertEqual([], result["errors"])

    def test_run_flags_slide_count_mismatch_against_deck_spec(self):
        brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
        with tempfile.TemporaryDirectory() as directory:
            spec_path = Path(directory) / "deck_spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source": {"path": "x.pptx", "sha256": "0" * 64},
                        "slides": [
                            {"number": 1, "part": "ppt/slides/slide1.xml", "elements": [], "warnings": []},
                            {"number": 2, "part": "ppt/slides/slide2.xml", "elements": [], "warnings": []},
                        ],
                        "warnings": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            out_path = Path(directory) / "out.pptx"
            # deck_spec에는 슬라이드가 2개지만 build_deck.py에는 1개짜리만 넘긴다.
            one_slide_spec_path = Path(directory) / "one_slide.json"
            one_slide_spec_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source": {"path": "x.pptx", "sha256": "0" * 64},
                        "slides": [{"number": 1, "part": "ppt/slides/slide1.xml", "elements": [], "warnings": []}],
                        "warnings": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            BUILD.build_deck(one_slide_spec_path, brand_path, out_path)
            result = QUALITY_CHECK.run(out_path, deck_spec_path=spec_path)
        self.assertEqual("fail", result["status"])
        self.assertTrue(any("슬라이드 수 불일치" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
