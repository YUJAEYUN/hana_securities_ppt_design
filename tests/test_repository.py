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


if __name__ == "__main__":
    unittest.main()
