# OSINT Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate all PRUEBA_OSINT module functionality into DEMO_GAULA, accessible from the "Correlaciones e OSINT" panel (`panel-inteligencia`) in `console.html` via three sub-tabs with AJAX/fetch loading.

**Architecture:** Copy PRUEBA_OSINT's blueprints/services/plugins into `modules/osint/` in DEMO_GAULA; apply three mechanical adaptations (auth, db import, plugin path); register three blueprints on the `nexo` Flask app; add Node/Edge models to `osint.db`; replace the static `panel-inteligencia` content with sub-tabs that fetch HTML fragments and Cytoscape.js graph data.

**Tech Stack:** Flask (monolith, no factory), Flask-SQLAlchemy (multi-bind), Cytoscape.js 3.28, NetworkX, DuckDuckGo Search, Playwright (optional), Python 3.10+.

**Spec:** `docs/superpowers/specs/2026-06-03-osint-integration-design.md`

---

## File Map

| File | Action | Notes |
|------|--------|-------|
| `modules/__init__.py` | CREATE | empty |
| `modules/osint/__init__.py` | CREATE | empty |
| `modules/osint/auth.py` | CREATE | login_required decorator |
| `modules/osint/social/__init__.py` | CREATE | social_osint_bp Blueprint |
| `modules/osint/social/routes.py` | CREATE | adapted from PRUEBA_OSINT |
| `modules/osint/social/scrapers/__init__.py` | CREATE | empty |
| `modules/osint/social/scrapers/facebook_playwright.py` | COPY | verbatim from PRUEBA_OSINT |
| `modules/osint/opendata/__init__.py` | CREATE | opendata_osint_bp Blueprint |
| `modules/osint/opendata/routes.py` | CREATE | adapted from PRUEBA_OSINT |
| `modules/osint/analytics/__init__.py` | CREATE | analytics_osint_bp Blueprint |
| `modules/osint/analytics/routes.py` | CREATE | adapted, /graph only |
| `modules/osint/analytics/graph_builder.py` | COPY | verbatim from PRUEBA_OSINT |
| `modules/osint/plugins/__init__.py` | CREATE | empty |
| `modules/osint/plugins/base.py` | COPY | verbatim from PRUEBA_OSINT |
| `modules/osint/plugins/registry.py` | CREATE | adapted module path |
| `modules/osint/plugins/ejemplo_ip.py` | CREATE | adapted import |
| `modules/osint/services/__init__.py` | CREATE | empty |
| `modules/osint/services/search_engine.py` | COPY | verbatim from PRUEBA_OSINT |
| `modules/osint/services/facebook_osint.py` | CREATE | adapted db imports |
| `modules/osint/services/x_osint.py` | CREATE | adapted db imports |
| `modules/osint/services/tiktok_osint.py` | CREATE | adapted db imports |
| `models/osint_graph.py` | CREATE | Node/Edge with bind_key="osint" |
| `templates/osint/social_fragment.html` | CREATE | fragment (no base.html) |
| `templates/osint/opendata_fragment.html` | CREATE | fragment (no base.html) |
| `app.py` | MODIFY | models import + blueprints + discover_plugins |
| `requirements.txt` | MODIFY | add networkx, duckduckgo-search, playwright |
| `templates/console.html` | MODIFY | Cytoscape CDN + panel-inteligencia |

---

## Task 1: Directory skeleton + auth helper + requirements

**Files:**
- Create: `modules/__init__.py`
- Create: `modules/osint/__init__.py`
- Create: `modules/osint/auth.py`
- Create: `modules/osint/social/__init__.py`
- Create: `modules/osint/social/scrapers/__init__.py`
- Create: `modules/osint/opendata/__init__.py`
- Create: `modules/osint/analytics/__init__.py`
- Create: `modules/osint/plugins/__init__.py`
- Create: `modules/osint/services/__init__.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Create all empty `__init__.py` files**

Run (from DEMO_GAULA root):
```bash
mkdir -p modules/osint/social/scrapers
mkdir -p modules/osint/opendata
mkdir -p modules/osint/analytics
mkdir -p modules/osint/plugins
mkdir -p modules/osint/services
touch modules/__init__.py
touch modules/osint/__init__.py
touch modules/osint/social/__init__.py
touch modules/osint/social/scrapers/__init__.py
touch modules/osint/opendata/__init__.py
touch modules/osint/analytics/__init__.py
touch modules/osint/plugins/__init__.py
touch modules/osint/services/__init__.py
```

- [ ] **Step 2: Create `modules/osint/auth.py`**

```python
from functools import wraps
from flask import session, redirect, url_for


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper
```

- [ ] **Step 3: Update `requirements.txt`**

Add these lines to `requirements.txt` (file currently ends after `beautifulsoup4==4.13.4`):
```
networkx>=3.3
duckduckgo-search>=6.2.0
playwright>=1.60.0
```

- [ ] **Step 4: Install new dependencies**

```bash
pip install networkx "duckduckgo-search>=6.2.0" playwright
playwright install chromium
```

Expected: all packages install without error. Playwright downloads Chromium browser.

- [ ] **Step 5: Commit skeleton**

```bash
git add modules/ requirements.txt
git commit -m "feat: create modules/osint directory skeleton and auth helper"
```

---

## Task 2: Node/Edge models for osint.db

**Files:**
- Create: `models/osint_graph.py`

- [ ] **Step 1: Create `models/osint_graph.py`**

```python
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

    def to_cytoscape(self):
        return {
            "data": {
                "id":    self.value,
                "label": self.label or self.value,
                "type":  self.type,
                "group": self.group,
                "color": self._GROUP_COLORS.get(self.group, "#6b6860"),
            }
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
```

> **Nota:** La clase `Edge` de PRUEBA_OSINT se renombra a `OsintEdge` para evitar colisión con cualquier nombre interno de SQLAlchemy. El tablename sigue siendo `"edge"`. Las funciones de servicio (`persist_facebook_data`, etc.) importarán `get_or_create_node` y `create_edge` desde este módulo.

- [ ] **Step 2: Commit**

```bash
git add models/osint_graph.py
git commit -m "feat: add Node/OsintEdge models bound to osint.db"
```

---

## Task 3: Services (adapted)

**Files:**
- Copy verbatim: `modules/osint/services/search_engine.py` ← from `PRUEBA_OSINT/app/services/search_engine.py`
- Create: `modules/osint/services/facebook_osint.py`
- Create: `modules/osint/services/x_osint.py`
- Create: `modules/osint/services/tiktok_osint.py`

- [ ] **Step 1: Copy search_engine.py verbatim**

```bash
cp "../PRUEBA_OSINT/app/services/search_engine.py" "modules/osint/services/search_engine.py"
```

(No imports from `app.*` — copy is exact.)

- [ ] **Step 2: Create `modules/osint/services/facebook_osint.py`**

Same content as `PRUEBA_OSINT/app/services/facebook_osint.py` with two import changes inside `persist_facebook_data`:

```python
def persist_facebook_data(facebook_data: dict, objetivo: str) -> int:
    from models import db
    from models.osint_graph import get_or_create_node, create_edge

    if not facebook_data:
        return 0

    session  = db.session
    created  = 0
    slug_obj = objetivo.lower().replace(" ", "_")

    person, _ = get_or_create_node(
        session, "person", slug_obj, objetivo, "target",
        {"fuente_enriquecimiento": "facebook_playwright"},
    )

    platform_node, _ = get_or_create_node(
        session, "platform", "facebook_platform", "Facebook", "platform",
        {"url": "https://facebook.com", "color_brand": "#1877F2"},
    )

    profile_url  = facebook_data.get("profile_url") or f"https://facebook.com/{slug_obj}"
    og           = facebook_data.get("og", {})
    profile_name = (
        og.get("og:title")
        or facebook_data.get("profile", {}).get("name")
        or objetivo
    )
    is_mock = facebook_data.get("is_mock", False)
    intel   = facebook_data.get("intel", {})

    profile_node, is_new = get_or_create_node(
        session,
        type  = "social_profile",
        value = profile_url,
        label = profile_name,
        group = "social_profile",
        metadata_dict = {
            "username":  objetivo,
            "fuente":    "playwright" if not is_mock else "mock_demo",
            "is_mock":   is_mock,
            "location":  intel.get("ubicacion_actual", ""),
            "work":      intel.get("trabajo", ""),
            "education": intel.get("educacion", ""),
            "bio":       intel.get("bio", ""),
            "confianza": "baja" if is_mock else "media",
        },
    )
    if is_new:
        created += 1

    create_edge(session, person, profile_node, "TIENE_PERFIL",
                {"fuente": "facebook_playwright", "is_mock": is_mock})
    create_edge(session, profile_node, platform_node, "PERTENECE_A",
                {"fuente": "facebook_playwright"})
    create_edge(session, person, platform_node, "ACTIVO_EN",
                {"fuente": "facebook_playwright"})

    for hint in facebook_data.get("email_hints", []):
        if hint and "@" in hint:
            email_val  = hint.lower().strip()
            email_node, en = get_or_create_node(
                session, "email", email_val, email_val, "contact",
                {"fuente": "facebook_playwright", "confianza": "baja"},
            )
            if en:
                created += 1
            create_edge(session, person, email_node, "USA_EMAIL",
                        {"fuente": "facebook_playwright", "confianza": "baja"})

    for conn in facebook_data.get("mutual_connections", []):
        if conn:
            conn_slug  = conn.lower().replace(" ", "_")
            conn_node, cn = get_or_create_node(
                session, "person", conn_slug, conn, "contact",
                {"fuente": "facebook_conexion_mutua", "confianza": "baja"},
            )
            if cn:
                created += 1
            create_edge(session, person, conn_node, "CONEXION_MUTUA",
                        {"fuente": "facebook_playwright", "confianza": "baja"})

    session.commit()
    return created
```

- [ ] **Step 3: Create `modules/osint/services/x_osint.py`**

Same logic as `PRUEBA_OSINT/app/services/x_osint.py`. Only change: two deferred imports inside `persist_x_profiles`:

```python
import re

_X_SYSTEM_PATHS = frozenset({
    "home", "search", "explore", "notifications", "messages", "settings",
    "i", "intent", "hashtag", "compose", "login", "logout", "signup",
    "privacy", "tos", "about", "jobs", "help", "status", "account",
    "oauth", "widgets", "twitter", "x",
})


def _extract_username(url: str) -> str | None:
    m = re.search(
        r'(?:x\.com|twitter\.com)/([a-zA-Z0-9_]{1,50})(?:/|$|\?|#)',
        url, re.IGNORECASE,
    )
    if m:
        username = m.group(1)
        if username.lower() not in _X_SYSTEM_PATHS:
            return username
    return None


def _extract_follower_hint(snippet: str) -> str | None:
    if not snippet:
        return None
    m = re.search(r'([\d,.]+[KkMm]?)\s*(?:Followers|followers|seguidores)', snippet)
    return m.group(0)[:40] if m else None


def extract_x_profiles(dork_results: list[dict], objetivo: str) -> dict:
    profiles: list[dict] = []
    seen_usernames: set[str] = set()

    for r in dork_results:
        url     = r.get("url",     "")
        title   = r.get("title",   "")
        snippet = r.get("snippet", "")

        username = _extract_username(url)
        if not username:
            continue
        if username.lower() in seen_usernames:
            continue
        seen_usernames.add(username.lower())

        profiles.append({
            "username":      username,
            "url":           f"https://x.com/{username}",
            "title":         title[:120] if title else f"@{username} en X",
            "bio_snippet":   snippet[:250] if snippet else None,
            "follower_hint": _extract_follower_hint(snippet),
            "source":        "duckduckgo_dork",
            "confianza":     "media",
        })

    intel_summary = next(
        (p["bio_snippet"] for p in profiles if p.get("bio_snippet")), None
    )

    return {
        "platform":      "X",
        "objetivo":      objetivo,
        "profiles":      profiles,
        "total_found":   len(profiles),
        "raw_count":     len(dork_results),
        "intel_summary": intel_summary,
    }


def persist_x_profiles(x_data: dict, objetivo: str) -> int:
    from models import db
    from models.osint_graph import get_or_create_node, create_edge

    if not x_data.get("profiles"):
        return 0

    session  = db.session
    created  = 0
    slug_obj = objetivo.lower().replace(" ", "_")

    person, _ = get_or_create_node(
        session, "person", slug_obj, objetivo, "target",
        {"fuente_enriquecimiento": "x_dork"},
    )

    platform_node, _ = get_or_create_node(
        session, "platform", "x_platform", "X (Twitter)", "x_platform",
        {"url": "https://x.com", "color_brand": "#1DA1F2"},
    )

    for p in x_data["profiles"]:
        profile_node, is_new = get_or_create_node(
            session,
            type  = "social_profile",
            value = p["url"],
            label = f"@{p['username']}",
            group = "x_profile",
            metadata_dict = {
                "username":      p["username"],
                "bio_snippet":   p.get("bio_snippet", ""),
                "follower_hint": p.get("follower_hint", ""),
                "fuente":        "duckduckgo_dork",
                "confianza":     "media",
            },
        )
        if is_new:
            created += 1

        create_edge(session, person, profile_node, "TIENE_CUENTA_EN",
                    {"fuente": "x_dork", "plataforma": "X"})
        create_edge(session, profile_node, platform_node, "PERTENECE_A",
                    {"fuente": "x_dork"})

    if x_data["profiles"]:
        create_edge(session, person, platform_node, "ACTIVO_EN",
                    {"perfiles_encontrados": x_data["total_found"]})

    session.commit()
    return created
```

- [ ] **Step 4: Create `modules/osint/services/tiktok_osint.py`**

Same as `PRUEBA_OSINT/app/services/tiktok_osint.py`. Only deferred imports in `persist_tiktok_profiles` change:

```python
import re


def _extract_tiktok_username(url: str) -> str | None:
    m = re.search(
        r'tiktok\.com/@([a-zA-Z0-9_.]{1,64})(?:/|$|\?|#)',
        url, re.IGNORECASE,
    )
    return m.group(1) if m else None


def _extract_video_count_hint(snippet: str) -> str | None:
    if not snippet:
        return None
    m = re.search(
        r'([\d,.]+[KkMm]?)\s*(?:[Vv]ideos?|[Ll]ikes?|[Ff]ollowers?|seguidores)',
        snippet,
    )
    return m.group(0)[:40] if m else None


def _extract_hashtags(snippet: str) -> list[str]:
    if not snippet:
        return []
    return re.findall(r'#([a-zA-Z0-9_]{2,40})', snippet)[:10]


def extract_tiktok_profiles(dork_results: list[dict], objetivo: str) -> dict:
    profiles:       list[dict] = []
    seen_usernames: set[str]   = set()
    all_hashtags:   list[str]  = []

    for r in dork_results:
        url     = r.get("url",     "")
        title   = r.get("title",   "")
        snippet = r.get("snippet", "")

        username = _extract_tiktok_username(url)
        if not username:
            continue
        if username.lower() in seen_usernames:
            continue
        seen_usernames.add(username.lower())

        tags = _extract_hashtags(snippet)
        all_hashtags.extend(tags)

        profiles.append({
            "username":   username,
            "url":        f"https://tiktok.com/@{username}",
            "title":      title[:120] if title else f"@{username} en TikTok",
            "bio_snippet": snippet[:250] if snippet else None,
            "stats_hint": _extract_video_count_hint(snippet),
            "hashtags":   tags,
            "source":     "duckduckgo_dork",
            "confianza":  "media",
        })

    seen_tags: set[str] = set()
    unique_tags = [t for t in all_hashtags if not (t in seen_tags or seen_tags.add(t))]  # type: ignore

    return {
        "platform":            "TikTok",
        "objetivo":            objetivo,
        "profiles":            profiles,
        "total_found":         len(profiles),
        "raw_count":           len(dork_results),
        "hashtags_detectados": unique_tags[:15],
    }


def persist_tiktok_profiles(tiktok_data: dict, objetivo: str) -> int:
    from models import db
    from models.osint_graph import get_or_create_node, create_edge

    if not tiktok_data.get("profiles"):
        return 0

    session  = db.session
    created  = 0
    slug_obj = objetivo.lower().replace(" ", "_")

    person, _ = get_or_create_node(
        session, "person", slug_obj, objetivo, "target",
        {"fuente_enriquecimiento": "tiktok_dork"},
    )

    platform_node, _ = get_or_create_node(
        session, "platform", "tiktok_platform", "TikTok", "tiktok_platform",
        {"url": "https://tiktok.com", "color_brand": "#ff0050"},
    )

    for p in tiktok_data["profiles"]:
        profile_node, is_new = get_or_create_node(
            session,
            type  = "social_profile",
            value = p["url"],
            label = f"@{p['username']}",
            group = "tiktok_profile",
            metadata_dict = {
                "username":    p["username"],
                "bio_snippet": p.get("bio_snippet", ""),
                "stats_hint":  p.get("stats_hint", ""),
                "hashtags":    p.get("hashtags", []),
                "fuente":      "duckduckgo_dork",
                "confianza":   "media",
            },
        )
        if is_new:
            created += 1

        create_edge(session, person, profile_node, "TIENE_CUENTA_EN",
                    {"fuente": "tiktok_dork", "plataforma": "TikTok"})
        create_edge(session, profile_node, platform_node, "PERTENECE_A",
                    {"fuente": "tiktok_dork"})

    if tiktok_data["profiles"]:
        create_edge(session, person, platform_node, "ACTIVO_EN",
                    {"perfiles_encontrados": tiktok_data["total_found"],
                     "hashtags_detectados":  tiktok_data.get("hashtags_detectados", [])})

    session.commit()
    return created
```

- [ ] **Step 5: Commit services**

```bash
git add modules/osint/services/
git commit -m "feat: add adapted OSINT services (facebook, x, tiktok, search_engine)"
```

---

## Task 4: Plugins (adapted)

**Files:**
- Copy verbatim: `modules/osint/plugins/base.py` ← `PRUEBA_OSINT/app/plugins/base.py`
- Create: `modules/osint/plugins/registry.py`
- Create: `modules/osint/plugins/ejemplo_ip.py`

- [ ] **Step 1: Copy `base.py` verbatim**

```bash
cp "../PRUEBA_OSINT/app/plugins/base.py" "modules/osint/plugins/base.py"
```

- [ ] **Step 2: Create `modules/osint/plugins/registry.py`**

Same as PRUEBA_OSINT except module path and base import:

```python
import importlib
import pkgutil
from pathlib import Path

from modules.osint.plugins.base import BaseOsintPlugin

_REGISTRY: list[BaseOsintPlugin] = []


def discover_plugins() -> None:
    plugins_dir = Path(__file__).parent

    for module_info in pkgutil.iter_modules([str(plugins_dir)]):
        if module_info.name in ("base", "registry"):
            continue

        module_path = f"modules.osint.plugins.{module_info.name}"
        try:
            mod = importlib.import_module(module_path)
        except Exception as exc:
            print(f"[osint-plugins] ERROR importando '{module_path}': {exc}")
            continue

        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseOsintPlugin)
                and attr is not BaseOsintPlugin
            ):
                try:
                    instance = attr()
                    _REGISTRY.append(instance)
                    print(f"[osint-plugins] Registrado: {instance.name}")
                except Exception as exc:
                    print(f"[osint-plugins] ERROR instanciando '{attr_name}': {exc}")


def get_plugins() -> list[BaseOsintPlugin]:
    return _REGISTRY
```

- [ ] **Step 3: Create `modules/osint/plugins/ejemplo_ip.py`**

```python
import requests
from modules.osint.plugins.base import BaseOsintPlugin


class IpGeoPlugin(BaseOsintPlugin):
    name          = "ip_geolocation"
    category      = "network"
    needs_api_key = False

    def ejecutar(self, objetivo: str) -> dict:
        try:
            r = requests.get(f"http://ip-api.com/json/{objetivo}", timeout=5)
            r.raise_for_status()
            return {"status": "ok", "plugin": self.name, "data": r.json()}
        except Exception as exc:
            return {"status": "error", "plugin": self.name, "error": str(exc)}
```

- [ ] **Step 4: Commit plugins**

```bash
git add modules/osint/plugins/
git commit -m "feat: add adapted OSINT plugin system (base, registry, ejemplo_ip)"
```

---

## Task 5: Social blueprint

**Files:**
- Copy verbatim: `modules/osint/social/scrapers/facebook_playwright.py` ← `PRUEBA_OSINT/app/blueprints/social/scrapers/facebook_playwright.py`
- Create: `modules/osint/social/__init__.py`
- Create: `modules/osint/social/routes.py`

- [ ] **Step 1: Copy `facebook_playwright.py` verbatim**

```bash
cp "../PRUEBA_OSINT/app/blueprints/social/scrapers/facebook_playwright.py" \
   "modules/osint/social/scrapers/facebook_playwright.py"
```

- [ ] **Step 2: Create `modules/osint/social/__init__.py`**

```python
from flask import Blueprint

social_osint_bp = Blueprint("social_osint", __name__)

from modules.osint.social import routes  # noqa: E402, F401
```

- [ ] **Step 3: Create `modules/osint/social/routes.py`**

Full adapted file (all `app.*` imports replaced, blueprint renamed, template path updated):

```python
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FutureTimeoutError
from flask import render_template, request
from modules.osint.auth import login_required
from modules.osint.social import social_osint_bp
from modules.osint.social.scrapers.facebook_playwright import scrape_facebook_profile
from modules.osint.services.search_engine import ejecutar_dork_universal
from modules.osint.services.x_osint import extract_x_profiles, persist_x_profiles
from modules.osint.services.tiktok_osint import extract_tiktok_profiles, persist_tiktok_profiles
from modules.osint.services.facebook_osint import persist_facebook_data
from modules.osint.plugins.registry import get_plugins

GITHUB_HEADERS = {
    "User-Agent": "OSINT-Terminal/1.0 (educational research)",
    "Accept":     "application/vnd.github+json",
}

REDDIT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/html, */*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Referer":         "https://www.reddit.com/",
}

TIMEOUT          = 10
PARALLEL_TIMEOUT = 30


def _fetch_github(username: str) -> tuple:
    errors  = []
    profile = None
    repos   = []

    try:
        r = requests.get(
            f"https://api.github.com/users/{username}",
            headers=GITHUB_HEADERS, timeout=TIMEOUT,
        )
        r.raise_for_status()
        profile = r.json()
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else "?"
        if code == 404:
            errors.append(f"GitHub: usuario '{username}' no encontrado.")
        else:
            errors.append(f"GitHub: error HTTP {code}.")
    except requests.exceptions.ConnectionError:
        errors.append("GitHub: error de conexión.")
    except requests.exceptions.Timeout:
        errors.append("GitHub: tiempo de espera agotado.")
    except requests.exceptions.RequestException as e:
        errors.append(f"GitHub: {e}.")

    if profile:
        try:
            r2 = requests.get(
                f"https://api.github.com/users/{username}/repos",
                headers=GITHUB_HEADERS,
                params={"per_page": 10, "sort": "updated"},
                timeout=TIMEOUT,
            )
            if r2.status_code == 200:
                repos = r2.json()
        except requests.exceptions.RequestException as e:
            errors.append(f"GitHub repos: {e}.")

    return profile, repos, errors


def _fetch_reddit(username: str) -> tuple:
    errors  = []
    profile = None
    posts   = []

    try:
        r = requests.get(
            f"https://www.reddit.com/user/{username}/about.json",
            headers=REDDIT_HEADERS, timeout=TIMEOUT,
        )
        r.raise_for_status()
        data    = r.json()
        profile = data.get("data", {})
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else "?"
        if code == 403:
            errors.append("Reddit: acceso denegado (403).")
        elif code == 429:
            errors.append("Reddit: rate limit (429).")
        elif code == 404:
            errors.append(f"Reddit: usuario '{username}' no encontrado.")
        else:
            errors.append(f"Reddit: error HTTP {code}.")
    except requests.exceptions.ConnectionError:
        errors.append("Reddit: error de conexión.")
    except requests.exceptions.Timeout:
        errors.append("Reddit: tiempo de espera agotado.")
    except requests.exceptions.RequestException as e:
        errors.append(f"Reddit: {e}.")

    if profile:
        try:
            r2 = requests.get(
                f"https://www.reddit.com/user/{username}/submitted.json",
                headers=REDDIT_HEADERS, params={"limit": 10}, timeout=TIMEOUT,
            )
            r2.raise_for_status()
            children = r2.json().get("data", {}).get("children", [])
            posts    = [c["data"] for c in children]
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response else "?"
            errors.append(f"Reddit posts: error HTTP {code}.")
        except requests.exceptions.RequestException as e:
            errors.append(f"Reddit posts: {e}.")

    return profile, posts, errors


def _task_github(username):
    profile, repos, errors = _fetch_github(username)
    return {"profile": profile, "repos": repos, "errors": errors}

def _task_reddit(username):
    profile, posts, errors = _fetch_reddit(username)
    return {"profile": profile, "posts": posts, "errors": errors}

def _task_facebook(username):
    data, errors = scrape_facebook_profile(username)
    return {"data": data, "errors": errors}

def _task_x(username):
    raw    = ejecutar_dork_universal(username, ["x"], max_results=30)
    res    = raw.get("x", {})
    x_data = extract_x_profiles(res.get("results", []), username)
    return {"data": x_data, "errors": res.get("errors", [])}

def _task_tiktok(username):
    raw         = ejecutar_dork_universal(username, ["tiktok"], max_results=30)
    res         = raw.get("tiktok", {})
    tiktok_data = extract_tiktok_profiles(res.get("results", []), username)
    return {"data": tiktok_data, "errors": res.get("errors", [])}


_ALL_TASKS = {
    "github":   _task_github,
    "reddit":   _task_reddit,
    "facebook": _task_facebook,
    "x":        _task_x,
    "tiktok":   _task_tiktok,
}


def _ejecutar_busqueda_paralela(username: str) -> dict:
    results: dict = {}
    with ThreadPoolExecutor(max_workers=5, thread_name_prefix="osint") as executor:
        futures = {
            executor.submit(fn, username): key
            for key, fn in _ALL_TASKS.items()
        }
        try:
            for future in as_completed(futures, timeout=PARALLEL_TIMEOUT + 10):
                key = futures[future]
                try:
                    results[key] = future.result(timeout=PARALLEL_TIMEOUT)
                except FutureTimeoutError:
                    results[key] = {"errors": [f"{key}: timeout ({PARALLEL_TIMEOUT}s)."]}
                except Exception as exc:
                    results[key] = {"errors": [f"{key}: error inesperado ({exc})."]}
        except FutureTimeoutError:
            pass

    for key in _ALL_TASKS:
        if key not in results:
            results[key] = {"errors": [f"{key}: no completó en el tiempo máximo."]}

    return results


@social_osint_bp.route("/lookup")
@login_required
def lookup():
    username = request.args.get("q", "").strip()
    source   = request.args.get("source", "github")

    if not username:
        return render_template(
            "osint/social_fragment.html",
            username=username, source=source,
            errors=["No se proporcionó un nombre de usuario."],
        )

    github_profile = github_repos = None
    reddit_profile = reddit_posts = None
    facebook_data  = None
    x_data         = None
    tiktok_data    = None
    errors: list   = []

    if source == "all":
        parallel = _ejecutar_busqueda_paralela(username)

        gh = parallel.get("github", {})
        github_profile = gh.get("profile")
        github_repos   = gh.get("repos", [])
        errors.extend(gh.get("errors", []))

        rd = parallel.get("reddit", {})
        reddit_profile = rd.get("profile")
        reddit_posts   = rd.get("posts", [])
        errors.extend(rd.get("errors", []))

        fb = parallel.get("facebook", {})
        facebook_data = fb.get("data")
        errors.extend(fb.get("errors", []))
        if facebook_data:
            try:
                facebook_data["saved_nodes"] = persist_facebook_data(facebook_data, username)
            except Exception as exc:
                errors.append(f"Facebook DB persist: {exc}")
                facebook_data["saved_nodes"] = 0

        x_res  = parallel.get("x", {})
        x_data = x_res.get("data")
        errors.extend(x_res.get("errors", []))
        if x_data:
            try:
                x_data["saved_nodes"] = persist_x_profiles(x_data, username)
            except Exception as exc:
                errors.append(f"X DB persist: {exc}")
                x_data["saved_nodes"] = 0

        tk_res      = parallel.get("tiktok", {})
        tiktok_data = tk_res.get("data")
        errors.extend(tk_res.get("errors", []))
        if tiktok_data:
            try:
                tiktok_data["saved_nodes"] = persist_tiktok_profiles(tiktok_data, username)
            except Exception as exc:
                errors.append(f"TikTok DB persist: {exc}")
                tiktok_data["saved_nodes"] = 0

    else:
        if source in ("github", "both"):
            github_profile, github_repos, gh_errors = _fetch_github(username)
            errors.extend(gh_errors)

        if source in ("reddit", "both"):
            reddit_profile, reddit_posts, rd_errors = _fetch_reddit(username)
            errors.extend(rd_errors)

        if source == "facebook":
            facebook_data, fb_errors = scrape_facebook_profile(username)
            errors.extend(fb_errors)
            if facebook_data:
                try:
                    facebook_data["saved_nodes"] = persist_facebook_data(facebook_data, username)
                except Exception as exc:
                    errors.append(f"Facebook DB persist: {exc}")
                    facebook_data["saved_nodes"] = 0

        plataformas_dork = []
        if source == "x":
            plataformas_dork.append("x")
        if source == "tiktok":
            plataformas_dork.append("tiktok")
        if source == "deep_all":
            plataformas_dork.extend(["x", "tiktok", "facebook"])
            facebook_data, fb_errors = scrape_facebook_profile(username)
            errors.extend(fb_errors)
            if facebook_data:
                try:
                    facebook_data["saved_nodes"] = persist_facebook_data(facebook_data, username)
                except Exception as exc:
                    errors.append(f"Facebook DB persist: {exc}")
                    facebook_data["saved_nodes"] = 0

        if plataformas_dork:
            dork_results = ejecutar_dork_universal(username, plataformas_dork, max_results=50)

            if "x" in dork_results:
                raw_x  = dork_results["x"].get("results", [])
                errors.extend(dork_results["x"].get("errors", []))
                x_data = extract_x_profiles(raw_x, username)
                try:
                    x_data["saved_nodes"] = persist_x_profiles(x_data, username)
                except Exception as exc:
                    errors.append(f"X DB persist: {exc}")
                    x_data["saved_nodes"] = 0

            if "tiktok" in dork_results:
                raw_tk      = dork_results["tiktok"].get("results", [])
                errors.extend(dork_results["tiktok"].get("errors", []))
                tiktok_data = extract_tiktok_profiles(raw_tk, username)
                try:
                    tiktok_data["saved_nodes"] = persist_tiktok_profiles(tiktok_data, username)
                except Exception as exc:
                    errors.append(f"TikTok DB persist: {exc}")
                    tiktok_data["saved_nodes"] = 0

    plugin_results = []
    for plugin in get_plugins():
        try:
            plugin_results.append(plugin.ejecutar(username))
        except Exception as exc:
            errors.append(f"Plugin {plugin.name}: {exc}")

    return render_template(
        "osint/social_fragment.html",
        username=username,
        source=source,
        github_profile=github_profile,
        github_repos=github_repos,
        reddit_profile=reddit_profile,
        reddit_posts=reddit_posts,
        facebook_data=facebook_data,
        x_data=x_data,
        tiktok_data=tiktok_data,
        plugin_results=plugin_results,
        errors=errors,
    )
```

- [ ] **Step 4: Commit social blueprint**

```bash
git add modules/osint/social/
git commit -m "feat: add adapted social OSINT blueprint (GitHub, Reddit, Facebook, X, TikTok)"
```

---

## Task 6: Opendata blueprint

**Files:**
- Create: `modules/osint/opendata/__init__.py`
- Create: `modules/osint/opendata/routes.py`

- [ ] **Step 1: Create `modules/osint/opendata/__init__.py`**

```python
from flask import Blueprint

opendata_osint_bp = Blueprint("opendata_osint", __name__)

from modules.osint.opendata import routes  # noqa: E402, F401
```

- [ ] **Step 2: Create `modules/osint/opendata/routes.py`**

```python
import requests
from flask import render_template, request
from modules.osint.auth import login_required
from modules.osint.opendata import opendata_osint_bp

HEADERS = {"User-Agent": "OSINT-Tool/1.0 (educational research)"}
TIMEOUT = 8


def _fetch_ip_geo(ip):
    errors = []
    result = None
    try:
        r = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query"},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                result = data
            else:
                errors.append(f"ip-api.com: {data.get('message', 'consulta fallida')}.")
        else:
            errors.append(f"ip-api.com: respuesta inesperada ({r.status_code}).")
    except requests.exceptions.ConnectionError:
        errors.append("ip-api.com: error de conexión.")
    except requests.exceptions.Timeout:
        errors.append("ip-api.com: tiempo de espera agotado.")
    except requests.exceptions.RequestException as e:
        errors.append(f"ip-api.com: error ({e}).")
    return result, errors


def _fetch_domain_rdap(domain):
    errors = []
    result = None
    try:
        r = requests.get(
            f"https://rdap.org/domain/{domain}",
            headers=HEADERS, timeout=TIMEOUT,
        )
        if r.status_code == 200:
            result = r.json()
        elif r.status_code == 404:
            errors.append(f"RDAP: dominio '{domain}' no encontrado.")
        else:
            errors.append(f"RDAP: respuesta inesperada ({r.status_code}).")
    except requests.exceptions.ConnectionError:
        errors.append("RDAP: error de conexión.")
    except requests.exceptions.Timeout:
        errors.append("RDAP: tiempo de espera agotado.")
    except requests.exceptions.RequestException as e:
        errors.append(f"RDAP: error ({e}).")
    return result, errors


def _fetch_crt_sh(domain):
    errors = []
    certs  = []
    try:
        r = requests.get(
            "https://crt.sh/",
            params={"q": domain, "output": "json"},
            headers=HEADERS, timeout=TIMEOUT,
        )
        if r.status_code == 200:
            raw  = r.json()
            seen = set()
            for entry in raw[:50]:
                name = entry.get("name_value", "")
                for sub in name.split("\n"):
                    sub = sub.strip()
                    if sub and sub not in seen:
                        seen.add(sub)
                        certs.append({
                            "name":       sub,
                            "issuer":     entry.get("issuer_name", ""),
                            "not_before": entry.get("not_before", ""),
                            "not_after":  entry.get("not_after", ""),
                        })
        else:
            errors.append(f"crt.sh: respuesta inesperada ({r.status_code}).")
    except requests.exceptions.ConnectionError:
        errors.append("crt.sh: error de conexión.")
    except requests.exceptions.Timeout:
        errors.append("crt.sh: tiempo de espera agotado.")
    except requests.exceptions.RequestException as e:
        errors.append(f"crt.sh: error ({e}).")
    return certs, errors


def _parse_rdap(data):
    if not data:
        return {}
    parsed = {
        "handle":      data.get("handle"),
        "ldhName":     data.get("ldhName"),
        "status":      data.get("status", []),
        "events":      [],
        "nameservers": [],
        "entities":    [],
    }
    for ev in data.get("events", []):
        parsed["events"].append({
            "action": ev.get("eventAction"),
            "date":   ev.get("eventDate", "")[:10],
        })
    for ns in data.get("nameservers", []):
        parsed["nameservers"].append(ns.get("ldhName", ""))
    for ent in data.get("entities", []):
        roles = ent.get("roles", [])
        vcard = ent.get("vcardArray", [None, []])[1]
        name  = next((v[3] for v in vcard if v[0] == "fn"), None) if vcard else None
        parsed["entities"].append({"roles": roles, "name": name})
    return parsed


@opendata_osint_bp.route("/lookup")
@login_required
def lookup():
    query  = request.args.get("q", "").strip()
    source = request.args.get("source", "ip")

    if not query:
        return render_template(
            "osint/opendata_fragment.html",
            query=query, source=source,
            errors=["No se proporcionó una consulta."],
        )

    ip_data = rdap_data = crt_data = None
    errors = []

    if source == "ip":
        ip_data, ip_errors = _fetch_ip_geo(query)
        errors.extend(ip_errors)

    elif source == "domain":
        rdap_raw, rdap_errors = _fetch_domain_rdap(query)
        rdap_data = _parse_rdap(rdap_raw)
        errors.extend(rdap_errors)
        crt_data, crt_errors = _fetch_crt_sh(query)
        errors.extend(crt_errors)

    elif source == "both":
        ip_data, ip_errors = _fetch_ip_geo(query)
        errors.extend(ip_errors)
        rdap_raw, rdap_errors = _fetch_domain_rdap(query)
        rdap_data = _parse_rdap(rdap_raw)
        errors.extend(rdap_errors)
        crt_data, crt_errors = _fetch_crt_sh(query)
        errors.extend(crt_errors)

    return render_template(
        "osint/opendata_fragment.html",
        query=query, source=source,
        ip_data=ip_data, rdap_data=rdap_data, crt_data=crt_data,
        errors=errors,
    )
```

- [ ] **Step 3: Commit opendata blueprint**

```bash
git add modules/osint/opendata/
git commit -m "feat: add adapted opendata OSINT blueprint (IP, RDAP, crt.sh)"
```

---

## Task 7: Analytics blueprint

**Files:**
- Copy verbatim: `modules/osint/analytics/graph_builder.py` ← `PRUEBA_OSINT/app/blueprints/analytics/graph_builder.py`
- Create: `modules/osint/analytics/__init__.py`
- Create: `modules/osint/analytics/routes.py`

- [ ] **Step 1: Copy `graph_builder.py` verbatim**

```bash
cp "../PRUEBA_OSINT/app/blueprints/analytics/graph_builder.py" \
   "modules/osint/analytics/graph_builder.py"
```

- [ ] **Step 2: Create `modules/osint/analytics/__init__.py`**

```python
from flask import Blueprint

analytics_osint_bp = Blueprint("analytics_osint", __name__)

from modules.osint.analytics import routes  # noqa: E402, F401
```

- [ ] **Step 3: Create `modules/osint/analytics/routes.py`**

Only the `/graph` JSON endpoint (the `/view` page is not needed — the graph renders in the console panel):

```python
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
```

- [ ] **Step 4: Commit analytics blueprint**

```bash
git add modules/osint/analytics/
git commit -m "feat: add adapted analytics OSINT blueprint (/graph JSON endpoint)"
```

---

## Task 8: Fragment templates

**Files:**
- Create: `templates/osint/social_fragment.html`
- Create: `templates/osint/opendata_fragment.html`

- [ ] **Step 1: Create `templates/osint/` directory**

```bash
mkdir -p templates/osint
```

- [ ] **Step 2: Create `templates/osint/social_fragment.html`**

```html
<style>
.osint-frag{font-family:'JetBrains Mono',monospace;color:#d0d8e8;font-size:.82rem}
.osint-frag .result-section{margin-bottom:1.5rem;border-top:1px solid #1e2535;padding-top:1rem}
.osint-frag .section-title{display:flex;align-items:center;gap:.5rem;font-size:.85rem;font-weight:600;margin-bottom:.75rem;color:#a0b4cc}
.osint-frag .section-tag{background:#0d1a2e;border:1px solid #2a4060;color:#4bc8a8;padding:2px 8px;border-radius:3px;font-size:.72rem;letter-spacing:.05em}
.osint-frag .badge{background:#0d1a2e;border:1px solid #2a4060;color:#8ab4cc;padding:1px 7px;border-radius:3px;font-size:.7rem;margin-right:.3rem}
.osint-frag .badge-x{color:#1DA1F2;border-color:#1a3a5c}
.osint-frag .badge-tiktok{color:#ff0050;border-color:#5c001a}
.osint-frag .badge-dork{color:#a855f7;border-color:#3a1a5c}
.osint-frag .badge-demo{color:#f59e0b;border-color:#5c3a00}
.osint-frag .data-table{width:100%;border-collapse:collapse;margin-bottom:.75rem}
.osint-frag .data-table td,.osint-frag .data-table th{padding:4px 8px;border-bottom:1px solid #1e2535;vertical-align:top}
.osint-frag .data-table th{color:#6b8aaa;font-weight:500;text-align:left;font-size:.75rem}
.osint-frag .col-key{color:#6b8aaa;width:140px;white-space:nowrap}
.osint-frag .col-desc{max-width:260px;word-break:break-word}
.osint-frag .ext-link{color:#4bc8a8;text-decoration:none}
.osint-frag .ext-link:hover{text-decoration:underline}
.osint-frag .table-wrap{overflow-x:auto;max-height:280px;overflow-y:auto}
.osint-frag .error-block{background:#1a0a0a;border:1px solid #5c1a1a;border-radius:4px;padding:.5rem .75rem;margin-bottom:1rem}
.osint-frag .error-line{color:#f87171;margin:2px 0;font-size:.78rem}
.osint-frag .profile-card{display:flex;gap:1rem;margin-bottom:.75rem}
.osint-frag .profile-avatar{width:64px;height:64px;border-radius:4px;object-fit:cover;border:1px solid #2a4060;flex-shrink:0}
.osint-frag .dork-notice{background:#0a0d1a;border-left:3px solid #4b6ac8;padding:.4rem .75rem;font-size:.77rem;color:#8ab4cc;margin-bottom:.75rem}
.osint-frag .subsection-title{color:#6b8aaa;font-size:.78rem;font-weight:600;margin:.75rem 0 .4rem;text-transform:uppercase;letter-spacing:.05em}
.osint-frag .empty-state{text-align:center;padding:2rem;color:#4a5a6a;font-size:.85rem}
.osint-frag .results-meta{margin-bottom:.5rem;font-size:.77rem;color:#6b8aaa}
</style>

<div class="osint-frag">
  <div class="results-meta">
    Objetivo: <strong>{{ username }}</strong> —
    Fuente:
    {% if source == 'github' %}<span class="badge">GitHub</span>
    {% elif source == 'reddit' %}<span class="badge">Reddit</span>
    {% elif source == 'facebook' %}<span class="badge">Facebook</span>
    {% elif source == 'x' %}<span class="badge badge-x">X</span>
    {% elif source == 'tiktok' %}<span class="badge badge-tiktok">TikTok</span>
    {% elif source == 'both' %}<span class="badge">GitHub</span><span class="badge">Reddit</span>
    {% elif source == 'deep_all' %}<span class="badge badge-x">X</span><span class="badge badge-tiktok">TikTok</span><span class="badge">Facebook</span>
    {% elif source == 'all' %}<span class="badge">GitHub</span><span class="badge">Reddit</span><span class="badge">Facebook</span><span class="badge badge-x">X</span><span class="badge badge-tiktok">TikTok</span>
    {% endif %}
  </div>

  {% if errors %}
  <div class="error-block">
    {% for err in errors %}<p class="error-line">⚠ {{ err }}</p>{% endfor %}
  </div>
  {% endif %}

  {% if github_profile %}
  <section class="result-section">
    <h3 class="section-title"><span class="section-tag">GITHUB</span> Perfil</h3>
    <div class="profile-card">
      {% if github_profile.avatar_url %}
      <img src="{{ github_profile.avatar_url }}" alt="avatar" class="profile-avatar">
      {% endif %}
      <div>
        <table class="data-table">
          <tbody>
            <tr><td class="col-key">Nombre</td><td>{{ github_profile.name or '—' }}</td></tr>
            <tr><td class="col-key">Login</td><td>{{ github_profile.login }}</td></tr>
            <tr><td class="col-key">Correo</td><td>{{ github_profile.email or '—' }}</td></tr>
            <tr><td class="col-key">Empresa</td><td>{{ github_profile.company or '—' }}</td></tr>
            <tr><td class="col-key">Ubicación</td><td>{{ github_profile.location or '—' }}</td></tr>
            <tr><td class="col-key">Bio</td><td>{{ github_profile.bio or '—' }}</td></tr>
            <tr><td class="col-key">Twitter</td><td>{{ github_profile.twitter_username or '—' }}</td></tr>
            <tr><td class="col-key">Repos públicos</td><td>{{ github_profile.public_repos }}</td></tr>
            <tr><td class="col-key">Seguidores</td><td>{{ github_profile.followers }}</td></tr>
            <tr><td class="col-key">URL</td><td><a href="{{ github_profile.html_url }}" target="_blank" rel="noopener" class="ext-link">{{ github_profile.html_url }}</a></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
  {% endif %}

  {% if github_repos %}
  <section class="result-section">
    <h3 class="section-title"><span class="section-tag">GITHUB</span> Repos ({{ github_repos|length }})</h3>
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr><th>Repositorio</th><th>Lenguaje</th><th>Stars</th><th>Actualizado</th></tr></thead>
        <tbody>
          {% for repo in github_repos %}
          <tr>
            <td><a href="{{ repo.html_url }}" target="_blank" rel="noopener" class="ext-link">{{ repo.name }}</a></td>
            <td>{{ repo.language or '—' }}</td>
            <td>{{ repo.stargazers_count }}</td>
            <td>{{ repo.updated_at[:10] if repo.updated_at else '—' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </section>
  {% endif %}

  {% if reddit_profile %}
  <section class="result-section">
    <h3 class="section-title"><span class="section-tag">REDDIT</span> Perfil</h3>
    <table class="data-table">
      <tbody>
        <tr><td class="col-key">Username</td><td>{{ reddit_profile.name }}</td></tr>
        <tr><td class="col-key">Karma (total)</td><td>{{ (reddit_profile.total_karma or 0)|int }}</td></tr>
        <tr><td class="col-key">Karma (posts)</td><td>{{ (reddit_profile.link_karma or 0)|int }}</td></tr>
        <tr><td class="col-key">URL</td><td><a href="https://reddit.com/u/{{ reddit_profile.name }}" target="_blank" rel="noopener" class="ext-link">reddit.com/u/{{ reddit_profile.name }}</a></td></tr>
      </tbody>
    </table>
  </section>
  {% endif %}

  {% if reddit_posts %}
  <section class="result-section">
    <h3 class="section-title"><span class="section-tag">REDDIT</span> Posts ({{ reddit_posts|length }})</h3>
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr><th>Título</th><th>Subreddit</th><th>Score</th></tr></thead>
        <tbody>
          {% for post in reddit_posts %}
          <tr>
            <td><a href="https://reddit.com{{ post.permalink }}" target="_blank" rel="noopener" class="ext-link">{{ post.title[:70] }}{% if post.title|length > 70 %}…{% endif %}</a></td>
            <td>r/{{ post.subreddit }}</td>
            <td>{{ post.score }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </section>
  {% endif %}

  {% if facebook_data %}
  <section class="result-section">
    <h3 class="section-title"><span class="section-tag">FACEBOOK</span> Perfil {% if facebook_data.is_mock %}<span class="badge badge-demo">DEMO</span>{% endif %}</h3>
    {% if facebook_data.intel %}
    <table class="data-table">
      <tbody>
        <tr><td class="col-key">Ubicación</td><td>{{ facebook_data.intel.ubicacion_actual }}</td></tr>
        <tr><td class="col-key">Trabajo</td><td>{{ facebook_data.intel.trabajo }}</td></tr>
        <tr><td class="col-key">Educación</td><td>{{ facebook_data.intel.educacion }}</td></tr>
        <tr><td class="col-key">Bio</td><td>{{ facebook_data.intel.bio }}</td></tr>
      </tbody>
    </table>
    {% endif %}
    {% if facebook_data.email_hints %}
    <p style="font-size:.77rem;color:#4bc8a8">Correos detectados: {{ facebook_data.email_hints|join(', ') }}</p>
    {% endif %}
    {% if facebook_data.saved_nodes %}<p style="font-size:.75rem;color:#4bc87a">{{ facebook_data.saved_nodes }} nodos guardados en grafo.</p>{% endif %}
  </section>
  {% endif %}

  {% if x_data %}
  <section class="result-section">
    <h3 class="section-title"><span class="section-tag" style="color:#1DA1F2">X/TWITTER</span> <span class="badge badge-dork">DuckDuckGo Dork</span></h3>
    <p class="dork-notice">site:x.com "{{ username }}" → {{ x_data.total_found }} perfiles en {{ x_data.raw_count }} resultados.</p>
    {% if x_data.profiles %}
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr><th>Username</th><th>URL</th><th>Bio</th><th>Confianza</th></tr></thead>
        <tbody>
          {% for p in x_data.profiles %}
          <tr>
            <td style="color:#1DA1F2">@{{ p.username }}</td>
            <td><a href="{{ p.url }}" target="_blank" rel="noopener" class="ext-link">{{ p.url }}</a></td>
            <td class="col-desc">{{ p.bio_snippet or '—' }}</td>
            <td>{{ p.confianza }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}<p style="color:#4a5a6a;font-size:.77rem">Sin perfiles identificados.</p>{% endif %}
    {% if x_data.saved_nodes %}<p style="font-size:.75rem;color:#4bc87a">{{ x_data.saved_nodes }} nodos guardados.</p>{% endif %}
  </section>
  {% endif %}

  {% if tiktok_data %}
  <section class="result-section">
    <h3 class="section-title"><span class="section-tag" style="color:#ff0050">TIKTOK</span> <span class="badge badge-dork">DuckDuckGo Dork</span></h3>
    <p class="dork-notice">site:tiktok.com "{{ username }}" → {{ tiktok_data.total_found }} perfiles en {{ tiktok_data.raw_count }} resultados.</p>
    {% if tiktok_data.profiles %}
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr><th>Username</th><th>URL</th><th>Stats</th></tr></thead>
        <tbody>
          {% for p in tiktok_data.profiles %}
          <tr>
            <td style="color:#ff0050">@{{ p.username }}</td>
            <td><a href="{{ p.url }}" target="_blank" rel="noopener" class="ext-link">{{ p.url }}</a></td>
            <td>{{ p.stats_hint or '—' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}<p style="color:#4a5a6a;font-size:.77rem">Sin perfiles identificados.</p>{% endif %}
    {% if tiktok_data.saved_nodes %}<p style="font-size:.75rem;color:#4bc87a">{{ tiktok_data.saved_nodes }} nodos guardados.</p>{% endif %}
  </section>
  {% endif %}

  {% if not github_profile and not reddit_profile and not facebook_data and not x_data and not tiktok_data and not errors %}
  <div class="empty-state"><p>Sin resultados para <strong>{{ username }}</strong>.</p></div>
  {% endif %}
</div>
```

- [ ] **Step 3: Create `templates/osint/opendata_fragment.html`**

```html
<style>
.osint-frag{font-family:'JetBrains Mono',monospace;color:#d0d8e8;font-size:.82rem}
.osint-frag .result-section{margin-bottom:1.5rem;border-top:1px solid #1e2535;padding-top:1rem}
.osint-frag .section-title{display:flex;align-items:center;gap:.5rem;font-size:.85rem;font-weight:600;margin-bottom:.75rem;color:#a0b4cc}
.osint-frag .section-tag{background:#0d1a2e;border:1px solid #2a4060;color:#4bc8a8;padding:2px 8px;border-radius:3px;font-size:.72rem;letter-spacing:.05em}
.osint-frag .data-table{width:100%;border-collapse:collapse;margin-bottom:.75rem}
.osint-frag .data-table td,.osint-frag .data-table th{padding:4px 8px;border-bottom:1px solid #1e2535;vertical-align:top}
.osint-frag .data-table th{color:#6b8aaa;font-weight:500;text-align:left;font-size:.75rem}
.osint-frag .col-key{color:#6b8aaa;width:140px;white-space:nowrap}
.osint-frag .mono-cell{font-family:'JetBrains Mono',monospace;font-size:.77rem}
.osint-frag .col-desc{max-width:260px;word-break:break-word}
.osint-frag .table-wrap{overflow-x:auto;max-height:280px;overflow-y:auto}
.osint-frag .error-block{background:#1a0a0a;border:1px solid #5c1a1a;border-radius:4px;padding:.5rem .75rem;margin-bottom:1rem}
.osint-frag .error-line{color:#f87171;margin:2px 0;font-size:.78rem}
.osint-frag .badge{background:#0d1a2e;border:1px solid #2a4060;color:#8ab4cc;padding:1px 7px;border-radius:3px;font-size:.7rem;margin-right:.3rem}
.osint-frag .subsection-title{color:#6b8aaa;font-size:.78rem;font-weight:600;margin:.75rem 0 .4rem;text-transform:uppercase;letter-spacing:.05em}
.osint-frag .empty-state{text-align:center;padding:2rem;color:#4a5a6a;font-size:.85rem}
.osint-frag .results-meta{margin-bottom:.5rem;font-size:.77rem;color:#6b8aaa}
</style>

<div class="osint-frag">
  <div class="results-meta">
    Consulta: <strong>{{ query }}</strong> —
    Fuente:
    {% if source == 'ip' %}<span class="badge">Geoloc. IP</span>
    {% elif source == 'domain' %}<span class="badge">RDAP</span><span class="badge">crt.sh</span>
    {% else %}<span class="badge">IP</span><span class="badge">RDAP</span><span class="badge">crt.sh</span>{% endif %}
  </div>

  {% if errors %}
  <div class="error-block">
    {% for err in errors %}<p class="error-line">⚠ {{ err }}</p>{% endfor %}
  </div>
  {% endif %}

  {% if ip_data %}
  <section class="result-section">
    <h3 class="section-title"><span class="section-tag">IP-API</span> Geolocalización</h3>
    <table class="data-table">
      <tbody>
        <tr><td class="col-key">IP</td><td>{{ ip_data.query }}</td></tr>
        <tr><td class="col-key">País</td><td>{{ ip_data.country }} ({{ ip_data.countryCode }})</td></tr>
        <tr><td class="col-key">Región</td><td>{{ ip_data.regionName }}</td></tr>
        <tr><td class="col-key">Ciudad</td><td>{{ ip_data.city }}</td></tr>
        <tr><td class="col-key">Coordenadas</td><td>{{ ip_data.lat }}, {{ ip_data.lon }}</td></tr>
        <tr><td class="col-key">Zona horaria</td><td>{{ ip_data.timezone }}</td></tr>
        <tr><td class="col-key">ISP</td><td>{{ ip_data.isp }}</td></tr>
        <tr><td class="col-key">Organización</td><td>{{ ip_data.org }}</td></tr>
        <tr><td class="col-key">AS</td><td>{{ ip_data.as }}</td></tr>
      </tbody>
    </table>
  </section>
  {% endif %}

  {% if rdap_data and rdap_data.ldhName %}
  <section class="result-section">
    <h3 class="section-title"><span class="section-tag">RDAP</span> Registro de dominio</h3>
    <table class="data-table">
      <tbody>
        <tr><td class="col-key">Dominio</td><td>{{ rdap_data.ldhName }}</td></tr>
        <tr><td class="col-key">Handle</td><td>{{ rdap_data.handle or '—' }}</td></tr>
        <tr><td class="col-key">Estado</td><td>{{ rdap_data.status|join(', ') if rdap_data.status else '—' }}</td></tr>
        {% for ev in rdap_data.events %}
        <tr><td class="col-key">{{ ev.action }}</td><td>{{ ev.date }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
    {% if rdap_data.nameservers %}
    <p class="subsection-title">Nameservers</p>
    <table class="data-table"><tbody>{% for ns in rdap_data.nameservers %}<tr><td>{{ ns }}</td></tr>{% endfor %}</tbody></table>
    {% endif %}
    {% if rdap_data.entities %}
    <p class="subsection-title">Entidades</p>
    <table class="data-table"><thead><tr><th>Nombre</th><th>Roles</th></tr></thead>
    <tbody>{% for ent in rdap_data.entities %}<tr><td>{{ ent.name or '—' }}</td><td>{{ ent.roles|join(', ') }}</td></tr>{% endfor %}</tbody></table>
    {% endif %}
  </section>
  {% endif %}

  {% if crt_data %}
  <section class="result-section">
    <h3 class="section-title"><span class="section-tag">CRT.SH</span> Certificados ({{ crt_data|length }})</h3>
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr><th>Nombre / Subdominio</th><th>Emisor</th><th>Válido desde</th><th>Válido hasta</th></tr></thead>
        <tbody>
          {% for cert in crt_data %}
          <tr>
            <td class="mono-cell">{{ cert.name }}</td>
            <td class="col-desc">{{ cert.issuer[:60] }}{% if cert.issuer|length > 60 %}…{% endif %}</td>
            <td>{{ cert.not_before[:10] if cert.not_before else '—' }}</td>
            <td>{{ cert.not_after[:10] if cert.not_after else '—' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </section>
  {% endif %}

  {% if not ip_data and not rdap_data and not crt_data and not errors %}
  <div class="empty-state"><p>Sin resultados para <strong>{{ query }}</strong>.</p></div>
  {% endif %}
</div>
```

- [ ] **Step 4: Commit templates**

```bash
git add templates/osint/
git commit -m "feat: add OSINT fragment templates (social, opendata)"
```

---

## Task 9: Register blueprints and models in app.py

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add osint_graph model import inside `seed_db()`**

In `app.py`, find the line `db.create_all()` inside `seed_db()` and add the model import **before** it:

```python
def seed_db():
    with nexo.app_context():
        # Import OSINT graph models so SQLAlchemy registers them before create_all()
        from models.osint_graph import Node as OsintNode, OsintEdge  # noqa: F401
        db.create_all()
        # ... rest of seed_db unchanged
```

- [ ] **Step 2: Add discover_plugins call at the end of `seed_db()`**

Still inside `with nexo.app_context():`, at the very end of `seed_db()` (after all the `db.session.commit()` calls):

```python
        from modules.osint.plugins.registry import discover_plugins
        discover_plugins()
```

- [ ] **Step 3: Register the three OSINT blueprints on `nexo`**

Add at the bottom of `app.py`, after all existing route definitions (before or after `if __name__ == "__main__":` if it exists):

```python
# ── Módulo OSINT integrado ────────────────────────────────────────────────────
from modules.osint.social    import social_osint_bp
from modules.osint.opendata  import opendata_osint_bp
from modules.osint.analytics import analytics_osint_bp

nexo.register_blueprint(social_osint_bp,    url_prefix="/osint/social")
nexo.register_blueprint(opendata_osint_bp,  url_prefix="/osint/opendata")
nexo.register_blueprint(analytics_osint_bp, url_prefix="/osint/analytics")
```

- [ ] **Step 4: Verify app starts without errors**

```bash
python app.py
```

Expected output (no errors):
```
[osint-plugins] Registrado: ip_geolocation
 * Running on http://127.0.0.1:5000
```

If you see `ImportError` or `ModuleNotFoundError`, check that the import path in the error matches the actual file location.

- [ ] **Step 5: Verify OSINT routes are registered**

With the app running, open: `http://127.0.0.1:5000/osint/social/lookup?q=torvalds&source=github`

Expected: redirects to login page (if not logged in), or returns an HTML fragment with GitHub data.

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat: register OSINT blueprints and wire up osint_graph models in app.py"
```

---

## Task 10: Update console.html — Cytoscape CDN + panel-inteligencia sub-tabs

**Files:**
- Modify: `templates/console.html`

- [ ] **Step 1: Add Cytoscape.js CDN in `<head>`**

In `console.html`, find line 21:
```html
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
```

Add Cytoscape **after** that line:
```html
  <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
```

- [ ] **Step 2: Replace `panel-inteligencia` content (lines 685–742)**

Find and replace the entire `<section class="panel-section" id="panel-inteligencia">` block (from `<!-- PANEL CORRELACIONES E OSINT -->` through the closing `</section>` at line 742) with the following:

```html
        <!-- PANEL CORRELACIONES E OSINT (INTELIGENCIA TÁCTICA) -->
        <section class="panel-section" id="panel-inteligencia">
          <div class="section-header-tactical">
            <h2>Correlaciones de Redes Extorsivas y OSINT</h2>
            <p>Búsqueda activa en redes sociales, datos abiertos y grafo de relaciones.</p>
          </div>

          <!-- Sub-tabs -->
          <div class="osint-tabs" style="display:flex;gap:.5rem;margin-bottom:1rem;border-bottom:1px solid #1e2535;padding-bottom:.5rem">
            <button class="osint-tab-btn btn btn-secondary-tactical active" data-tab="social" onclick="osintSwitchTab('social')">Redes Sociales</button>
            <button class="osint-tab-btn btn btn-secondary-tactical" data-tab="opendata" onclick="osintSwitchTab('opendata')">Datos Abiertos</button>
            <button class="osint-tab-btn btn btn-secondary-tactical" data-tab="graph" onclick="osintSwitchTab('graph')">Grafo de Relaciones</button>
          </div>

          <!-- Tab: Redes Sociales -->
          <div class="osint-tab-pane" id="osint-tab-social">
            <div class="dashboard-card double-bezel">
              <div class="inner-core">
                <h3>Búsqueda en Redes Sociales</h3>
                <p class="helper-text-mono">Extracción de identidades digitales mediante API, scraping y dorking.</p>
                <div style="display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin-bottom:.75rem">
                  <input type="text" id="osint-social-q" class="search-input-tactical" placeholder="usuario o alias..." style="flex:1;min-width:150px">
                  <select id="osint-social-source" class="select-tactical">
                    <option value="github">GitHub</option>
                    <option value="reddit">Reddit</option>
                    <option value="both">GitHub + Reddit</option>
                    <option value="facebook">Facebook</option>
                    <option value="x">X (Twitter)</option>
                    <option value="tiktok">TikTok</option>
                    <option value="deep_all">Profunda (FB+X+TikTok)</option>
                    <option value="all">Todas las fuentes</option>
                  </select>
                  <button class="btn btn-primary-tactical" onclick="osintFetchSocial()">EJECUTAR</button>
                </div>
                <div id="osint-social-spinner" style="display:none;color:#4bc8a8;font-size:.8rem;margin-bottom:.5rem">⟳ Ejecutando búsqueda...</div>
                <div id="osint-social-results" style="max-height:500px;overflow-y:auto"></div>
              </div>
            </div>
          </div>

          <!-- Tab: Datos Abiertos -->
          <div class="osint-tab-pane" id="osint-tab-opendata" style="display:none">
            <div class="dashboard-card double-bezel">
              <div class="inner-core">
                <h3>Datos Abiertos: IP y Dominios</h3>
                <p class="helper-text-mono">Geolocalización de IPs, registros RDAP y certificados de transparencia.</p>
                <div style="display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin-bottom:.75rem">
                  <input type="text" id="osint-od-q" class="search-input-tactical" placeholder="IP o dominio..." style="flex:1;min-width:150px">
                  <select id="osint-od-source" class="select-tactical">
                    <option value="ip">Geoloc. IP</option>
                    <option value="domain">Dominio RDAP + Certs</option>
                    <option value="both">Ambos</option>
                  </select>
                  <button class="btn btn-primary-tactical" onclick="osintFetchOpendata()">EJECUTAR</button>
                </div>
                <div id="osint-od-spinner" style="display:none;color:#4bc8a8;font-size:.8rem;margin-bottom:.5rem">⟳ Consultando fuentes abiertas...</div>
                <div id="osint-od-results" style="max-height:500px;overflow-y:auto"></div>
              </div>
            </div>
          </div>

          <!-- Tab: Grafo de Relaciones -->
          <div class="osint-tab-pane" id="osint-tab-graph" style="display:none">
            <div class="dashboard-card double-bezel">
              <div class="inner-core">
                <h3>Grafo de Relaciones OSINT</h3>
                <p class="helper-text-mono">Visualización del grafo de entidades acumulado en osint.db. Filtra por objetivo o carga todo.</p>
                <div style="display:flex;gap:.5rem;align-items:center;margin-bottom:.75rem">
                  <input type="text" id="osint-graph-q" class="search-input-tactical" placeholder="objetivo (vacío = todo el grafo)" style="flex:1">
                  <button class="btn btn-primary-tactical" onclick="osintLoadGraph()">CARGAR GRAFO</button>
                  <button class="btn btn-secondary-tactical" onclick="osintResetGraph()">LIMPIAR</button>
                </div>
                <div id="osint-graph-spinner" style="display:none;color:#4bc8a8;font-size:.8rem;margin-bottom:.5rem">⟳ Cargando grafo...</div>
                <div id="osint-graph-info" style="font-size:.75rem;color:#6b8aaa;margin-bottom:.5rem"></div>
                <div id="osint-graph-canvas" style="width:100%;height:420px;background:#07080c;border:1px solid #1e2535;border-radius:4px"></div>
              </div>
            </div>
          </div>
        </section>
```

- [ ] **Step 3: Add OSINT JavaScript before the closing `</body>`**

In `console.html`, find the line:
```html
  <script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
```

Add a new `<script>` block **after** that line (before `</body>`):

```html
<script>
// ── OSINT Panel ────────────────────────────────────────────────────────────
let _osintCy = null;

function osintSwitchTab(tab) {
  document.querySelectorAll('.osint-tab-pane').forEach(p => p.style.display = 'none');
  document.querySelectorAll('.osint-tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('osint-tab-' + tab).style.display = '';
  document.querySelector('[data-tab="' + tab + '"]').classList.add('active');
}

function osintFetchSocial() {
  const q      = document.getElementById('osint-social-q').value.trim();
  const source = document.getElementById('osint-social-source').value;
  if (!q) { alert('Ingresa un objetivo.'); return; }

  const spinner = document.getElementById('osint-social-spinner');
  const results = document.getElementById('osint-social-results');
  spinner.style.display = '';
  results.innerHTML = '';

  fetch('/osint/social/lookup?q=' + encodeURIComponent(q) + '&source=' + source)
    .then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    })
    .then(html => { results.innerHTML = html; })
    .catch(err  => { results.innerHTML = '<p style="color:#f87171;font-size:.8rem">⚠ Error: ' + err.message + '</p>'; })
    .finally(() => { spinner.style.display = 'none'; });
}

function osintFetchOpendata() {
  const q      = document.getElementById('osint-od-q').value.trim();
  const source = document.getElementById('osint-od-source').value;
  if (!q) { alert('Ingresa una IP o dominio.'); return; }

  const spinner = document.getElementById('osint-od-spinner');
  const results = document.getElementById('osint-od-results');
  spinner.style.display = '';
  results.innerHTML = '';

  fetch('/osint/opendata/lookup?q=' + encodeURIComponent(q) + '&source=' + source)
    .then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    })
    .then(html => { results.innerHTML = html; })
    .catch(err  => { results.innerHTML = '<p style="color:#f87171;font-size:.8rem">⚠ Error: ' + err.message + '</p>'; })
    .finally(() => { spinner.style.display = 'none'; });
}

function osintLoadGraph() {
  const q       = document.getElementById('osint-graph-q').value.trim();
  const spinner = document.getElementById('osint-graph-spinner');
  const info    = document.getElementById('osint-graph-info');
  spinner.style.display = '';
  info.textContent = '';

  if (_osintCy) { _osintCy.destroy(); _osintCy = null; }

  fetch('/osint/analytics/graph?q=' + encodeURIComponent(q))
    .then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(data => {
      const GROUP_COLORS = {
        target:'#c8a84b', contact:'#4bc8a8', network:'#4b8ac8',
        org:'#c84b8a', repo:'#8ac84b', platform:'#6b6860',
        x_platform:'#1DA1F2', x_profile:'#1565a8',
        tiktok_platform:'#ff0050', tiktok_profile:'#a0002f',
        social_profile:'#a855f7',
      };

      const elements = [];
      (data.nodes || []).forEach(n => {
        elements.push({ data: {
          id: n.id, label: n.label || n.id,
          color: GROUP_COLORS[n.group] || '#6b6860',
        }});
      });
      (data.links || []).forEach(l => {
        elements.push({ data: {
          source: l.source, target: l.target, label: l.label || '',
        }});
      });

      info.textContent = (data.nodes||[]).length + ' nodos · ' + (data.links||[]).length + ' aristas' + (q ? ' (subgrafo de "' + q + '")' : ' (grafo completo)');

      if (elements.length === 0) {
        info.textContent = 'Sin nodos. Ejecuta primero una búsqueda en Redes Sociales o Datos Abiertos.';
        return;
      }

      _osintCy = cytoscape({
        container: document.getElementById('osint-graph-canvas'),
        elements: elements,
        style: [
          { selector: 'node', style: {
            'background-color': 'data(color)',
            'label': 'data(label)',
            'color': '#d0d8e8',
            'font-size': '9px',
            'text-valign': 'bottom',
            'text-margin-y': '3px',
            'width': '24px', 'height': '24px',
          }},
          { selector: 'edge', style: {
            'line-color': '#2a3a50',
            'target-arrow-color': '#2a3a50',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '7px',
            'color': '#4a5a6a',
            'width': 1,
          }},
        ],
        layout: { name: 'cose', animate: false, padding: 20 },
      });
    })
    .catch(err => { info.textContent = '⚠ Error al cargar grafo: ' + err.message; })
    .finally(() => { spinner.style.display = 'none'; });
}

function osintResetGraph() {
  if (_osintCy) { _osintCy.destroy(); _osintCy = null; }
  document.getElementById('osint-graph-info').textContent = '';
  document.getElementById('osint-graph-q').value = '';
}

// Enter key support for OSINT inputs
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('osint-social-q')
    .addEventListener('keydown', e => { if (e.key === 'Enter') osintFetchSocial(); });
  document.getElementById('osint-od-q')
    .addEventListener('keydown', e => { if (e.key === 'Enter') osintFetchOpendata(); });
  document.getElementById('osint-graph-q')
    .addEventListener('keydown', e => { if (e.key === 'Enter') osintLoadGraph(); });
});
</script>
```

- [ ] **Step 4: Verify panel works end-to-end**

1. Start the app: `python app.py`
2. Log in as `admin` / `Admin147*`
3. Navigate to the console (`/`)
4. Click "Correlaciones e OSINT" in the sidebar
5. Verify three sub-tabs appear: "Redes Sociales", "Datos Abiertos", "Grafo de Relaciones"
6. In "Redes Sociales", search `torvalds` with source `GitHub` → verify HTML fragment appears with GitHub profile
7. In "Datos Abiertos", search `8.8.8.8` with source `Geoloc. IP` → verify IP geolocation data appears
8. In "Grafo de Relaciones", press "CARGAR GRAFO" with empty input → verify Cytoscape canvas shows (may be empty if no prior searches)
9. After a social search, switch to "Grafo de Relaciones" and search the same username → verify nodes appear

- [ ] **Step 5: Commit**

```bash
git add templates/console.html
git commit -m "feat: add OSINT sub-tabs to panel-inteligencia with fetch + Cytoscape graph"
```

---

## Self-Review Checklist

- [x] **Spec coverage:**
  - ✅ Single Flask app (no iframe) — blueprints registered on `nexo`
  - ✅ Sub-tabs inside panel with AJAX/fetch — Task 10
  - ✅ Node/Edge in osint.db bind — Task 2 (`__bind_key__ = "osint"`)
  - ✅ `modules/osint/auth.py` helper — Task 1
  - ✅ Social blueprint (GitHub, Reddit, Facebook, X, TikTok) — Task 5
  - ✅ Opendata blueprint (IP, RDAP, crt.sh) — Task 6
  - ✅ Analytics blueprint (graph JSON only) — Task 7
  - ✅ Fragment templates — Task 8
  - ✅ `discover_plugins()` called in `seed_db()` — Task 9
  - ✅ Cytoscape.js CDN — Task 10
  - ✅ requirements.txt updated — Task 1

- [x] **Type consistency:**
  - `social_osint_bp` defined in Task 5 Step 2, imported in Task 9 Step 3 ✅
  - `opendata_osint_bp` defined in Task 6 Step 1, imported in Task 9 Step 3 ✅
  - `analytics_osint_bp` defined in Task 7 Step 2, imported in Task 9 Step 3 ✅
  - `OsintEdge` defined in Task 2, used in Task 7 analytics routes ✅
  - `get_or_create_node`, `create_edge` defined in Task 2, used in Tasks 3 services ✅
  - Template `osint/social_fragment.html` returned in Task 5 routes, created in Task 8 ✅
  - Template `osint/opendata_fragment.html` returned in Task 6 routes, created in Task 8 ✅

- [x] **No placeholders:** All code is complete. No TBD, TODO, or stub implementations.
