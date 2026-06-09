import json
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.types import TypeDecorator, Text
from sqlalchemy.orm import relationship

from models import db


class JSONType(TypeDecorator):
    impl     = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return "{}"
        return json.dumps(value, ensure_ascii=False, default=str)

    def process_result_value(self, value, dialect):
        if not value:
            return {}
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}


class Node(db.Model):
    __tablename__ = "node"
    __bind_key__  = "osint"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    type             = Column(String(60),  nullable=False, index=True)
    value            = Column(String(512), nullable=False, unique=True, index=True)
    label            = Column(String(256), nullable=False, default="")
    group            = Column(String(60),  nullable=False, default="contact", index=True)
    metadata_payload = Column(JSONType,    nullable=False, default=dict)
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at       = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    outgoing_edges = relationship(
        "OsintEdge",
        foreign_keys="[OsintEdge.source_id]",
        back_populates="source_node",
        cascade="all, delete-orphan",
        lazy="select",
    )
    incoming_edges = relationship(
        "OsintEdge",
        foreign_keys="[OsintEdge.target_id]",
        back_populates="target_node",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_osint_node_type_value", "type", "value"),
        Index("ix_osint_node_group_type",  "group", "type"),
    )

    _GROUP_COLORS = {
        "target":          "#c8a84b",
        "contact":         "#4bc8a8",
        "network":         "#4b8ac8",
        "org":             "#c84b8a",
        "repo":            "#8ac84b",
        "platform":        "#6b6860",
        "x_platform":      "#1DA1F2",
        "x_profile":       "#1565a8",
        "tiktok_platform": "#ff0050",
        "tiktok_profile":  "#a0002f",
        "social_profile":  "#a855f7",
    }


class OsintEdge(db.Model):
    __tablename__ = "edge"
    __bind_key__  = "osint"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    source_id        = Column(
        Integer, ForeignKey("node.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_id        = Column(
        Integer, ForeignKey("node.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type    = Column(String(100), nullable=False, index=True)
    metadata_payload = Column(JSONType,    nullable=False, default=dict)
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)

    source_node = relationship(
        "Node", foreign_keys=[source_id], back_populates="outgoing_edges"
    )
    target_node = relationship(
        "Node", foreign_keys=[target_id], back_populates="incoming_edges"
    )

    __table_args__ = (
        Index("ix_osint_edge_src_tgt_rel", "source_id", "target_id", "relation_type"),
    )


def get_or_create_node(session, type, value, label, group, metadata_dict=None):
    node = session.query(Node).filter_by(value=value).first()
    if node:
        if metadata_dict:
            existing = node.metadata_payload or {}
            node.metadata_payload = {**existing, **metadata_dict}
            node.updated_at = datetime.utcnow()
        return node, False
    node = Node(
        type=type, value=value, label=label, group=group,
        metadata_payload=metadata_dict or {},
    )
    session.add(node)
    session.flush()
    return node, True


def create_edge(session, source_node, target_node, relation_type, metadata_dict=None):
    existing = session.query(OsintEdge).filter_by(
        source_id=source_node.id,
        target_id=target_node.id,
        relation_type=relation_type,
    ).first()
    if existing:
        if metadata_dict:
            prev = existing.metadata_payload or {}
            existing.metadata_payload = {**prev, **metadata_dict}
        return existing, False
    edge = OsintEdge(
        source_id=source_node.id,
        target_id=target_node.id,
        relation_type=relation_type,
        metadata_payload=metadata_dict or {},
    )
    session.add(edge)
    session.flush()
    return edge, True
