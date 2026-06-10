"""connectors/social_stubs.py — Stubs para conectores de redes sociales.

Estos conectores requieren autenticación o Playwright para funcionar.
Cada uno devuelve ConnectorResult(ok=False) con un mensaje descriptivo.
Implementaciones completas deben subclasear o reemplazar estas clases.
"""
from __future__ import annotations

from typing import Any

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_STUB_MSG = "requiere autenticación o Playwright — stub no funcional"


class _SocialStub(BaseConnector):
    """Clase base para stubs de redes sociales."""

    _name: str = "stub"
    _types: frozenset[str] = frozenset({"username", "alias", "full_name"})

    @property
    def name(self) -> str:
        return self._name

    @property
    def supported_target_types(self) -> frozenset[str]:
        return self._types

    @property
    def needs_api_key(self) -> bool:
        return True

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        return ConnectorResult(
            connector=self.name,
            ok=False,
            data={},
            errors=[f"{self.name}: {_STUB_MSG}"],
            metadata={"stub": True},
        )


# ─── Redes sociales ────────────────────────────────────────────

class FacebookConnector(_SocialStub):
    _name = "facebook"


class InstagramConnector(_SocialStub):
    _name = "instagram"


class TikTokConnector(_SocialStub):
    _name = "tiktok"


class YouTubeConnector(_SocialStub):
    _name = "youtube"
    _types = frozenset({"username", "alias", "full_name", "channel_id"})


class LinkedInConnector(_SocialStub):
    _name = "linkedin"
    _types = frozenset({"username", "alias", "full_name", "email"})


class TwitterConnector(_SocialStub):
    _name = "twitter"


class ThreadsConnector(_SocialStub):
    _name = "threads"


class PinterestConnector(_SocialStub):
    _name = "pinterest"


class TelegramConnector(_SocialStub):
    _name = "telegram"
    _types = frozenset({"username", "alias", "phone"})


class DiscordConnector(_SocialStub):
    _name = "discord"
    _types = frozenset({"username", "alias", "user_id"})


# ─── Plataformas de código ─────────────────────────────────────

class GitLabConnector(_SocialStub):
    _name = "gitlab"
    _types = frozenset({"username", "alias", "email"})


class BitbucketConnector(_SocialStub):
    _name = "bitbucket"
    _types = frozenset({"username", "alias", "email"})


# ─── Motores de búsqueda ───────────────────────────────────────

class GoogleConnector(_SocialStub):
    _name = "google"
    _types = frozenset({"username", "alias", "full_name", "email", "domain", "ip", "phone"})


class BingConnector(_SocialStub):
    _name = "bing"
    _types = frozenset({"username", "alias", "full_name", "email", "domain", "ip"})


class BraveConnector(_SocialStub):
    _name = "brave"
    _types = frozenset({"username", "alias", "full_name", "email", "domain", "ip"})


# ─── Plataformas de threat intelligence ───────────────────────

class ShodanConnector(_SocialStub):
    _name = "shodan"
    _types = frozenset({"ip", "domain"})


class CensysConnector(_SocialStub):
    _name = "censys"
    _types = frozenset({"ip", "domain", "email"})


class VirusTotalConnector(_SocialStub):
    _name = "virustotal"
    _types = frozenset({"ip", "domain", "hash", "url"})


class IntelligenceXConnector(_SocialStub):
    _name = "intelligencex"
    _types = frozenset({"email", "domain", "ip", "username", "bitcoin_address"})


# ─── Registro de todos los stubs ──────────────────────────────

ALL_SOCIAL_STUBS: list[type[_SocialStub]] = [
    FacebookConnector,
    InstagramConnector,
    TikTokConnector,
    YouTubeConnector,
    LinkedInConnector,
    TwitterConnector,
    ThreadsConnector,
    PinterestConnector,
    TelegramConnector,
    DiscordConnector,
    GitLabConnector,
    BitbucketConnector,
    GoogleConnector,
    BingConnector,
    BraveConnector,
    CensysConnector,
    IntelligenceXConnector,
]
