from __future__ import annotations

from io import BytesIO
from urllib.parse import urlsplit

from fastapi import HTTPException
from fastapi.responses import Response
import segno

from assetguard.infrastructure.config import get_settings


def qr_base_url(public_url: str | None) -> str:
    """Return the configured application URL or a validated public override."""
    if not public_url:
        return get_settings().public_url.rstrip("/")

    parsed = urlsplit(public_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(
            422,
            "QR public_url must be an HTTPS origin without credentials, query or fragment.",
        )
    return f"https://{parsed.netloc}{parsed.path.rstrip('/')}"


def qr_svg_response(payload: str, title: str) -> Response:
    qr = segno.make(payload, error="m")
    output = BytesIO()
    qr.save(output, kind="svg", scale=4, border=2, title=title)
    return Response(output.getvalue(), media_type="image/svg+xml")
