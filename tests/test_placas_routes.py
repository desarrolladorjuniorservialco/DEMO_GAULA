# tests/test_placas_routes.py
import io
from unittest.mock import patch


# ── Helpers ──────────────────────────────────────────────────────────────────

def _auth_client(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analista"
        sess["role"] = "analista"
        sess["name"] = "Analista Test"
    return client


def _minimal_png() -> bytes:
    """PNG de 1×1 pixel válido (base64 decodificado)."""
    import base64
    return base64.b64decode(
        b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+"
        b"M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )


# ── Tests del engine (sin deps ML) ───────────────────────────────────────────

def test_extraer_placas_carro_valido():
    from modules.placas.engine import extraer_placas_de_texto
    resultados = extraer_placas_de_texto("ABC123")
    assert any(p == "ABC123" for p, _, _ in resultados)


def test_extraer_placas_moto_valido():
    from modules.placas.engine import extraer_placas_de_texto
    resultados = extraer_placas_de_texto("XYZ12D")
    assert any(p == "XYZ12D" for p, _, _ in resultados)


def test_extraer_placas_texto_invalido():
    from modules.placas.engine import extraer_placas_de_texto
    assert extraer_placas_de_texto("HOLA MUNDO") == []


def test_extraer_placas_correccion_ocr():
    """'0' en posición de letra debe corregirse a 'O'."""
    from modules.placas.engine import extraer_placas_de_texto
    resultados = extraer_placas_de_texto("0BC123")
    placas = [p for p, _, _ in resultados]
    assert "OBC123" in placas


def test_reconocer_placa_sin_deps():
    """Sin EasyOCR instalado, devuelve {ok:False, missing_deps:True}."""
    from modules.placas import engine
    with patch.object(engine, "_check_deps", return_value=False):
        resultado = engine.reconocer_placa(b"cualquier_bytes")
    assert resultado["ok"] is False
    assert resultado["missing_deps"] is True
    assert "pip install" in resultado["install_cmd"]


# ── Tests de rutas ────────────────────────────────────────────────────────────

def test_placas_index_redirige_sin_login(app):
    client = app.test_client()
    resp = client.get("/placas/")
    assert resp.status_code == 302


def test_placas_index_renderiza_con_login(app):
    client = _auth_client(app)
    resp = client.get("/placas/")
    assert resp.status_code == 200
    assert b"placa" in resp.data.lower()


def test_analizar_sin_archivo_retorna_400(app):
    client = _auth_client(app)
    resp = client.post("/placas/analizar")
    assert resp.status_code == 400


def test_analizar_mime_no_imagen_retorna_400(app):
    client = _auth_client(app)
    data = {"imagen": (io.BytesIO(b"contenido"), "archivo.txt", "text/plain")}
    resp = client.post("/placas/analizar", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_analizar_sin_deps_retorna_json_missing_deps(app):
    from modules.placas import engine
    client = _auth_client(app)
    with patch.object(engine, "_check_deps", return_value=False):
        data = {"imagen": (io.BytesIO(_minimal_png()), "test.png", "image/png")}
        resp = client.post("/placas/analizar", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is False
    assert body["missing_deps"] is True


def test_analizar_redirige_sin_login(app):
    client = app.test_client()
    data = {"imagen": (io.BytesIO(_minimal_png()), "test.png", "image/png")}
    resp = client.post("/placas/analizar", data=data, content_type="multipart/form-data")
    assert resp.status_code == 302


def test_analizar_ok_devuelve_json_con_placa(app):
    """Happy path: engine retorna placa → endpoint devuelve JSON con placa."""
    from modules.placas import engine
    fake_resultado = {
        "ok": True,
        "placa": "ABC123",
        "tipo": "CARRO",
        "confianza": 0.94,
        "paneles": ["b64a", "b64b", "b64c", "b64d"],
        "alternativas": [],
    }
    client = _auth_client(app)
    with patch.object(engine, "reconocer_placa", return_value=fake_resultado):
        data = {"imagen": (io.BytesIO(_minimal_png()), "test.png", "image/png")}
        resp = client.post("/placas/analizar", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["placa"] == "ABC123"
    assert len(body["paneles"]) == 4
