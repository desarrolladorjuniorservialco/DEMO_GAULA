import logging
from flask import request, jsonify
from modules.osint.auth import login_required
from modules.osint.analytics import analytics_osint_bp
from modules.osint.analytics.graph_builder import (
    build_graph, ENTITY_STYLE, ENTITY_RISK, _generate_findings,
)

log = logging.getLogger(__name__)

# ── Helpers: derive visual style for DB-sourced nodes ─────────────────────────

def _node_style_defaults(ntype: str) -> dict:
    style = ENTITY_STYLE.get(ntype, {"color": "#6b8aaa", "shape": "ellipse", "size": 26})
    return {
        "color":      style["color"],
        "shape":      style["shape"],
        "base_size":  style["size"],
        "risk_level": ENTITY_RISK.get(ntype, "Bajo"),
    }


def _enrich_db_node(n) -> dict:
    meta    = n.metadata_payload or {}
    ntype   = n.type or "person"
    defaults = _node_style_defaults(ntype)
    return {
        "id":             n.value,
        "label":          n.label or n.value,
        "type":           ntype,
        "color":          meta.get("color",          defaults["color"]),
        "shape":          meta.get("shape",          defaults["shape"]),
        "base_size":      meta.get("base_size",      defaults["base_size"]),
        "confidence":     meta.get("confidence",     0.80),
        "risk_level":     meta.get("risk_level",     defaults["risk_level"]),
        "source_evidence":meta.get("source_evidence","osint.db"),
        "discovered_at":  n.created_at.strftime("%Y-%m-%d") if n.created_at else "",
        "metadata":       {k: v for k, v in meta.items()
                           if k not in ("color","shape","base_size","confidence",
                                        "risk_level","source_evidence","is_target")},
        "is_target":      meta.get("is_target", False),
    }


def _enrich_db_edge(e, src_val: str, tgt_val: str) -> dict:
    meta = e.metadata_payload or {}
    return {
        "source":          src_val,
        "target":          tgt_val,
        "relation_type":   e.relation_type,
        "label":           e.relation_type.replace("_", " "),
        "confidence":      meta.get("confidence", 0.75),
        "weight":          meta.get("weight",     1.0),
        "source_evidence": meta.get("source_evidence", "osint.db"),
    }


# ── Persist graph to osint.db ─────────────────────────────────────────────────

def _persist_graph(graph_data: dict) -> None:
    """Save nodes and edges from a build_graph result to osint.db."""
    try:
        from models import db
        from models.osint_graph import get_or_create_node, create_edge

        node_objs: dict[str, object] = {}
        for n in graph_data.get("nodes", []):
            meta_payload = {
                "color":          n["color"],
                "shape":          n["shape"],
                "base_size":      n["base_size"],
                "confidence":     n["confidence"],
                "risk_level":     n["risk_level"],
                "source_evidence":n["source_evidence"],
                "is_target":      n.get("is_target", False),
                **n.get("metadata", {}),
            }
            # group field kept for backward-compat with older DB reads
            group = n["type"]
            obj, _ = get_or_create_node(
                db.session,
                type=n["type"],
                value=n["id"],
                label=n["label"],
                group=group,
                metadata_dict=meta_payload,
            )
            node_objs[n["id"]] = obj

        for e in graph_data.get("links", []):
            src_obj = node_objs.get(e["source"])
            tgt_obj = node_objs.get(e["target"])
            if src_obj and tgt_obj:
                create_edge(
                    db.session, src_obj, tgt_obj,
                    relation_type=e["relation_type"],
                    metadata_dict={
                        "confidence":     e["confidence"],
                        "weight":         e["weight"],
                        "source_evidence":e["source_evidence"],
                    },
                )
        db.session.commit()
    except Exception as exc:
        log.warning("osint graph persist error: %s", exc)
        try:
            from models import db
            db.session.rollback()
        except Exception:
            pass


# ── /graph endpoint ───────────────────────────────────────────────────────────

@analytics_osint_bp.route("/graph")
@login_required
def graph():
    query  = request.args.get("q",      "").strip()
    source = request.args.get("source", "all")

    # ── Try loading from osint.db first ───────────────────────────────────────
    try:
        from models import db
        from models.osint_graph import Node, OsintEdge

        slug = query.lower().replace(" ", "_") if query else None

        if query:
            root = (
                db.session.query(Node).filter_by(value=query).first()
                or (db.session.query(Node).filter_by(value=slug).first() if slug else None)
            )

            if root:
                visited: set[int] = set()
                queue: list[int]  = [root.id]
                while queue:
                    nid = queue.pop(0)
                    if nid in visited:
                        continue
                    visited.add(nid)
                    for edge in db.session.query(OsintEdge).filter(
                        (OsintEdge.source_id == nid) | (OsintEdge.target_id == nid)
                    ).all():
                        nbr = edge.target_id if edge.source_id == nid else edge.source_id
                        if nbr not in visited:
                            queue.append(nbr)

                all_nodes = db.session.query(Node).filter(Node.id.in_(visited)).all()
                all_edges = db.session.query(OsintEdge).filter(
                    OsintEdge.source_id.in_(visited),
                    OsintEdge.target_id.in_(visited),
                ).all()

                if all_nodes:
                    nodes_out = [_enrich_db_node(n) for n in all_nodes]
                    links_out = []
                    for e in all_edges:
                        sv = e.source_node.value if e.source_node else None
                        tv = e.target_node.value if e.target_node else None
                        if sv and tv:
                            links_out.append(_enrich_db_edge(e, sv, tv))

                    nodes_map  = {n["id"]: n for n in nodes_out}
                    findings   = _generate_findings(nodes_map, links_out, query)
                    by_type: dict[str, int] = {}
                    for n in nodes_out:
                        by_type[n["type"]] = by_type.get(n["type"], 0) + 1

                    return jsonify({
                        "nodes":    nodes_out,
                        "links":    links_out,
                        "findings": findings,
                        "stats": {
                            "total_nodes":   len(nodes_out),
                            "total_edges":   len(links_out),
                            "entity_counts": by_type,
                        },
                    })
        else:
            # No query → return full graph
            all_nodes = db.session.query(Node).limit(150).all()
            all_edges = db.session.query(OsintEdge).limit(300).all()
            if all_nodes:
                nodes_out = [_enrich_db_node(n) for n in all_nodes]
                links_out = []
                node_ids  = {n.id for n in all_nodes}
                for e in all_edges:
                    if e.source_id in node_ids and e.target_id in node_ids:
                        sv = e.source_node.value if e.source_node else None
                        tv = e.target_node.value if e.target_node else None
                        if sv and tv:
                            links_out.append(_enrich_db_edge(e, sv, tv))
                nodes_map = {n["id"]: n for n in nodes_out}
                by_type: dict[str, int] = {}
                for n in nodes_out:
                    by_type[n["type"]] = by_type.get(n["type"], 0) + 1
                return jsonify({
                    "nodes": nodes_out, "links": links_out,
                    "findings": _generate_findings(nodes_map, links_out, ""),
                    "stats": {"total_nodes": len(nodes_out), "total_edges": len(links_out), "entity_counts": by_type},
                })

    except Exception as exc:
        log.warning("analytics /graph DB error: %s", exc)

    if not query:
        return jsonify({"nodes": [], "links": [], "findings": [], "stats": {"total_nodes": 0, "total_edges": 0, "entity_counts": {}}})

    # ── Build from live data ──────────────────────────────────────────────────
    data       = _collect_all_data_lite(query, source)
    graph_data = build_graph(
        username       = query,
        github_profile = data["github_profile"],
        github_repos   = data["github_repos"],
        reddit_profile = data["reddit_profile"],
        facebook_data  = data["facebook_data"],
        ip_data        = data["ip_data"],
        rdap_data      = data["rdap_data"],
    )

    # Persist so subsequent requests use the DB path
    _persist_graph(graph_data)

    return jsonify(graph_data)


def _collect_all_data_lite(query: str, source: str) -> dict:
    from modules.osint.social.routes import _fetch_github, _fetch_reddit

    result = {
        "github_profile": None, "github_repos": None,
        "reddit_profile": None, "facebook_data": None,
        "ip_data":        None, "rdap_data":     None,
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

    return result
