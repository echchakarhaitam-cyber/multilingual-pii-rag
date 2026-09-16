"""
Generate deterministic test fixtures for the ingestion loaders.

Fixtures are not committed to git (tests/fixtures/ is gitignored) -- run this
script directly, or let tests/test_ingestion.py regenerate them on demand:

    python scripts/generate_test_fixtures.py
"""

from pathlib import Path

from docx import Document
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

EXPECTED_FIXTURES = [
    "sample_fr.docx",
    "sample_ar.docx",
    "sample_empty.docx",
    "sample_fr.pdf",
    "sample_ar.pdf",
    "sample_fr.html",
    "sample_ar.html",
    "sample_empty.html",
]

FRENCH_PARAGRAPHS = [
    "Bonjour, je m'appelle Marie Dubois et j'habite a Paris.",
    "Mon numero de telephone est le 06 12 34 56 78.",
    "Je travaille comme ingenieure logicielle depuis cinq ans.",
]

ARABIC_PARAGRAPHS = [
    "مرحباً، اسمي أحمد بن علي وأعيش في الرباط.",
    "رقم هاتفي هو 0612345678 وبريدي الإلكتروني ahmed@example.com.",
    "أعمل مهندس برمجيات منذ خمس سنوات.",
]

HTML_HEAD = (
    '<head><meta charset="utf-8"><title>Fixture</title>'
    "<style>body { color: black; }</style>"
    '<script>console.log("tracking pixel");</script>'
    "</head>"
)
# No <title>: get_text() extracts head/title text too, since only
# BOILERPLATE_TAGS are stripped -- the empty fixture must have nothing left.
EMPTY_HTML_HEAD = (
    "<head><style>body { color: black; }</style>"
    '<script>console.log("tracking pixel");</script>'
    "</head>"
)
HTML_BOILERPLATE = (
    "<nav>Home About Contact</nav>"
    "<header>Site Header Menu</header>"
    "<aside>Related links sidebar</aside>"
)
HTML_FOOTER = "<footer>Copyright 2026 Site Footer</footer>"

# Arabic-capable TrueType fonts to try, in order, across common platforms.
CANDIDATE_ARABIC_FONTS = [
    Path(r"C:\Windows\Fonts\tahoma.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
]


def _find_arabic_font() -> Path:
    for candidate in CANDIDATE_ARABIC_FONTS:
        if candidate.exists():
            return candidate
    raise RuntimeError(
        "No Arabic-capable TrueType font found on this machine. Install one "
        "(e.g. Noto Naskh Arabic) or add its path to CANDIDATE_ARABIC_FONTS "
        "in scripts/generate_test_fixtures.py."
    )


def _generate_docx_fixtures() -> None:
    fr_doc = Document()
    for paragraph in FRENCH_PARAGRAPHS:
        fr_doc.add_paragraph(paragraph)
    fr_doc.save(FIXTURES_DIR / "sample_fr.docx")

    ar_doc = Document()
    for paragraph in ARABIC_PARAGRAPHS:
        ar_doc.add_paragraph(paragraph)
    ar_doc.save(FIXTURES_DIR / "sample_ar.docx")

    Document().save(FIXTURES_DIR / "sample_empty.docx")


def _generate_pdf_fixtures() -> None:
    fr_canvas = canvas.Canvas(str(FIXTURES_DIR / "sample_fr.pdf"))
    fr_canvas.setFont("Helvetica", 12)
    y = 750
    for paragraph in FRENCH_PARAGRAPHS:
        fr_canvas.drawString(72, y, paragraph)
        y -= 20
    fr_canvas.save()

    pdfmetrics.registerFont(TTFont("ArabicFixtureFont", str(_find_arabic_font())))

    ar_canvas = canvas.Canvas(str(FIXTURES_DIR / "sample_ar.pdf"))
    ar_canvas.setFont("ArabicFixtureFont", 14)
    y = 750
    for paragraph in ARABIC_PARAGRAPHS:
        ar_canvas.drawString(72, y, paragraph)
        y -= 25
    ar_canvas.save()


def _build_html_page(main_content: str, lang: str) -> str:
    return (
        f'<!DOCTYPE html><html lang="{lang}">{HTML_HEAD}<body>'
        f"{HTML_BOILERPLATE}<main>{main_content}</main>{HTML_FOOTER}"
        "</body></html>"
    )


def _generate_html_fixtures() -> None:
    french_main = "\n".join(f"<p>{paragraph}</p>" for paragraph in FRENCH_PARAGRAPHS)
    arabic_main = "\n".join(f"<p>{paragraph}</p>" for paragraph in ARABIC_PARAGRAPHS)

    (FIXTURES_DIR / "sample_fr.html").write_text(
        _build_html_page(french_main, lang="fr"), encoding="utf-8"
    )
    (FIXTURES_DIR / "sample_ar.html").write_text(
        _build_html_page(arabic_main, lang="ar"), encoding="utf-8"
    )

    empty_html = f"<!DOCTYPE html><html>{EMPTY_HTML_HEAD}<body>{HTML_BOILERPLATE}{HTML_FOOTER}</body></html>"
    (FIXTURES_DIR / "sample_empty.html").write_text(empty_html, encoding="utf-8")


def generate_fixtures() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    _generate_docx_fixtures()
    _generate_pdf_fixtures()
    _generate_html_fixtures()


if __name__ == "__main__":
    generate_fixtures()
    print(f"Fixtures generated in {FIXTURES_DIR}")
