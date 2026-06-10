"""opendata/routes.py — Tab Datos Abiertos: SIMIT + RUES + Phone + dorking web."""
from __future__ import annotations

import re
from typing import Any

from flask import render_template, request

from modules.osint.auth import login_required
from modules.osint.connectors.base import ConnectorResult
from modules.osint.connectors.phone import PhoneConnector
from modules.osint.connectors.rues import RuesConnector
from modules.osint.connectors.simit import SimitConnector
from modules.osint.connectors.web_dork import run_dork
from modules.osint.opendata import opendata_bp

_PLATE_RE = re.compile(r"^[A-Za-z]{3}[0-9A-Za-z]{3}$")
_PHONE_RE = re.compile(r"^(\+57|57)?3\d{9}$")
_NAME_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÑáéíóúñ]+(?:\s+[A-Za-zÁÉÍÓÚÑáéíóúñ]+)+$")

_SIMIT = SimitConnector()
_RUES = RuesConnector()
_PHONE = PhoneConnector()


def _detect_type(q: str) -> str:
    q = q.strip()
    if _PHONE_RE.match(q) or q.startswith("+"):
        return "phone"
    if _PLATE_RE.match(q):
        return "plate"
    if q.isdigit() and 6 <= len(q) <= 10:
        return "document"
    if _NAME_RE.match(q):
        return "name"
    return "unknown"


def _gather(q: str, target_type: str) -> dict[str, Any]:
    """Ejecuta los conectores aplicables al tipo y devuelve el contexto."""
    simit: ConnectorResult | None = None
    rues: ConnectorResult | None = None
    phone: ConnectorResult | None = None

    if target_type in ("plate", "document"):
        simit = _SIMIT.fetch(q, target_type=target_type)
    if target_type in ("document", "name"):
        rues = _RUES.fetch(q, target_type=target_type)
    if target_type == "phone":
        phone = _PHONE.fetch(q)

    dork: tuple[list[dict], list[str]] = ([], [])
    if target_type in ("plate", "document", "name", "unknown"):
        queries = [f'"{q}"']
        if target_type in ("document", "plate"):
            queries.append(f'"{q}" Colombia')
        dork = run_dork(queries, max_results=8)

    return {"simit": simit, "rues": rues, "phone": phone, "dork": dork}


@opendata_bp.route("/lookup")
@login_required
def lookup() -> Any:
    q = request.args.get("q", "").strip()

    def _render(**ctx: Any) -> Any:
        base = {
            "q": q, "target_type": "unknown", "simit": None, "rues": None,
            "phone": None, "dork_results": [], "errors": [],
            "sources_queried": 0, "findings_count": 0,
        }
        base.update(ctx)
        return render_template("osint/opendata_fragment.html", **base)

    if not q:
        return _render(errors=["No se proporcionó un término de búsqueda."])
    if len(q) > 100:
        return _render(errors=["Consulta demasiado larga (máximo 100 caracteres)."])

    target_type = _detect_type(q)
    ctx = _gather(q, target_type)
    simit, rues, phone = ctx["simit"], ctx["rues"], ctx["phone"]
    dork_results, dork_errors = ctx["dork"]

    errors: list[str] = []
    for r in (simit, rues, phone):
        if r:
            errors.extend(r.errors)
    errors.extend(dork_errors)

    sources = [r for r in (simit, rues, phone) if r is not None]
    sources_queried = len(sources) + (1 if dork_results or not sources else 0)
    findings_count = sum([
        len(simit.data.get("rows", [])) if simit and simit.ok else 0,
        len(rues.data.get("expedientes", [])) if rues and rues.ok else 0,
        1 if phone and phone.ok else 0,
        len(dork_results),
    ])

    return _render(
        target_type=target_type, simit=simit, rues=rues, phone=phone,
        dork_results=dork_results, errors=errors,
        sources_queried=sources_queried, findings_count=findings_count,
    )
