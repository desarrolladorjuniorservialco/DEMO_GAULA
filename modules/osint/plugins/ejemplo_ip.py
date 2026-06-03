import requests
from modules.osint.plugins.base import BaseOsintPlugin


class IpGeoPlugin(BaseOsintPlugin):
    name          = "ip_geolocation"
    category      = "network"
    needs_api_key = False

    def ejecutar(self, objetivo: str) -> dict:
        try:
            r = requests.get(f"http://ip-api.com/json/{objetivo}", timeout=5)
            r.raise_for_status()
            return {"status": "ok", "plugin": self.name, "data": r.json()}
        except Exception as exc:
            return {"status": "error", "plugin": self.name, "error": str(exc)}
