"""
graph_builder.py — shim de compatibilidad.

Contenido canonico movido a modules/osint/graph/builder.py.
Re-exporta todos los simbolos publicos para no romper importaciones existentes.
"""
from modules.osint.graph.builder import (  # noqa: F401
    build_graph,
    _generate_findings,
    _count_by_type,
    _node,
    _edge,
    ENTITY_STYLE,
    ENTITY_RISK,
    CONFIDENCE,
    TYPE_PERSON,
    TYPE_ALIAS,
    TYPE_EMAIL,
    TYPE_ORGANIZATION,
    TYPE_DOMAIN,
    TYPE_IP,
    TYPE_REPOSITORY,
    TYPE_SOCIAL_PROFILE,
    TYPE_LOCATION,
    TYPE_PLATFORM,
    TYPE_URL,
)
