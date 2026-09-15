"""Tests for src/ingestion/loaders.py."""

from pathlib import Path

import pytest

from scripts.generate_test_fixtures import EXPECTED_FIXTURES, FIXTURES_DIR, generate_fixtures
from src.ingestion.loaders import load_docx, load_pdf


@pytest.fixture(scope="session", autouse=True)
def _ensure_fixtures() -> None:
    """Regenerate tests/fixtures/ on demand -- it is gitignored, not committed."""
    missing = [name for name in EXPECTED_FIXTURES if not (FIXTURES_DIR / name).exists()]
    if missing:
        generate_fixtures()


class TestLoadDocx:
    def test_extracts_french_paragraphs(self) -> None:
        result = load_docx(FIXTURES_DIR / "sample_fr.docx")

        assert len(result) == 1
        doc = result[0]
        assert doc["page"] is None
        assert "Marie Dubois" in doc["text"]
        assert doc["source"] == str(FIXTURES_DIR / "sample_fr.docx")
        assert doc["metadata"]["total_paragraphs"] == 3
        assert doc["metadata"]["has_arabic"] is False
        assert doc["metadata"]["corruption_risk"] is False

    def test_detects_arabic_text(self) -> None:
        result = load_docx(FIXTURES_DIR / "sample_ar.docx")

        doc = result[0]
        assert doc["metadata"]["has_arabic"] is True
        assert doc["metadata"]["corruption_risk"] is False
        assert "�" not in doc["text"]

    def test_raises_file_not_found_for_missing_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_docx(FIXTURES_DIR / "does_not_exist.docx")

    def test_raises_value_error_for_empty_document(self) -> None:
        with pytest.raises(ValueError):
            load_docx(FIXTURES_DIR / "sample_empty.docx")


class TestLoadPdf:
    def test_extracts_french_text(self) -> None:
        result = load_pdf(FIXTURES_DIR / "sample_fr.pdf")

        assert len(result) == 1
        doc = result[0]
        assert set(doc.keys()) == {"text", "source", "page", "metadata"}
        assert doc["page"] == 1
        assert doc["source"] == str(FIXTURES_DIR / "sample_fr.pdf")
        assert "Marie Dubois" in doc["text"]

    def test_detects_arabic_text(self) -> None:
        result = load_pdf(FIXTURES_DIR / "sample_ar.pdf")

        doc = result[0]
        assert doc["metadata"]["has_arabic"] is True
        assert doc["metadata"]["corruption_risk"] is False

    def test_metadata_contains_total_pages(self) -> None:
        result = load_pdf(FIXTURES_DIR / "sample_fr.pdf")

        for doc in result:
            assert "total_pages" in doc["metadata"]
            assert doc["metadata"]["total_pages"] == len(result)

    def test_raises_file_not_found_for_missing_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_pdf(Path(FIXTURES_DIR) / "does_not_exist.pdf")
