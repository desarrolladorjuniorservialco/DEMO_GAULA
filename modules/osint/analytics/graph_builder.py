import networkx as nx
from networkx.readwrite import json_graph


# Node type constants — used in graph.html filters
TYPE_PERSON = "person"
TYPE_EMAIL = "email"
TYPE_IP = "ip"
TYPE_DOMAIN = "domain"
TYPE_ORG = "organization"
TYPE_REPO = "repository"
TYPE_PLATFORM = "platform"

# Group constants — drive Cytoscape color scheme
GROUP_TARGET = "target"       # the searched identity
GROUP_CONTACT = "contact"     # people, emails discovered
GROUP_NETWORK = "network"     # IPs, domains, nameservers
GROUP_ORG = "org"             # organizations / companies
GROUP_REPO = "repo"           # repositories
GROUP_PLATFORM = "platform"   # social platforms (GitHub, Reddit, Facebook)


def _add_node(G: nx.DiGraph, node_id: str, label: str, node_type: str, group: str) -> None:
    """Add node only if not already present (prevents overwriting target node)."""
    if node_id not in G:
        G.add_node(node_id, label=label, type=node_type, group=group)


def _add_edge(G: nx.DiGraph, src: str, tgt: str, label: str, edge_type: str) -> None:
    """Add directed edge between two nodes."""
    G.add_edge(src, tgt, label=label, type=edge_type)


def build_graph(
    username: str,
    github_profile: dict | None = None,
    github_repos: list | None = None,
    reddit_profile: dict | None = None,
    facebook_data: dict | None = None,
    ip_data: dict | None = None,
    rdap_data: dict | None = None,
) -> dict:
    """
    Build a directed relationship graph from OSINT data collected across modules.

    Node schema: { id, label, type, group }
    Edge schema: { source, target, label, type }

    Returns networkx node_link_data dict suitable for direct JSON serialization.
    """
    G = nx.DiGraph()

    # Root: the investigated identity
    _add_node(G, username, username, TYPE_PERSON, GROUP_TARGET)

    # ── GitHub ──────────────────────────────────────────────────────────────
    if github_profile:
        gh_platform = "GitHub"
        _add_node(G, gh_platform, gh_platform, TYPE_PLATFORM, GROUP_PLATFORM)
        _add_edge(G, username, gh_platform, "activo_en", "active_on")

        if github_profile.get("email"):
            email = github_profile["email"]
            _add_node(G, email, email, TYPE_EMAIL, GROUP_CONTACT)
            _add_edge(G, username, email, "usa_correo", "uses_email")

        if github_profile.get("company"):
            org = github_profile["company"].strip("@ ")
            _add_node(G, org, org, TYPE_ORG, GROUP_ORG)
            _add_edge(G, username, org, "miembro_de", "member_of")

        if github_profile.get("blog"):
            blog = github_profile["blog"]
            _add_node(G, blog, blog, TYPE_DOMAIN, GROUP_NETWORK)
            _add_edge(G, username, blog, "mantiene", "maintains")

        if github_profile.get("twitter_username"):
            tw = "@" + github_profile["twitter_username"]
            _add_node(G, tw, tw, TYPE_PERSON, GROUP_CONTACT)
            _add_edge(G, username, tw, "alias_twitter", "alias")

        for repo in (github_repos or []):
            repo_id = f"repo:{repo['name']}"
            _add_node(G, repo_id, repo["name"], TYPE_REPO, GROUP_REPO)
            _add_edge(G, username, repo_id, "propietario", "owns")
            if repo.get("language"):
                lang_id = f"lang:{repo['language']}"
                _add_node(G, lang_id, repo["language"], TYPE_ORG, GROUP_ORG)
                _add_edge(G, repo_id, lang_id, "escrito_en", "written_in")

    # ── Reddit ───────────────────────────────────────────────────────────────
    if reddit_profile:
        rd_platform = "Reddit"
        _add_node(G, rd_platform, rd_platform, TYPE_PLATFORM, GROUP_PLATFORM)
        _add_edge(G, username, rd_platform, "activo_en", "active_on")

    # ── Facebook ─────────────────────────────────────────────────────────────
    if facebook_data:
        fb_platform = "Facebook"
        _add_node(G, fb_platform, fb_platform, TYPE_PLATFORM, GROUP_PLATFORM)
        _add_edge(G, username, fb_platform, "activo_en", "active_on")

        for hint in facebook_data.get("email_hints", []):
            _add_node(G, hint, hint, TYPE_EMAIL, GROUP_CONTACT)
            _add_edge(G, username, hint, "usa_correo", "uses_email")

        for post in facebook_data.get("recent_posts", []):
            for mention in post.get("mentions", []):
                _add_node(G, mention, mention, TYPE_PERSON, GROUP_CONTACT)
                _add_edge(G, username, mention, "interactúa", "interacts_with")

        for conn in facebook_data.get("mutual_connections", []):
            _add_node(G, conn, conn, TYPE_PERSON, GROUP_CONTACT)
            _add_edge(G, username, conn, "conexión_mutua", "mutual_connection")

        og = facebook_data.get("og", {})
        if og.get("og:title") and not facebook_data.get("is_mock"):
            real_name = og["og:title"]
            if real_name != username:
                _add_node(G, real_name, real_name, TYPE_PERSON, GROUP_CONTACT)
                _add_edge(G, username, real_name, "nombre_real", "alias")

    # ── IP Geolocation ────────────────────────────────────────────────────────
    if ip_data:
        ip = ip_data.get("query", "")
        if ip:
            _add_node(G, ip, ip, TYPE_IP, GROUP_NETWORK)
            _add_edge(G, username, ip, "resuelve_a", "resolved_to")

            isp = ip_data.get("isp", "")
            if isp:
                _add_node(G, isp, isp, TYPE_ORG, GROUP_NETWORK)
                _add_edge(G, ip, isp, "isp", "owned_by")

            org = ip_data.get("org", "")
            if org and org != isp:
                _add_node(G, org, org, TYPE_ORG, GROUP_NETWORK)
                _add_edge(G, ip, org, "organización", "owned_by")

            asn = ip_data.get("as", "")
            if asn:
                _add_node(G, asn, asn, TYPE_ORG, GROUP_NETWORK)
                _add_edge(G, ip, asn, "ASN", "owned_by")

            country = ip_data.get("country", "")
            city = ip_data.get("city", "")
            if country:
                geo_id = f"{city}, {country}" if city else country
                _add_node(G, geo_id, geo_id, TYPE_ORG, GROUP_NETWORK)
                _add_edge(G, ip, geo_id, "ubicado_en", "located_in")

    # ── RDAP Domain ───────────────────────────────────────────────────────────
    if rdap_data and rdap_data.get("ldhName"):
        domain = rdap_data["ldhName"]
        _add_node(G, domain, domain, TYPE_DOMAIN, GROUP_NETWORK)
        _add_edge(G, username, domain, "dominio", "owns_domain")

        for ns in rdap_data.get("nameservers", []):
            _add_node(G, ns, ns, TYPE_DOMAIN, GROUP_NETWORK)
            _add_edge(G, domain, ns, "nameserver", "uses_ns")

        for ent in rdap_data.get("entities", []):
            if ent.get("name"):
                _add_node(G, ent["name"], ent["name"], TYPE_ORG, GROUP_ORG)
                role = ent["roles"][0] if ent.get("roles") else "entidad"
                _add_edge(G, domain, ent["name"], role, "registered_by")

    return json_graph.node_link_data(G)
