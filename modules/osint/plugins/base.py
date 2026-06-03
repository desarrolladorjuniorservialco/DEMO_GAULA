"""
plugins/base.py — Clase base para plugins OSINT
================================================
Para crear un nuevo plugin, hereda de BaseOsintPlugin, define las
propiedades requeridas e implementa ejecutar(objetivo).
El motor de autodescubrimiento en registry.py lo instanciará
automáticamente al iniciar Flask — sin registrarlo manualmente.
"""

from abc import ABC, abstractmethod


class BaseOsintPlugin(ABC):
    """Contrato mínimo que debe cumplir cualquier plugin OSINT."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador único del plugin (snake_case)."""
        ...

    @property
    @abstractmethod
    def category(self) -> str:
        """Categoría semántica: 'network', 'social', 'identity', 'threat', etc."""
        ...

    @property
    def needs_api_key(self) -> bool:
        """True si el plugin requiere una API key configurada en .env."""
        return False

    @abstractmethod
    def ejecutar(self, objetivo: str) -> dict:
        """
        Ejecuta el plugin para el objetivo dado.

        Debe retornar siempre un dict con al menos:
          {
            "status":  "ok" | "error",
            "plugin":  self.name,
            "data":    {...},   # resultado real
          }
        En caso de error, incluir también "error": "<mensaje>".
        """
        ...
