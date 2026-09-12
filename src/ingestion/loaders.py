"""
Document loaders for PDF, DOCX, and HTML sources.
Arabic PDFs must be spot-checked manually -- loaders can silently mangle RTL text.
"""

from pathlib import Path
from typing import Any


def load_pdf(path: str | Path) -> list[dict[str, Any]]:
    """TODO (Week 2): implement with pypdf + Arabic RTL sanity check."""
    raise NotImplementedError("Week 2: implement PDF loading with pypdf")


def load_docx(path: str | Path) -> list[dict[str, Any]]:
    """TODO (Week 2): implement with python-docx."""
    raise NotImplementedError("Week 2: implement DOCX loading with python-docx")


def load_html(path_or_url: str) -> list[dict[str, Any]]:
    """TODO (Week 2): implement with BeautifulSoup, from scratch."""
    raise NotImplementedError("Week 2: implement HTML loading with BeautifulSoup")
