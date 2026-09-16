"""
Document loaders for PDF, DOCX, and HTML sources.
Arabic PDFs must be spot-checked manually -- loaders can silently mangle RTL text.
"""

import logging
import re
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

BOILERPLATE_TAGS = ("nav", "header", "footer", "script", "style", "aside")
URL_FETCH_TIMEOUT_SECONDS = 10

logger = logging.getLogger(__name__)

ARABIC_PATTERN = re.compile(r"[؀-ۿ]")
REPLACEMENT_CHAR = "�"
CORRUPTION_RATIO_THRESHOLD = 0.1


def _assess_arabic_corruption(text: str) -> tuple[bool, bool]:
    """Return (has_arabic, corruption_risk) for a page of extracted text."""
    arabic_count = len(ARABIC_PATTERN.findall(text))
    has_arabic = arabic_count > 0

    replacement_count = text.count(REPLACEMENT_CHAR)
    corruption_risk = has_arabic and replacement_count > arabic_count * CORRUPTION_RATIO_THRESHOLD

    return has_arabic, corruption_risk


def load_pdf(path: str | Path) -> list[dict[str, Any]]:
    """Extract text per page from a PDF, flagging Arabic RTL corruption risk."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    try:
        reader = PdfReader(str(path))
    except PdfReadError as exc:
        raise ValueError(f"Unreadable PDF: {path}") from exc

    total_pages = len(reader.pages)
    documents: list[dict[str, Any]] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        has_arabic, corruption_risk = _assess_arabic_corruption(text)

        if corruption_risk:
            logger.warning(
                "Possible Arabic text corruption on page %d of %s "
                "(replacement characters exceed 10%% of Arabic character count)",
                page_number,
                path,
            )

        documents.append(
            {
                "text": text,
                "source": str(path),
                "page": page_number,
                "metadata": {
                    "total_pages": total_pages,
                    "has_arabic": has_arabic,
                    "corruption_risk": corruption_risk,
                },
            }
        )

    if not any(doc["text"].strip() for doc in documents):
        raise ValueError(f"No text extracted from PDF: {path}")

    return documents


def load_docx(path: str | Path) -> list[dict[str, Any]]:
    """Extract paragraph text from a DOCX, flagging Arabic RTL corruption risk."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX not found: {path}")

    try:
        document = Document(str(path))
    except PackageNotFoundError as exc:
        raise ValueError(f"Unreadable DOCX: {path}") from exc

    paragraphs = [p.text for p in document.paragraphs]
    text = "\n".join(paragraphs)

    if not text.strip():
        raise ValueError(f"No text extracted from DOCX: {path}")

    has_arabic, corruption_risk = _assess_arabic_corruption(text)

    if corruption_risk:
        logger.warning(
            "Possible Arabic text corruption in %s "
            "(replacement characters exceed 10%% of Arabic character count)",
            path,
        )

    return [
        {
            "text": text,
            "source": str(path),
            "page": None,
            "metadata": {
                "total_paragraphs": len(paragraphs),
                "has_arabic": has_arabic,
                "corruption_risk": corruption_risk,
            },
        }
    ]


def load_html(path_or_url: str) -> list[dict[str, Any]]:
    """Extract text from local HTML or a URL, stripping boilerplate and
    flagging Arabic RTL corruption risk."""
    if path_or_url.startswith(("http://", "https://")):
        try:
            response = requests.get(path_or_url, timeout=URL_FETCH_TIMEOUT_SECONDS)
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise ValueError(
                f"Timeout fetching URL after {URL_FETCH_TIMEOUT_SECONDS}s: {path_or_url}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ValueError(f"Unreachable URL: {path_or_url}") from exc

        html_content = response.text
        source = path_or_url
    else:
        path = Path(path_or_url)
        if not path.exists():
            raise FileNotFoundError(f"HTML file not found: {path}")
        html_content = path.read_text(encoding="utf-8")
        source = str(path)

    soup = BeautifulSoup(html_content, "html.parser")
    for tag_name in BOILERPLATE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    if not text.strip():
        raise ValueError(f"No text extracted from HTML: {source}")

    has_arabic, corruption_risk = _assess_arabic_corruption(text)

    if corruption_risk:
        logger.warning(
            "Possible Arabic text corruption in %s "
            "(replacement characters exceed 10%% of Arabic character count)",
            source,
        )

    return [
        {
            "text": text,
            "source": source,
            "page": None,
            "metadata": {
                "has_arabic": has_arabic,
                "corruption_risk": corruption_risk,
                "content_length": len(text),
            },
        }
    ]
