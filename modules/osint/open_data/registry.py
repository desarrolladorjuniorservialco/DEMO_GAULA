from __future__ import annotations

from importlib import import_module
from pkgutil import walk_packages
from types import ModuleType

from .base import BaseOpenDataSource


class OpenDataRegistry:
    """Registry and autodiscovery helper for open-data sources."""

    def __init__(self) -> None:
        self._sources: dict[str, BaseOpenDataSource] = {}

    def register(self, source: BaseOpenDataSource) -> BaseOpenDataSource:
        self._sources[source.name] = source
        return source

    def get(self, name: str) -> BaseOpenDataSource | None:
        return self._sources.get(name)

    def all(self) -> list[BaseOpenDataSource]:
        return list(self._sources.values())

    def discover(self, package_name: str = "modules.osint.open_data") -> list[BaseOpenDataSource]:
        package = import_module(package_name)
        if not hasattr(package, "__path__"):
            return self.all()

        for module_info in walk_packages(package.__path__, package.__name__ + "."):
            try:
                module = import_module(module_info.name)
            except Exception:
                continue
            self._register_module_sources(module)
        return self.all()

    def _register_module_sources(self, module: ModuleType) -> None:
        for obj in module.__dict__.values():
            if not isinstance(obj, type):
                continue
            if obj is BaseOpenDataSource or not issubclass(obj, BaseOpenDataSource):
                continue
            try:
                self.register(obj())
            except Exception:
                continue


open_data_registry = OpenDataRegistry()
