import logging
from flask import request, jsonify
from modules.osint.auth import login_required
from modules.osint.analytics import analytics_osint_bp
from modules.osint.analytics.graph_builder import build_graph

log = logging.getLogger(__name__)


@analytics_osint_bp.route("/graph")
@login_required
def graph():
    query  = request.args.get("q",      "").strip()
    source = request.args.get("source", "all")

    try:
        from models import db
        from models.osint_graph import Node, OsintEdge

        slug = query.lower().replace(" ", "_")

        if query:
            root = (
                db.session.query(Node).filter_by(value=query).first()
                or db.session.query(Node).filter_by(value=slug).first()
            )

            if root:
                visited_ids: set[int] = set()
                queue: list[int] = [root.id]
                while queue:
                    nid = queue.pop(0)
                    if nid in visited_ids:
                        continue
                    visited_ids.add(nid)
                    for edge in db.session.query(OsintEdge).filter(
                        (OsintEdge.source_id == nid) | (OsintEdge.target_id == nid)
                    ).all():
                        neighbor = edge.target_id if edge.source_id == nid else edge.source_id
                        if neighbor not in visited_ids:
                            queue.append(neighbor)

                all_nodes = db.session.query(Node).filter(Node.id.in_(visited_ids)).all()
                all_edges = db.session.query(OsintEdge).filter(
                    OsintEdge.source_id.in_(visited_ids),
                    OsintEdge.target_id.in_(visited_ids),
                ).all()
            else:
                all_nodes = []
                all_edges = []
        else:
            all_nodes = db.session.query(Node).all()
            all_edges = db.session.query(OsintEdge).all()

        if all_nodes:
            nodes_json = [
                {"id": n.value, "label": n.label or n.value, "type": n.type, "group": n.group}
                for n in all_nodes
            ]
            links_json = []
            for e in all_edges:
                src = e.source_node.value if e.source_node else None
                tgt = e.target_node.value if e.target_node else None
                if src and tgt:
                    links_json.append({"source": src, "target": tgt, "label": e.relation_type, "type": e.relation_type})

            return jsonify({"directed": True, "multigraph": False, "graph": {}, "nodes": nodes_json, "links": links_json})

    except Exception as exc:
        log.warning("analytics /graph SQLite error: %s", exc)

    if not query:
        return jsonify({"directed": True, "multigraph": False, "graph": {}, "nodes": [], "links": []})

    data = _collect_all_data_lite(query, source)
    graph_data = build_graph(
        username       = query,
        github_profile = data["github_profile"],
        github_repos   = data["github_repos"],
        reddit_profile = data["reddit_profile"],
        facebook_data  = data["facebook_data"],
        ip_data        = data["ip_data"],
        rdap_data      = data["rdap_data"],
    )
    return jsonify(graph_data)


def _collect_all_data_lite(query: str, source: str) -> dict:
    from modules.osint.social.routes import _fetch_github, _fetch_reddit
    from modules.osint.opendata.routes import _fetch_ip_geo, _fetch_domain_rdap, _parse_rdap

    result = {
        "github_profile": None, "github_repos": None,
        "reddit_profile": None, "facebook_data": None,
        "ip_data": None,        "rdap_data": None,
    }

    if source in ("github", "social", "all"):
        try:
            result["github_profile"], result["github_repos"], _ = _fetch_github(query)
        except Exception:
            pass

    if source in ("reddit", "social", "all"):
        try:
            result["reddit_profile"], _, _ = _fetch_reddit(query)
        except Exception:
            pass

    if source in ("ip", "network", "all"):
        try:
            result["ip_data"], _ = _fetch_ip_geo(query)
        except Exception:
            pass

    if source in ("domain", "network", "all"):
        try:
            rdap_raw, _         = _fetch_domain_rdap(query)
            result["rdap_data"] = _parse_rdap(rdap_raw)
        except Exception:
            pass

    return result
