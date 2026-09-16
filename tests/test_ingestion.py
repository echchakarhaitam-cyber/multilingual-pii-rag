"""Tests for src/ingestion/loaders.py."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from scripts.generate_test_fixtures import EXPECTED_FIXTURES, FIXTURES_DIR, generate_fixtures
from src.ingestion.loaders import load_docx, load_html, load_pdf


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


class TestLoadHtml:
    def test_extracts_french_text_and_strips_boilerplate(self) -> None:
        result = load_html(str(FIXTURES_DIR / "sample_fr.html"))

        assert len(result) == 1
        doc = result[0]
        assert doc["page"] is None
        assert doc["source"] == str(FIXTURES_DIR / "sample_fr.html")
        assert "Marie Dubois" in doc["text"]
        assert "Home About Contact" not in doc["text"]
        assert "Site Header Menu" not in doc["text"]
        assert "Related links sidebar" not in doc["text"]
        assert "Copyright 2026 Site Footer" not in doc["text"]
        assert "tracking pixel" not in doc["text"]
        assert doc["metadata"]["has_arabic"] is False
        assert doc["metadata"]["corruption_risk"] is False
        assert doc["metadata"]["content_length"] == len(doc["text"])

    def test_detects_arabic_text(self) -> None:
        result = load_html(str(FIXTURES_DIR / "sample_ar.html"))

        doc = result[0]
        assert doc["metadata"]["has_arabic"] is True
        assert doc["metadata"]["corruption_risk"] is False
        assert "Home About Contact" not in doc["text"]

    def test_raises_file_not_found_for_missing_local_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_html(str(FIXTURES_DIR / "does_not_exist.html"))

    def test_raises_value_error_for_empty_content(self) -> None:
        with pytest.raises(ValueError):
            load_html(str(FIXTURES_DIR / "sample_empty.html"))

    def test_fetches_url_via_requests_get(self) -> None:
        mock_response = Mock()
        mock_response.text = "<html><body><p>Hello from mocked URL</p></body></html>"
        mock_response.raise_for_status = Mock()

        with patch("src.ingestion.loaders.requests.get", return_value=mock_response) as mock_get:
            result = load_html("https://example.com/page.html")

        mock_get.assert_called_once_with("https://example.com/page.html", timeout=10)
        doc = result[0]
        assert doc["source"] == "https://example.com/page.html"
        assert "Hello from mocked URL" in doc["text"]

    def test_raises_value_error_on_timeout(self) -> None:
        with patch(
            "src.ingestion.loaders.requests.get",
            side_effect=requests.exceptions.Timeout,
        ):
            with pytest.raises(ValueError, match="(?i)timeout"):
                load_html("https://example.com/slow-page")

    def test_raises_value_error_on_unreachable_url(self) -> None:
        with patch(
            "src.ingestion.loaders.requests.get",
            side_effect=requests.exceptions.ConnectionError,
        ):
            with pytest.raises(ValueError):
                load_html("https://example.com/unreachable")
