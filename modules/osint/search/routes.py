from flask import jsonify, render_template, request, session

from modules.osint.auth import login_required
from modules.osint.core.engine import UniversalOsintEngine
from modules.osint.search import search_osint_bp

_ENGINE = UniversalOsintEngine()


@search_osint_bp.route("/search")
@login_required
def search():
    target = request.args.get("q", "").strip()
    source = request.args.get("source", "all").strip() or "all"
    persist = request.args.get("persist", "1").strip() not in {"0", "false", "no"}

    if not target:
        return jsonify({
            "error": "No se proporcionó un objetivo.",
            "target": "",
            "target_type": "unknown",
            "results": [],
            "findings": [],
        }), 400

    response = _ENGINE.search(
        target=target,
        source_hint=source,
        persist=persist,
        user_name=session.get("user"),
        created_by=str(session.get("user") or "system"),
    )
    return jsonify(response)


@search_osint_bp.route("/search/view")
@login_required
def search_page():
    return render_template("osint/search.html")


@search_osint_bp.route("/graph")
@login_required
def graph_alias():
    target = request.args.get("q", "").strip()
    source = request.args.get("source", "all").strip() or "all"

    if not target:
        return jsonify({"error": "No se proporcionó un objetivo."}), 400

    response = _ENGINE.search(
        target=target,
        source_hint=source,
        persist=True,
        user_name=session.get("user"),
        created_by=str(session.get("user") or "system"),
    )
    graph = response.get("graph", {})
    return jsonify(
        {
            "target": response.get("target", target),
            "target_type": response.get("target_type", "unknown"),
            "graph": graph,
            "findings": response.get("findings", []),
            "risk": response.get("risk", {}),
            "stats": response.get("stats", {}),
        }
    )
