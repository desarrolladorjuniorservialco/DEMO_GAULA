"""
facebook_playwright.py — shim de compatibilidad.

Implementación canónica en modules/osint/scrapers/browser/playwright.py.
"""
from modules.osint.scrapers.browser.playwright import (  # noqa: F401
    scrape_facebook_profile,
    _load_mock_data,
    _dork_facebook_url,
    _extract_og,
    _extract_intel,
    _is_login_wall,
    TIMEOUT_MS,
    NOT_PUBLIC,
    NOT_AVAILABLE,
    _FB_NON_PROFILE,
    _EMPTY_INTEL,
)
