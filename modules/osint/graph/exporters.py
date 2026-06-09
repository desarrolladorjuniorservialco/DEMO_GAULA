"""graph/exporters.py — Exportadores de grafos OSINT a GraphML, JSON, CSV."""
from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET
from typing import Any


class GraphExporter:
    """Convierte un dict de grafo en distintos formatos de exportación."""

    @staticmethod
    def to_json(graph_data: dict[str, Any], indent: int = 2) -> str:
        return json.dumps(graph_data, ensure_ascii=False, indent=indent, default=str)

    @staticmethod
    def to_graphml(graph_data: dict[str, Any]) -> str:
        """Genera XML en formato GraphML compatible con Gephi y Cytoscape."""
        root = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/graphml")

        for key_id, attr_name, domain, attr_type in [
            ("d_label", "label", "node", "string"),
            ("d_type",  "type",  "node", "string"),
            ("d_group", "group", "node", "string"),
            ("e_label", "label", "edge", "string"),
        ]:
            ET.SubElement(root, "key", id=key_id, **{
                "for": domain, "attr.name": attr_name, "attr.type": attr_type,
            })

        graph_el = ET.SubElement(root, "graph", id="G", edgedefault="directed")

        for node in graph_data.get("nodes", []):
            node_el = ET.SubElement(graph_el, "node", id=str(node.get("id", "")))
            for key_id, field in [("d_label", "label"), ("d_type", "type"), ("d_group", "group")]:
                data_el = ET.SubElement(node_el, "data", key=key_id)
                data_el.text = str(node.get(field, ""))

        for i, edge in enumerate(graph_data.get("edges", [])):
            src = str(edge.get("from") or edge.get("source", ""))
            tgt = str(edge.get("to") or edge.get("target", ""))
            edge_el = ET.SubElement(graph_el, "edge", id=f"e{i}", source=src, target=tgt)
            data_el = ET.SubElement(edge_el, "data", key="e_label")
            data_el.text = str(edge.get("label", ""))

        ET.indent(root, space="  ")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")

    @staticmethod
    def nodes_to_csv(graph_data: dict[str, Any]) -> str:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["id", "type", "label", "group", "value"])
        writer.writeheader()
        for node in graph_data.get("nodes", []):
            writer.writerow({
                "id":    node.get("id", ""),
                "type":  node.get("type", ""),
                "label": node.get("label", ""),
                "group": node.get("group", ""),
                "value": node.get("value", ""),
            })
        return buf.getvalue()

    @staticmethod
    def edges_to_csv(graph_data: dict[str, Any]) -> str:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["source", "target", "label"])
        writer.writeheader()
        for edge in graph_data.get("edges", []):
            writer.writerow({
                "source": edge.get("from") or edge.get("source", ""),
                "target": edge.get("to") or edge.get("target", ""),
                "label":  edge.get("label", ""),
            })
        return buf.getvalue()
