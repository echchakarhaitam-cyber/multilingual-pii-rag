# Findings Log

Lab-notebook entries documenting unexpected behavior discovered while building
this project. Each entry is dated and factual -- these are observations, not
conclusions about production behavior.

---

## 2026-09-16 -- PyMuPDF silently corrupts Arabic text on PDF text insertion

### What was attempted

While writing `scripts/generate_test_fixtures.py` to generate a clean Arabic
PDF fixture (`sample_ar.pdf`) for `tests/test_ingestion.py`, PyMuPDF (`fitz`
/ `pymupdf`, v1.28.2) was used to write Arabic text into a PDF via two of its
text-insertion APIs:

1. `Page.insert_text()` with a registered TrueType font
   (`C:\Windows\Fonts\tahoma.ttf`)
2. `Page.insert_htmlbox()`, which uses HarfBuzz-based complex-script shaping

The resulting PDFs were then read back with `pypdf.PdfReader` and
`page.extract_text()`, the same extraction path used by
`src/ingestion/loaders.py::load_pdf`.

### What happened

Both APIs produced text that, on extraction, did **not** round-trip to the
original input string.

**`insert_text()` case** -- input string `مرحبا بالعالم` (13 codepoints,
including one space):

```
Original codepoints (U+0600-U+06FF, base Arabic block):
0x645, 0x631, 0x62d, 0x628, 0x627, 0x20, 0x628, 0x627, 0x644, 0x639, 0x627, 0x644, 0x645

Extracted repr: 'ﻡﻝﺍﻉﻝﺍﺏ'
Extracted codepoints (U+FE70-U+FEFF, Arabic Presentation Forms-B):
0xfee1, 0xfedd, 0xfe8d, 0xfec9, 0xfedd, 0xfe8d, 0xfe8f
```

7 codepoints were extracted from 13 input codepoints -- the space and several
letters were dropped, and the remaining characters do not appear in their
original order.

**`insert_htmlbox()` case** -- input string `مرحبا بالعالم بكم` (with
HarfBuzz shaping enabled via CSS):

```
Extracted repr: 'ﻢﻜﺑ '
Extracted codepoints: 0xfee2, 0xfedc, 0xfe91
```

Only 3 codepoints were recovered from an 18-codepoint input; `insert_htmlbox`
also reported the text overflowed its layout box (`filled=1.0`), so partial
loss here is compounded by both a layout failure and a character-set failure.

In both cases, every extracted codepoint fell in **U+FE70-U+FEFF (Arabic
Presentation Forms-B)** -- glyph-shaping variants (isolated/medial/final
forms) -- rather than **U+0600-U+06FF (the base Arabic block)** that the
original input used and that this project's corruption check
(`src/ingestion/loaders.py::_assess_arabic_corruption`,
`ARABIC_PATTERN = re.compile(r"[\u0600-\u06FF]")`) scans for. No
`\ufffd` replacement characters appeared -- the corruption is not
"characters lost to encoding errors," it is "characters silently replaced by
different, out-of-range Unicode codepoints" that a `\u0600-\u06FF` regex scan
does not catch at all.

### Why this matters

This is precisely the failure mode this project's hypothesis is concerned
with: a standard, widely-used library (PyMuPDF) can silently mangle Arabic
text during a routine operation (writing text into a PDF) such that the text
extracted downstream is neither visually correct nor Unicode-equivalent to
the source -- and the corruption is invisible unless someone diffs the
extracted codepoints against the original. If this happens at the
*ingestion* stage of a pipeline, every downstream stage (PII detection,
embedding, retrieval) inherits already-corrupted input and has no way to
recover the original signal. A recall or precision number measured on such a
pipeline would be measuring performance on corrupted text without anyone
knowing it.

This also means the `_assess_arabic_corruption` replacement-character check
(`\ufffd` ratio) in `load_pdf`/`load_docx` is necessary but not sufficient:
it catches "text destroyed into replacement characters" but would not catch
"Arabic text silently shifted into the Presentation Forms block," since
those codepoints are valid, non-replacement Unicode -- just the wrong
characters.

### Workaround used

Switched the PDF fixture generator from PyMuPDF to `reportlab`
(`reportlab.pdfgen.canvas`) with a registered system TrueType font
(`C:\Windows\Fonts\tahoma.ttf`, via `reportlab.pdfbase.ttfonts.TTFont`).
`reportlab.Canvas.drawString()` does not perform Arabic shaping/joining, so
it draws each input character using the font's cmap directly and builds the
embedded font's `ToUnicode` CMap from the exact input codepoints. Extracting
that PDF with `pypdf` recovers the same Unicode character *set* as the
input:

```
Input:     مرحبا بالعالم بكم اليوم
Extracted: مويلا مكب ملاعلاب ابحرم
```

The extracted text is in **reversed visual order** (reportlab does not
perform bidi reordering either), but every character is a genuine base-block
Arabic codepoint (U+0600-U+06FF) with no replacement characters and no
Presentation-Forms substitution -- `set(input_text) <= set(extracted_text)`
holds. For the purposes of this project's `has_arabic` /
`corruption_risk` checks, this fixture is a clean positive case: it
correctly triggers `has_arabic=True`, `corruption_risk=False`. The visual
reversal is a separate, known limitation of the fixture generator (not
something `load_pdf` is asked to detect per current requirements) and is
not addressed by this workaround.

This is implemented in `scripts/generate_test_fixtures.py`
(`_generate_pdf_fixtures`, `CANDIDATE_ARABIC_FONTS`).

### Open question for later (Week 4)

Does this same corruption pattern -- base Arabic block silently mapped to
Arabic Presentation Forms-B, with dropped/reordered characters -- appear in
real-world Arabic PDFs (e.g. scanned/exported government or legal documents,
which is this project's target domain), and if so, does it measurably affect
Presidio's PII-detection recall on Arabic text? This was only observed here
in a synthetic fixture generated with PyMuPDF; it has not yet been checked
against real-world PDF sources or measured against Presidio's output. To be
investigated and measured in Week 4.
