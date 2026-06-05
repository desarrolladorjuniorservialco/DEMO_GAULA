import importlib
import pkgutil
from pathlib import Path

from modules.osint.plugins.base import BaseOsintPlugin

_REGISTRY: list[BaseOsintPlugin] = []
_DISCOVERED = False


def discover_plugins() -> None:
    global _DISCOVERED
    if _DISCOVERED:
        return

    plugins_dir = Path(__file__).parent

    _REGISTRY.clear()
    for module_info in pkgutil.iter_modules([str(plugins_dir)]):
        if module_info.name in ("base", "registry"):
            continue

        module_path = f"modules.osint.plugins.{module_info.name}"
        try:
            mod = importlib.import_module(module_path)
        except Exception as exc:
            print(f"[osint-plugins] ERROR importando '{module_path}': {exc}")
            continue

        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseOsintPlugin)
                and attr is not BaseOsintPlugin
            ):
                try:
                    instance = attr()
                    _REGISTRY.append(instance)
                    print(f"[osint-plugins] Registrado: {instance.name}")
                except Exception as exc:
                    print(f"[osint-plugins] ERROR instanciando '{attr_name}': {exc}")

    _DISCOVERED = True


def get_plugins() -> list[BaseOsintPlugin]:
    return _REGISTRY
