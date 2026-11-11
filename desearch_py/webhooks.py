"""Verify Desearch webhook deliveries (Monitors).

Every delivery carries ``Desearch-Signature: t=<unix seconds>,v1=<hex>``, where
``v1`` is the HMAC-SHA256 of ``"<t>.<raw body>"`` keyed with the monitor's
``webhook_secret`` (``whsec_…``, used as given). Check it against the raw
request body, before parsing the JSON: a re-serialized body does not match.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import List, Optional, Tuple, Union

SIGNATURE_HEADER = "Desearch-Signature"
DEFAULT_TOLERANCE_SECONDS = 300


def _parse_signature_header(header: str) -> Optional[Tuple[str, List[str]]]:
    timestamp: Optional[str] = None
    signatures: List[str] = []
    for part in header.split(","):
        key, sep, value = part.strip().partition("=")
        if not sep:
            continue
        if key == "t":
            if not (value.isascii() and value.isdigit()):
                return None
            timestamp = value
        elif key == "v1" and value:
            signatures.append(value)
    if timestamp is None or not signatures:
        return None
    return timestamp, signatures


def verify_webhook_signature(
    secret: str,
    header: Optional[str],
    body: Union[bytes, bytearray, str],
    *,
    tolerance: Optional[float] = DEFAULT_TOLERANCE_SECONDS,
    now: Optional[float] = None,
) -> bool:
    """
    Check a webhook delivery's ``Desearch-Signature`` header.

    Args:
        secret (str): The monitor's ``webhook_secret``, from ``create_monitor``,
            ``update_monitor`` (new webhook URL) or ``rotate_monitor_webhook_secret``.
        header (Optional[str]): The ``Desearch-Signature`` header value.
        body (Union[bytes, str]): The raw request body, exactly as received. A ``str`` is
            encoded as UTF-8.
        tolerance (Optional[float]): Most seconds between the signature's timestamp and now,
            either way. Defaults to 300 (5 minutes). ``None`` skips the check.
        now (Optional[float]): The current Unix time, for tests. Defaults to ``time.time()``.

    Returns:
        bool: True when the header is well formed, its timestamp is within ``tolerance``
        and a ``v1`` signature matches (compared in constant time).
    """
    if not secret or not header:
        return False
    parsed = _parse_signature_header(header)
    if parsed is None:
        return False
    timestamp, signatures = parsed
    if tolerance is not None:
        current = time.time() if now is None else now
        if abs(current - int(timestamp)) > tolerance:
            return False
    raw = body.encode("utf-8") if isinstance(body, str) else bytes(body)
    expected = hmac.new(
        secret.encode("utf-8"), timestamp.encode() + b"." + raw, hashlib.sha256
    ).hexdigest().encode()
    matched = False
    for signature in signatures:
        # Check every candidate so the time does not depend on which one matches.
        if hmac.compare_digest(expected, signature.encode("utf-8")):
            matched = True
    return matched
