"""graph/persistence.py — Persiste grafos OSINT en osint.db."""
from __future__ import annotations

from typing import Any


class GraphPersistence:
    """
    Persiste y recupera grafos OSINT usando Node/OsintEdge de models/osint_graph.py.

    Imports ORM diferidos para evitar importaciones circulares en contexto de app.
    """

    @staticmethod
    def save_graph(graph_data: dict[str, Any], consulta_id: int | None = None) -> dict[str, int]:
        """
        Persiste nodos y aristas del dict devuelto por build_graph().

        Returns:
            dict con nodes_saved (int) y edges_saved (int).
        """
        from models import db
        from models.osint_graph import get_or_create_node, create_edge

        nodes_saved = 0
        edges_saved = 0
        id_to_node: dict[str, Any] = {}

        for node_dict in graph_data.get("nodes", []):
            node_id = node_dict.get("id", "")
            ntype = node_dict.get("type", "unknown")
            value = node_dict.get("value") or node_dict.get("label") or node_id
            label = node_dict.get("label", value)
            group = node_dict.get("group", "contact")
            metadata = {k: v for k, v in node_dict.items()
                        if k not in ("id", "type", "value", "label", "group")}
            if consulta_id:
                metadata["consulta_id"] = consulta_id

            node = get_or_create_node(
                db.session, type=ntype, value=value,
                label=label, group=group, metadata_dict=metadata,
            )
            id_to_node[node_id] = node
            nodes_saved += 1

        for edge_dict in graph_data.get("edges", []):
            src_id = edge_dict.get("from") or edge_dict.get("source")
            tgt_id = edge_dict.get("to") or edge_dict.get("target")
            relation = edge_dict.get("label") or edge_dict.get("relation", "related_to")

            src_node = id_to_node.get(src_id)
            tgt_node = id_to_node.get(tgt_id)
            if src_node and tgt_node:
                create_edge(
                    db.session,
                    source_node=src_node,
                    target_node=tgt_node,
                    relation_type=relation,
                    metadata_dict={"consulta_id": consulta_id} if consulta_id else {},
                )
                edges_saved += 1

        db.session.commit()
        return {"nodes_saved": nodes_saved, "edges_saved": edges_saved}

    @staticmethod
    def load_graph(consulta_id: int) -> dict[str, Any]:
        """Carga nodos y aristas asociados a una consulta específica."""
        from models.osint_graph import Node, OsintEdge

        nodes = Node.query.filter(
            Node.metadata_payload["consulta_id"].as_integer() == consulta_id
        ).all()

        node_ids = {n.id for n in nodes}
        edges = OsintEdge.query.filter(
            OsintEdge.source_id.in_(node_ids),
            OsintEdge.target_id.in_(node_ids),
        ).all()

        return {
            "nodes": [
                {"id": str(n.id), "type": n.type, "value": n.value, "label": n.label, "group": n.group}
                for n in nodes
            ],
            "edges": [
                {"from": str(e.source_id), "to": str(e.target_id), "label": e.relation_type}
                for e in edges
            ],
        }
