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
