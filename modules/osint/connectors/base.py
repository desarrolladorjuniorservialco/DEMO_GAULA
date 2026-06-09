from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ConnectorResult:
    """Resultado normalizado que todo conector debe producir."""
    connector: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "connector": self.connector,
            "ok": self.ok,
            "data": self.data,
            "errors": self.errors,
            "metadata": self.metadata,
        }


class BaseConnector(ABC):
    """
    Contrato I/O para todos los conectores OSINT.

    Diferencias con BaseOsintPlugin
    --------------------------------
    BaseOsintPlugin: unidad de composición auto-descubierta por registry.py.
    BaseConnector:   unidad de I/O tipada; retorna ConnectorResult; bloque
                     atómico sobre el que la orquestación construye la recolección.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador único snake_case. Ej: 'github', 'crtsh'."""
        ...

    @property
    @abstractmethod
    def supported_target_types(self) -> frozenset[str]:
        """
        Tipos de objetivo para los que este conector es aplicable.
        Vocabulario: 'username', 'email', 'domain', 'ip', 'phone',
                     'hash', 'url', 'alias', 'full_name'.
        """
        ...

    @property
    def needs_api_key(self) -> bool:
        return False

    @property
    def rate_limit_per_minute(self) -> int:
        return 0

    @property
    def timeout_seconds(self) -> float:
        return 10.0

    def supports(self, target_type: str) -> bool:
        return target_type in self.supported_target_types

    @abstractmethod
    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        """
        Ejecuta la consulta para el objetivo dado.

        Garantías:
        - NUNCA lanza excepciones; los registra en ConnectorResult.errors.
        - Retorna ConnectorResult(ok=False) si no hay datos utilizables.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
