"""
graph/builder.py — Constructor del grafo de entidades OSINT.

Movido desde modules/osint/analytics/graph_builder.py.
El modulo analytics mantiene un shim de re-exportacion para compatibilidad.

Entity types  : person, alias, email, organization, domain, ip,
                repository, social_profile, location, platform, url
Edge schema   : source, target, relation_type, confidence, weight, source_evidence
Return format : { nodes, links, findings, stats }
"""
from __future__ import annotations

from datetime import datetime

TYPE_PERSON         = "person"
TYPE_ALIAS          = "alias"
TYPE_EMAIL          = "email"
TYPE_ORGANIZATION   = "organization"
TYPE_DOMAIN         = "domain"
TYPE_IP             = "ip"
TYPE_REPOSITORY     = "repository"
TYPE_SOCIAL_PROFILE = "social_profile"
TYPE_LOCATION       = "location"
TYPE_PLATFORM       = "platform"
TYPE_URL            = "url"

ENTITY_STYLE: dict[str, dict] = {
    TYPE_PERSON:         {"color": "#e74c3c", "shape": "ellipse",         "size": 42},
    TYPE_ALIAS:          {"color": "#e67e22", "shape": "tag",             "size": 32},
    TYPE_EMAIL:          {"color": "#4bc8a8", "shape": "rectangle",       "size": 30},
    TYPE_ORGANIZATION:   {"color": "#9b59b6", "shape": "hexagon",         "size": 34},
    TYPE_DOMAIN:         {"color": "#3498db", "shape": "barrel",          "size": 30},
    TYPE_IP:             {"color": "#1abc9c", "shape": "diamond",         "size": 32},
    TYPE_REPOSITORY:     {"color": "#27ae60", "shape": "round-rectangle", "size": 22},
    TYPE_SOCIAL_PROFILE: {"color": "#1DA1F2", "shape": "star",            "size": 30},
    TYPE_LOCATION:       {"color": "#f1c40f", "shape": "triangle",        "size": 28},
    TYPE_PLATFORM:       {"color": "#6b8aaa", "shape": "ellipse",         "size": 26},
    TYPE_URL:            {"color": "#8ab4cc", "shape": "cut-rectangle",   "size": 22},
}

ENTITY_RISK: dict[str, str] = {
    TYPE_PERSON:         "Medio",
    TYPE_ALIAS:          "Medio",
    TYPE_EMAIL:          "Alto",
    TYPE_ORGANIZATION:   "Bajo",
    TYPE_DOMAIN:         "Medio",
    TYPE_IP:             "Alto",
    TYPE_REPOSITORY:     "Bajo",
    TYPE_SOCIAL_PROFILE: "Medio",
    TYPE_LOCATION:       "Bajo",
    TYPE_PLATFORM:       "Info",
    TYPE_URL:            "Bajo",
}

CONFIDENCE: dict[str, float] = {
    "github_api":      0.95,
    "rdap":            0.90,
    "reddit_api":      0.88,
    "ip_api":          0.85,
    "inference":       0.70,
    "dork_x":          0.60,
    "dork_tiktok":     0.55,
    "facebook_scrape": 0.50,
    "mock":            0.20,
}

_RISK_WEIGHT = {"Critico": 4, "Alto": 3, "Medio": 2, "Bajo": 1, "Info": 0}


def _node(
    node_id: str, label: str, ntype: str, conf: float,
    src: str, risk: str | None = None, meta: dict | None = None, is_target: bool = False,
) -> dict:
    style = ENTITY_STYLE.get(ntype, {"color": "#6b8aaa", "shape": "ellipse", "size": 26})
    return {
        "id":             node_id,
        "label":          label,
        "type":           ntype,
        "color":          style["color"],
        "shape":          style["shape"],
        "base_size":      round(style["size"] * (1.7 if is_target else 1.0)),
        "confidence":     round(conf, 2),
        "risk_level":     risk or ENTITY_RISK.get(ntype, "Bajo"),
        "source_evidence":src,
        "discovered_at":  datetime.utcnow().strftime("%Y-%m-%d"),
        "metadata":       meta or {},
        "is_target":      is_target,
    }


def _edge(src: str, tgt: str, relation: str, conf: float, source: str, weight: float = 1.0) -> dict:
    return {
        "source":          src,
        "target":          tgt,
        "relation_type":   relation,
        "label":           relation.replace("_", " "),
        "confidence":      round(conf, 2),
        "weight":          round(weight, 2),
        "source_evidence": source,
    }


def build_graph(
    username: str,
    github_profile: dict | None = None,
    github_repos:   list | None = None,
    reddit_profile: dict | None = None,
    facebook_data:  dict | None = None,
    ip_data:        dict | None = None,
    rdap_data:      dict | None = None,
) -> dict:
    """Build enriched OSINT entity graph. Returns { nodes, links, findings, stats }."""
    nodes: dict[str, dict] = {}
    edges: list[dict]      = []

    def add_node(nid, label, ntype, conf, src, risk=None, meta=None, is_target=False):
        if nid not in nodes:
            nodes[nid] = _node(nid, label, ntype, conf, src, risk, meta, is_target)

    def add_edge(s, t, rel, conf, src, w=1.0):
        if s in nodes and t in nodes:
            edges.append(_edge(s, t, rel, conf, src, w))

    add_node(username, username, TYPE_PERSON, 1.0, "query", risk="Bajo", is_target=True)

    if github_profile:
        gh = CONFIDENCE["github_api"]
        add_node("platform:GitHub", "GitHub", TYPE_PLATFORM, 1.0, "github_api")
        add_edge(username, "platform:GitHub", "activo_en", gh, "github_api", 0.6)
        if github_profile.get("email"):
            em = github_profile["email"]
            add_node(em, em, TYPE_EMAIL, gh, "github_api", risk="Alto")
            add_edge(username, em, "usa_correo", gh, "github_api", 0.95)
        if github_profile.get("company"):
            org = github_profile["company"].strip().lstrip("@").strip()
            if org:
                add_node(f"org:{org}", org, TYPE_ORGANIZATION, gh * 0.9, "github_api")
                add_edge(username, f"org:{org}", "trabaja_en", gh * 0.9, "github_api", 0.85)
        if github_profile.get("blog"):
            blog = github_profile["blog"].strip()
            if blog:
                add_node(blog, blog, TYPE_DOMAIN, gh * 0.85, "github_api")
                add_edge(username, blog, "dominio_personal", gh * 0.85, "github_api", 0.75)
        if github_profile.get("twitter_username"):
            tw = github_profile["twitter_username"]
            add_node(f"x:{tw}", f"@{tw}", TYPE_SOCIAL_PROFILE, gh * 0.9, "github_api")
            add_edge(username, f"x:{tw}", "alias_en_x", gh * 0.9, "github_api", 0.90)
        if github_profile.get("location"):
            loc = github_profile["location"].strip()
            if loc:
                add_node(f"loc:{loc}", loc, TYPE_LOCATION, gh * 0.65, "github_api", risk="Bajo")
                add_edge(username, f"loc:{loc}", "ubicado_en", gh * 0.65, "github_api", 0.50)
        langs_seen: set[str] = set()
        for repo in (github_repos or [])[:10]:
            rid  = f"repo:{repo['name']}"
            lang = (repo.get("language") or "").strip()
            if lang:
                langs_seen.add(lang)
            add_node(rid, repo["name"], TYPE_REPOSITORY, gh * 0.8, "github_api", risk="Bajo",
                     meta={"language": lang or "—", "stars": repo.get("stargazers_count", 0),
                           "url": repo.get("html_url", ""), "updated_at": (repo.get("updated_at") or "")[:10],
                           "is_secondary": True})
            add_edge(username, rid, "propietario_de", gh * 0.8, "github_api", 0.35)
        if langs_seen:
            nodes[username]["metadata"]["languages"] = sorted(langs_seen)

    if reddit_profile:
        rd    = CONFIDENCE["reddit_api"]
        rname = reddit_profile.get("name", username)
        add_node("platform:Reddit", "Reddit", TYPE_PLATFORM, 1.0, "reddit_api")
        add_edge(username, "platform:Reddit", "activo_en", rd, "reddit_api", 0.6)
        add_node(f"reddit:{rname}", f"u/{rname}", TYPE_SOCIAL_PROFILE, rd, "reddit_api",
                 meta={"karma_total": int(reddit_profile.get("total_karma") or 0),
                       "karma_link":  int(reddit_profile.get("link_karma")  or 0),
                       "url":         f"https://reddit.com/u/{rname}"})
        add_edge(username, f"reddit:{rname}", "perfil_en_reddit", rd, "reddit_api", 0.90)

    if facebook_data:
        fb_src = "mock" if facebook_data.get("is_mock") else "facebook_scrape"
        fb     = CONFIDENCE[fb_src]
        add_node("platform:Facebook", "Facebook", TYPE_PLATFORM, 1.0, fb_src)
        add_edge(username, "platform:Facebook", "activo_en", fb, fb_src, 0.6)
        for hint in facebook_data.get("email_hints", []):
            add_node(hint, hint, TYPE_EMAIL, fb, fb_src, risk="Alto")
            add_edge(username, hint, "usa_correo", fb, fb_src, 0.80)
        og        = facebook_data.get("og", {})
        real_name = (og.get("og:title") or "").strip()
        if real_name and real_name.lower() != username.lower():
            clean = real_name[:80]
            add_node(f"alias:{clean}", clean, TYPE_ALIAS, fb, fb_src)
            add_edge(username, f"alias:{clean}", "nombre_real_en_fb", fb, fb_src, 0.70)
        for conn in (facebook_data.get("mutual_connections") or [])[:5]:
            add_node(f"person:{conn}", conn, TYPE_PERSON, fb * 0.6, fb_src, risk="Bajo")
            add_edge(username, f"person:{conn}", "conexion_mutua", fb * 0.6, fb_src, 0.45)

    if ip_data:
        ip_c   = CONFIDENCE["ip_api"]
        ip_val = (ip_data.get("query") or "").strip()
        if ip_val:
            add_node(ip_val, ip_val, TYPE_IP, ip_c, "ip_api", risk="Alto",
                     meta={"isp": ip_data.get("isp", ""), "org": ip_data.get("org", "")})
            add_edge(username, ip_val, "resuelve_a", ip_c, "ip_api", 0.90)
            isp = (ip_data.get("isp") or "").strip()
            if isp:
                add_node(f"org:{isp}", isp, TYPE_ORGANIZATION, ip_c * 0.9, "ip_api", risk="Bajo")
                add_edge(ip_val, f"org:{isp}", "provisto_por", ip_c * 0.9, "ip_api", 0.70)
            country = ip_data.get("country", "")
            city    = ip_data.get("city", "")
            if country:
                geo_id    = f"loc:{city},{country}" if city else f"loc:{country}"
                geo_label = f"{city}, {country}"    if city else country
                add_node(geo_id, geo_label, TYPE_LOCATION, ip_c * 0.8, "ip_api", risk="Bajo",
                         meta={"lat": ip_data.get("lat"), "lon": ip_data.get("lon")})
                add_edge(ip_val, geo_id, "ubicado_en", ip_c * 0.8, "ip_api", 0.60)

    if rdap_data and rdap_data.get("ldhName"):
        rdap_c = CONFIDENCE["rdap"]
        domain = rdap_data["ldhName"]
        add_node(domain, domain, TYPE_DOMAIN, rdap_c, "rdap",
                 meta={"status": rdap_data.get("status") or []})
        add_edge(username, domain, "dominio_registrado", rdap_c, "rdap", 0.90)
        for ns in (rdap_data.get("nameservers") or []):
            add_node(ns, ns, TYPE_DOMAIN, rdap_c * 0.85, "rdap", risk="Bajo")
            add_edge(domain, ns, "nameserver", rdap_c * 0.85, "rdap", 0.55)
        for ent in (rdap_data.get("entities") or []):
            if ent.get("name"):
                oid  = f"org:{ent['name']}"
                role = (ent.get("roles") or ["registrado_por"])[0]
                add_node(oid, ent["name"], TYPE_ORGANIZATION, rdap_c * 0.85, "rdap")
                add_edge(domain, oid, role, rdap_c * 0.85, "rdap", 0.70)

    findings = _generate_findings(nodes, edges)
    return {
        "nodes":    list(nodes.values()),
        "links":    edges,
        "findings": findings,
        "stats":    {"total_nodes": len(nodes), "total_edges": len(edges),
                     "entity_counts": _count_by_type(nodes)},
    }


def _count_by_type(nodes: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for n in nodes.values():
        counts[n["type"]] = counts.get(n["type"], 0) + 1
    return counts


def _generate_findings(nodes: dict, edges: list, query: str = "") -> list[dict]:
    findings: list[dict] = []
    by_type: dict[str, list] = {}
    for n in nodes.values():
        by_type.setdefault(n["type"], []).append(n)

    emails    = by_type.get(TYPE_EMAIL,          [])
    orgs      = by_type.get(TYPE_ORGANIZATION,   [])
    ips       = by_type.get(TYPE_IP,             [])
    domains   = by_type.get(TYPE_DOMAIN,         [])
    socials   = by_type.get(TYPE_SOCIAL_PROFILE, [])
    repos     = by_type.get(TYPE_REPOSITORY,     [])
    locations = by_type.get(TYPE_LOCATION,       [])
    aliases   = by_type.get(TYPE_ALIAS,          [])

    if emails:
        label_list = ", ".join(e["label"] for e in emails[:3])
        findings.append({"nivel": "Alto",
                         "titulo": f"{'Multiples correos' if len(emails) > 1 else 'Correo'} identificado{'s' if len(emails) > 1 else ''}",
                         "descripcion": f"{len(emails)} direccion(es) detectada(s): {label_list}",
                         "tipo": "identidad", "icon": "E"})
    if aliases:
        findings.append({"nivel": "Medio", "titulo": "Identidad alternativa detectada",
                         "descripcion": f"Alias o nombre real: {', '.join(a['label'] for a in aliases[:3])}",
                         "tipo": "identidad", "icon": "A"})
    if orgs:
        findings.append({"nivel": "Medio", "titulo": "Afiliacion organizacional",
                         "descripcion": f"Vinculado a: {', '.join(o['label'] for o in orgs[:3])}",
                         "tipo": "afiliacion", "icon": "O"})
    if ips:
        findings.append({"nivel": "Alto", "titulo": "Infraestructura de red expuesta",
                         "descripcion": f"{'IP identificada' if len(ips) == 1 else str(len(ips)) + ' IPs detectadas'}: {', '.join(i['label'] for i in ips)}",
                         "tipo": "infraestructura", "icon": "I"})

    personal_domains = [d for d in domains
                        if any(e["target"] == d["id"] and e["relation_type"] in ("dominio_personal", "dominio_registrado")
                               for e in edges)]
    if personal_domains:
        findings.append({"nivel": "Medio", "titulo": "Dominio registrado",
                         "descripcion": f"Dominio propio detectado: {personal_domains[0]['label']}",
                         "tipo": "infraestructura", "icon": "D"})
    if len(socials) >= 2:
        findings.append({"nivel": "Medio", "titulo": "Presencia digital multiple",
                         "descripcion": f"Objetivo activo en {len(socials)} plataforma(s) social(es)",
                         "tipo": "identidad", "icon": "S"})
    if repos:
        langs = sorted({r["metadata"].get("language", "") for r in repos
                        if r["metadata"].get("language", "") not in ("", "-")})
        findings.append({"nivel": "Bajo",
                         "titulo": f"Actividad tecnica: {len(repos)} repositorio{'s' if len(repos) > 1 else ''}",
                         "descripcion": f"Lenguajes: {', '.join(langs[:5]) or '-'}",
                         "tipo": "tecnico", "icon": "R"})
    if locations:
        findings.append({"nivel": "Bajo", "titulo": "Ubicacion geografica detectada",
                         "descripcion": f"Zona identificada: {locations[0]['label']}",
                         "tipo": "geolocalizacion", "icon": "G"})
    if emails and orgs:
        findings.append({"nivel": "Alto", "titulo": "Correlacion: identidad laboral posible",
                         "descripcion": "Correo y organizacion detectados simultaneamente.",
                         "tipo": "correlacion", "icon": "C"})
    if ips and personal_domains:
        findings.append({"nivel": "Alto", "titulo": "Correlacion: infraestructura propia detectada",
                         "descripcion": "IP y dominio registrado encontrados.",
                         "tipo": "correlacion", "icon": "X"})

    score = sum(_RISK_WEIGHT.get(n["risk_level"], 0) for n in nodes.values())
    overall = "Critico" if score >= 12 else "Alto" if score >= 7 else "Medio" if score >= 3 else "Bajo"
    findings.append({"nivel": overall, "titulo": f"Riesgo operativo: {overall}",
                     "descripcion": f"Score: {score} - {len(nodes)} entidades, {len(edges)} relaciones.",
                     "tipo": "resumen", "icon": "!"})
    return findings
