from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


HARNESS = load_module("task_harness", ROOT / "tools" / "task_harness.py")
INGEST = load_module("ingest_deck", ROOT / "hana-ppt-skill" / "scripts" / "ingest_deck.py")
RENDER = load_module("render_slides", ROOT / "hana-ppt-skill" / "scripts" / "render_slides.py")
RESTYLE = load_module("restyle_deck", ROOT / "hana-ppt-skill" / "scripts" / "restyle_deck.py")


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

    def _fixture(self, path: Path) -> None:
        files = {
            "ppt/presentation.xml": (
                '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>'
            ),
            "ppt/theme/theme1.xml": self.THEME_XML,
            "ppt/slides/slide1.xml": (
                '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                "<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r>"
                "<a:t>원문 유지</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
            ),
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

    def test_hana_refine_mode_is_not_yet_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.pptx"
            self._fixture(source)
            brand_path = ROOT / "hana-ppt-skill" / "assets" / "brand.json"
            out_path = Path(directory) / "out.pptx"
            with self.assertRaises(NotImplementedError):
                RESTYLE.restyle(source, brand_path, out_path, "hana-refine")


if __name__ == "__main__":
    unittest.main()
