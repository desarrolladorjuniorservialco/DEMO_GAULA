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
