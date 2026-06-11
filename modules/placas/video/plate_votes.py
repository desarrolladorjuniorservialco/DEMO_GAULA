from __future__ import annotations

import threading

from modules.placas.engine import extraer_placas_de_texto


class PlateVoter:
    """Acumula lecturas OCR por track y resuelve la placa final por mayoría ponderada."""

    def __init__(self) -> None:
        self._votos: dict[int, dict[str, float]] = {}
        self._tipos: dict[str, str] = {}
        self._lock = threading.Lock()

    def agregar_lectura(self, track_id: int, texto: str | None, confianza: float) -> bool:
        if not texto:
            return False
        candidatos = extraer_placas_de_texto(texto)
        if not candidatos:
            return False
        placa, tipo, exacto = candidatos[0]
        peso = max(0.05, float(confianza)) + (0.15 if exacto else 0.0)
        with self._lock:
            votos = self._votos.setdefault(track_id, {})
            votos[placa] = votos.get(placa, 0.0) + peso
            self._tipos.setdefault(placa, tipo)
        return True

    def resolver(self, track_id: int) -> tuple[str | None, str | None, float]:
        with self._lock:
            votos = self._votos.get(track_id)
            if not votos:
                return None, None, 0.0
            placa = max(votos, key=votos.get)
            total = sum(votos.values())
            return placa, self._tipos.get(placa), round(votos[placa] / total, 2)


class ConteoVideo:
    """Contadores y eventos del conteo; fusiona tracks duplicados de la misma placa.

    Eventos (dicts append-only, consumidos incrementalmente por el SSE):
      {"tipo": "vehiculo",    "track_id": int, "ts_s": float}
      {"tipo": "placa",       "track_id": int, "placa": str,
       "tipo_vehiculo": str|None, "confianza": float, "ts_s": float}
      {"tipo": "sin_lectura", "track_id": int, "ts_s": float}
    """

    def __init__(self, gap_fusion_s: float = 2.0) -> None:
        self._gap = gap_fusion_s
        self._lock = threading.Lock()
        self.eventos: list[dict] = []
        self.vehiculos = 0
        self.placas_leidas = 0
        self.sin_lectura = 0
        self._placas_vistas: dict[str, tuple[float, float]] = {}

    def confirmar_vehiculo(self, track_id: int, ts_s: float) -> dict:
        with self._lock:
            self.vehiculos += 1
            ev = {"tipo": "vehiculo", "track_id": track_id, "ts_s": round(ts_s, 2)}
            self.eventos.append(ev)
            return ev

    def cerrar_track(
        self,
        track_id: int,
        placa: str | None,
        tipo: str | None,
        confianza: float,
        primer_ts: float,
        ultimo_ts: float,
    ) -> dict | None:
        """Resultado final de un track confirmado. Devuelve el evento emitido,
        o None si se fusionó con un track previo de la misma placa."""
        with self._lock:
            if placa is None:
                self.sin_lectura += 1
                ev = {"tipo": "sin_lectura", "track_id": track_id,
                      "ts_s": round(primer_ts, 2)}
                self.eventos.append(ev)
                return ev

            previo = self._placas_vistas.get(placa)
            if previo and primer_ts - previo[1] < self._gap:
                if self.vehiculos > 0:
                    self.vehiculos -= 1
                self._placas_vistas[placa] = (previo[0], max(previo[1], ultimo_ts))
                return None

            try:
                conf_val = float(confianza)
                if not (0.0 <= conf_val <= 1.0):
                    conf_val = max(0.0, min(1.0, conf_val)) if conf_val == conf_val else 0.0
            except (ValueError, TypeError):
                conf_val = 0.0

            self._placas_vistas[placa] = (primer_ts, ultimo_ts)
            self.placas_leidas += 1
            ev = {"tipo": "placa", "track_id": track_id, "placa": placa,
                  "tipo_vehiculo": tipo, "confianza": round(conf_val, 2),
                  "ts_s": round(primer_ts, 2)}
            self.eventos.append(ev)
            return ev
