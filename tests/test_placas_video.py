# tests/test_placas_video.py
"""Tests del pipeline de conteo de placas en video (sin dependencias ML pesadas)."""


# ── PlateVoter ────────────────────────────────────────────────────────────────

def test_voter_mayoria_simple():
    from modules.placas.video.plate_votes import PlateVoter
    v = PlateVoter()
    v.agregar_lectura(1, "ABC123", 0.9)
    v.agregar_lectura(1, "ABC123", 0.8)
    v.agregar_lectura(1, "A8C123", 0.7)  # misread: '8' en posición de letra → B
    placa, tipo, conf = v.resolver(1)
    assert placa == "ABC123"
    assert tipo == "CARRO"
    assert conf == 1.0  # todas las lecturas convergen a la misma placa

def test_voter_pondera_por_confianza():
    from modules.placas.video.plate_votes import PlateVoter
    v = PlateVoter()
    v.agregar_lectura(1, "XYZ789", 0.95)
    v.agregar_lectura(1, "XYZ789", 0.90)
    v.agregar_lectura(1, "XYZ780", 0.10)
    placa, _, conf = v.resolver(1)
    assert placa == "XYZ789"
    assert 0.0 < conf < 1.0

def test_voter_ignora_texto_invalido():
    from modules.placas.video.plate_votes import PlateVoter
    v = PlateVoter()
    assert v.agregar_lectura(1, "HOLA", 0.9) is False
    assert v.agregar_lectura(1, "", 0.9) is False
    assert v.agregar_lectura(1, None, 0.9) is False
    assert v.resolver(1) == (None, None, 0.0)

def test_voter_track_sin_lecturas():
    from modules.placas.video.plate_votes import PlateVoter
    assert PlateVoter().resolver(99) == (None, None, 0.0)

def test_voter_detecta_tipo_moto():
    from modules.placas.video.plate_votes import PlateVoter
    v = PlateVoter()
    v.agregar_lectura(2, "XYZ12D", 0.8)
    placa, tipo, _ = v.resolver(2)
    assert placa == "XYZ12D"
    assert tipo == "MOTO"
