"""Shared support for PDF responses."""

from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def pdf_font_name() -> str:
    """Register and return a font with Cyrillic glyphs for supported runtimes."""
    candidates = (
        ("AssetGuardDejaVu", Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")),
        ("AssetGuardArial", Path("C:/Windows/Fonts/arial.ttf")),
    )
    for name, path in candidates:
        if path.is_file():
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(path)))
            return name
    raise RuntimeError("A Unicode font is required for PDF export. Install fonts-dejavu-core.")
