"""opendata/routes.py — Tab Datos Abiertos: búsqueda universal SIMIT + PhoneConnector."""
from __future__ import annotations

import re
from typing import Any

from flask import render_template, request

from modules.osint.auth import login_required
from modules.osint.connectors.base import ConnectorResult
from modules.osint.connectors.phone import PhoneConnector
from modules.osint.connectors.simit import SimitConnector
from modules.osint.engines.orchestration import OsintOrchestrator
from modules.osint.opendata import opendata_bp

_PLATE_RE = re.compile(r"^[A-Za-z]{3}[0-9A-Za-z]{3}$")
_PHONE_RE = re.compile(r"^(\+57|57)?3\d{9}$")

_ORCHESTRATOR = OsintOrchestrator(
    connectors=[SimitConnector(), PhoneConnector()],
    max_workers=2,
    timeout=30.0,
)


def _detect_type(q: str) -> str:
    q = q.strip()
    if _PHONE_RE.match(q) or q.startswith("+"):
        return "phone"
    if _PLATE_RE.match(q):
        return "plate"
    if q.isdigit() and 6 <= len(q) <= 10:
        return "document"
    return "unknown"


def _run_connectors(q: str, target_type: str) -> dict[str, ConnectorResult]:
    results = _ORCHESTRATOR.run(
        target=q,
        target_type=target_type,
        extra_kwargs={
            "simit": {"target_type": target_type},
        },
    )
    if "phone" not in results:
        results["phone"] = ConnectorResult(
            connector="phone", ok=False, data={}, errors=[],
            metadata={"status": "unconfigured"},
        )
    return results


@opendata_bp.route("/lookup")
@login_required
def lookup() -> Any:
    q = request.args.get("q", "").strip()

    if len(q) > 100:
        return render_template(
            "osint/opendata_fragment.html",
            q=q,
            target_type="unknown",
            simit=None,
            phone=None,
            errors=["Consulta demasiado larga (máximo 100 caracteres)."],
            sources_queried=0,
            findings_count=0,
        )

    if not q:
        return render_template(
            "osint/opendata_fragment.html",
            q=q,
            target_type="unknown",
            simit=None,
            phone=None,
            errors=["No se proporcionó un término de búsqueda."],
            sources_queried=0,
            findings_count=0,
        )

    target_type = _detect_type(q)
    results = _run_connectors(q, target_type)

    simit = results.get("simit")
    phone = results.get("phone")

    all_errors: list[str] = []
    if simit:
        all_errors.extend(simit.errors)
    if phone:
        all_errors.extend(phone.errors)

    sources_queried = sum(
        1 for r in [simit, phone]
        if r and r.metadata.get("status") != "unconfigured"
    )
    findings_count = sum([
        len(simit.data.get("rows", [])) if simit and simit.ok else 0,
        1 if phone and phone.ok else 0,
    ])

    return render_template(
        "osint/opendata_fragment.html",
        q=q,
        target_type=target_type,
        simit=simit,
        phone=phone,
        errors=all_errors,
        sources_queried=sources_queried,
        findings_count=findings_count,
    )
