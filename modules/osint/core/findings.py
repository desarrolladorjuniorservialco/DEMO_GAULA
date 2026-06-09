from __future__ import annotations

from collections import Counter
from typing import Iterable

from .schemas import NormalizedResult


_RISK_LEVELS = (
    (16, "Crítico"),
    (11, "Alto"),
    (6, "Medio"),
    (0, "Bajo"),
)


class FindingEngine:
    def build(self, results: Iterable[NormalizedResult]) -> tuple[list[dict], dict]:
        items = list(results)
        counts = Counter(item.entity_type for item in items)
        findings: list[dict] = []
        score = 0

        emails = counts.get("email", 0)
        phones = counts.get("phone", 0)
        socials = counts.get("social_profile", 0)
        repos = counts.get("repository", 0)
        domains = counts.get("domain", 0)
        ips = counts.get("ip", 0)
        orgs = counts.get("organization", 0)
        aliases = counts.get("alias", 0)

        if emails:
            score += min(6, emails * 2)
            findings.append(
                {
                    "nivel": "Alto" if emails > 1 else "Medio",
                    "titulo": "Correo electrónico expuesto",
                    "descripcion": f"Se detectaron {emails} dirección(es) de correo.",
                    "tipo": "identidad",
                }
            )

        if phones:
            score += min(5, phones * 2)
            findings.append(
                {
                    "nivel": "Alto" if phones > 1 else "Medio",
                    "titulo": "Teléfono expuesto",
                    "descripcion": f"Se detectaron {phones} número(s) telefónico(s).",
                    "tipo": "identidad",
                }
            )

        if aliases:
            score += min(3, aliases)
            findings.append(
                {
                    "nivel": "Medio",
                    "titulo": "Alias detectado",
                    "descripcion": f"Se detectaron {aliases} alias o nombres alternativos.",
                    "tipo": "identidad",
                }
            )

        if socials >= 2:
            score += min(4, socials)
            findings.append(
                {
                    "nivel": "Medio",
                    "titulo": "Presencia en múltiples plataformas",
                    "descripcion": f"Se observó actividad en {socials} perfiles/redes.",
                    "tipo": "identidad",
                }
            )

        if repos:
            score += min(3, repos)
            findings.append(
                {
                    "nivel": "Bajo" if repos == 1 else "Medio",
                    "titulo": "Repositorios públicos detectados",
                    "descripcion": f"Se detectaron {repos} repositorio(s) asociado(s).",
                    "tipo": "tecnico",
                }
            )

        if domains and ips:
            score += 4
            findings.append(
                {
                    "nivel": "Alto",
                    "titulo": "Infraestructura propia probable",
                    "descripcion": "Se detectaron IP y dominio en el mismo conjunto de resultados.",
                    "tipo": "correlacion",
                }
            )

        if orgs and emails:
            score += 4
            findings.append(
                {
                    "nivel": "Alto",
                    "titulo": "Posible perfil laboral",
                    "descripcion": "Correo y organización aparecen correlacionados.",
                    "tipo": "correlacion",
                }
            )

        risk_level = "Bajo"
        for threshold, label in _RISK_LEVELS:
            if score >= threshold:
                risk_level = label
                break

        findings.append(
            {
                "nivel": risk_level,
                "titulo": f"Riesgo operativo: {risk_level}",
                "descripcion": f"Score acumulado: {score}. Hallazgos: {len(findings)}.",
                "tipo": "resumen",
            }
        )

        return findings, {"score": min(20, score), "level": risk_level}
