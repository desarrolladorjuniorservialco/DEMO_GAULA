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


# ── ConteoVideo ───────────────────────────────────────────────────────────────

def test_conteo_confirma_vehiculo():
    from modules.placas.video.plate_votes import ConteoVideo
    c = ConteoVideo()
    ev = c.confirmar_vehiculo(track_id=1, ts_s=3.5)
    assert c.vehiculos == 1
    assert ev["tipo"] == "vehiculo"
    assert ev["ts_s"] == 3.5
    assert c.eventos == [ev]


def test_conteo_cierra_track_con_placa():
    from modules.placas.video.plate_votes import ConteoVideo
    c = ConteoVideo()
    c.confirmar_vehiculo(1, 1.0)
    ev = c.cerrar_track(1, "ABC123", "CARRO", 0.9, primer_ts=1.0, ultimo_ts=3.0)
    assert c.placas_leidas == 1
    assert ev["tipo"] == "placa"
    assert ev["placa"] == "ABC123"
    assert ev["tipo_vehiculo"] == "CARRO"


def test_conteo_sin_lectura():
    from modules.placas.video.plate_votes import ConteoVideo
    c = ConteoVideo()
    c.confirmar_vehiculo(1, 1.0)
    ev = c.cerrar_track(1, None, None, 0.0, primer_ts=1.0, ultimo_ts=2.0)
    assert c.sin_lectura == 1
    assert ev["tipo"] == "sin_lectura"


def test_conteo_fusiona_retrack_misma_placa():
    """Mismo vehículo re-trackeado (gap < 2 s): no cuenta doble."""
    from modules.placas.video.plate_votes import ConteoVideo
    c = ConteoVideo(gap_fusion_s=2.0)
    c.confirmar_vehiculo(1, 1.0)
    c.cerrar_track(1, "ABC123", "CARRO", 0.9, primer_ts=1.0, ultimo_ts=4.0)
    c.confirmar_vehiculo(2, 4.5)          # reaparece a los 0.5 s
    ev = c.cerrar_track(2, "ABC123", "CARRO", 0.8, primer_ts=4.5, ultimo_ts=6.0)
    assert ev is None                      # fusionado, sin evento nuevo
    assert c.vehiculos == 1                # el segundo vehículo se descuenta
    assert c.placas_leidas == 1


def test_conteo_misma_placa_lejos_en_el_tiempo_cuenta_dos_veces():
    """Si la placa reaparece tras un gap grande, son dos pasadas reales."""
    from modules.placas.video.plate_votes import ConteoVideo
    c = ConteoVideo(gap_fusion_s=2.0)
    c.confirmar_vehiculo(1, 1.0)
    c.cerrar_track(1, "ABC123", "CARRO", 0.9, primer_ts=1.0, ultimo_ts=3.0)
    c.confirmar_vehiculo(2, 30.0)
    ev = c.cerrar_track(2, "ABC123", "CARRO", 0.8, primer_ts=30.0, ultimo_ts=33.0)
    assert ev is not None
    assert c.vehiculos == 2
    assert c.placas_leidas == 2


def test_conteo_vehiculos_no_va_negativo():
    """cerrar_track con fusión no puede hacer vehiculos < 0."""
    from modules.placas.video.plate_votes import ConteoVideo
    c = ConteoVideo(gap_fusion_s=10.0)
    # No se llamó confirmar_vehiculo, vehiculos=0
    ev = c.cerrar_track(1, "ABC123", "CARRO", 0.9, primer_ts=1.0, ultimo_ts=3.0)
    # Primera vez: no hay previo → cuenta normalmente
    assert c.placas_leidas == 1
    # Segunda llamada con la misma placa en gap → fusión, no negativo
    c2 = ConteoVideo(gap_fusion_s=10.0)
    c2.confirmar_vehiculo(1, 1.0)
    c2.cerrar_track(1, "ABC123", "CARRO", 0.9, primer_ts=1.0, ultimo_ts=3.0)
    c2.confirmar_vehiculo(2, 3.5)
    c2.cerrar_track(2, "ABC123", "CARRO", 0.8, primer_ts=3.5, ultimo_ts=5.0)
    assert c2.vehiculos >= 0  # nunca negativo


def test_conteo_confianza_invalida_no_crashea():
    """confianza NaN o non-numeric no crashea el sistema."""
    from modules.placas.video.plate_votes import ConteoVideo
    c = ConteoVideo()
    c.confirmar_vehiculo(1, 1.0)
    ev = c.cerrar_track(1, "ABC123", "CARRO", float("nan"), primer_ts=1.0, ultimo_ts=3.0)
    assert ev is not None
    assert ev["confianza"] == 0.0  # NaN convertido a 0.0


# ── TrackCropBuffer ───────────────────────────────────────────────────────────

def _crop_nitido(h=40, w=120):
    """Recorte sintético con alta varianza Laplaciana (ruido)."""
    import numpy as np
    rng = np.random.default_rng(42)
    return rng.integers(0, 255, size=(h, w, 3), dtype=np.uint8)


def _crop_borroso(h=40, w=120):
    """Recorte sintético plano (varianza Laplaciana ~0)."""
    import numpy as np
    return np.full((h, w, 3), 128, dtype=np.uint8)


def test_buffer_descarta_recortes_muy_pequenos():
    from modules.placas.video.best_frames import TrackCropBuffer
    buf = TrackCropBuffer()
    buf.agregar(1, _crop_nitido(h=8))          # alto < 12 px
    assert buf.mejores(1) == []


def test_buffer_prefiere_nitido_sobre_borroso():
    from modules.placas.video.best_frames import TrackCropBuffer
    buf = TrackCropBuffer(k=2)
    buf.agregar(1, _crop_borroso())
    buf.agregar(1, _crop_nitido())
    mejores = buf.mejores(1, n=1)
    assert len(mejores) == 1
    assert mejores[0].std() > 5   # el mejor debe ser el nítido


def test_buffer_limita_a_k():
    from modules.placas.video.best_frames import TrackCropBuffer
    buf = TrackCropBuffer(k=3)
    for _ in range(10):
        buf.agregar(1, _crop_nitido())
    assert len(buf.mejores(1, n=99)) == 3


def test_buffer_descartar_libera_memoria():
    from modules.placas.video.best_frames import TrackCropBuffer
    buf = TrackCropBuffer()
    buf.agregar(1, _crop_nitido())
    buf.descartar(1)
    assert buf.mejores(1) == []
