from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from .schemas import TargetDetection

try:
    from email_validator import validate_email as _validate_email
except Exception:  # pragma: no cover - optional dependency
    _validate_email = None

try:
    import phonenumbers
except Exception:  # pragma: no cover - optional dependency
    phonenumbers = None

try:
    import tldextract
except Exception:  # pragma: no cover - optional dependency
    tldextract = None


_HASH_RE = re.compile(r"^(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{40}|[a-fA-F0-9]{64})$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,64}$")
_DOMAIN_RE = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[A-Za-z]{2,63}$")


def _normalize_domain(value: str) -> str:
    raw = value.strip().lower()
    if raw.startswith(("http://", "https://")):
        raw = urlparse(raw).netloc or raw
    if raw.startswith("www."):
        raw = raw[4:]
    return raw.rstrip(".")


def _detect_phone(value: str) -> bool:
    if not phonenumbers:
        return bool(re.fullmatch(r"[\d\s()+-]{7,24}", value.strip()))
    try:
        parsed = phonenumbers.parse(value, None)
        return phonenumbers.is_possible_number(parsed) and phonenumbers.is_valid_number(parsed)
    except Exception:
        return False


def detect_target_type(value: str) -> TargetDetection:
    raw = (value or "").strip()
    normalized = raw
    metadata: dict[str, object] = {}

    if not raw:
        return TargetDetection(value="", target_type="unknown", normalized="", confidence=0.0)

    try:
        ipaddress.ip_address(raw)
        return TargetDetection(value=raw, target_type="ip", normalized=raw, confidence=0.99)
    except ValueError:
        pass

    if _validate_email:
        try:
            result = _validate_email(raw, check_deliverability=False)
            return TargetDetection(
                value=raw,
                target_type="email",
                normalized=result.email.lower(),
                confidence=0.99,
            )
        except Exception:
            pass
    elif _EMAIL_RE.fullmatch(raw):
        return TargetDetection(value=raw, target_type="email", normalized=raw.lower(), confidence=0.9)

    if raw.startswith(("http://", "https://")):
        parsed = urlparse(raw)
        host = (parsed.netloc or "").lower()
        if host:
            metadata["hostname"] = host
            return TargetDetection(
                value=raw,
                target_type="url",
                normalized=raw,
                confidence=0.95,
                metadata=metadata,
            )

    candidate = _normalize_domain(raw)
    if _DOMAIN_RE.fullmatch(candidate):
        if tldextract:
            ext = tldextract.extract(candidate)
            metadata["domain"] = candidate
            metadata["suffix"] = ext.suffix
            metadata["registered_domain"] = ext.registered_domain or candidate
        return TargetDetection(
            value=raw,
            target_type="domain",
            normalized=candidate,
            confidence=0.92,
            metadata=metadata,
        )

    if _HASH_RE.fullmatch(raw):
        return TargetDetection(value=raw, target_type="hash", normalized=raw.lower(), confidence=0.98)

    if _detect_phone(raw):
        normalized = re.sub(r"\s+", " ", raw).strip()
        return TargetDetection(value=raw, target_type="phone", normalized=normalized, confidence=0.9)

    if " " in raw.strip():
        return TargetDetection(value=raw, target_type="full_name", normalized=raw.strip(), confidence=0.72)

    if raw.startswith("@"):
        return TargetDetection(value=raw, target_type="alias", normalized=raw.lstrip("@").lower(), confidence=0.95)

    if _USERNAME_RE.fullmatch(raw):
        return TargetDetection(value=raw, target_type="username", normalized=raw.lower(), confidence=0.88)

    return TargetDetection(value=raw, target_type="unknown", normalized=raw.lower(), confidence=0.4)
