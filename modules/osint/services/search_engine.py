"""
search_engine.py — shim de compatibilidad.

Contenido canonico movido a modules/osint/engines/dork_engine.py.
Re-exporta ejecutar_dork_universal para no romper importaciones existentes.
"""
from modules.osint.engines.dork_engine import (  # noqa: F401
    ejecutar_dork_universal,
    _search_single_platform,
    _build_dork,
    PLATFORM_DOMAINS,
    DDG_AVAILABLE,
    INTER_SEARCH_DELAY,
)
