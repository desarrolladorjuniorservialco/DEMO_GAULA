import ipaddress
import re
import requests
from flask import render_template, request

from modules.osint.auth import login_required
from modules.osint.core.engine import UniversalOsintEngine
from modules.osint.opendata import opendata_osint_bp

HEADERS = {"User-Agent": "OSINT-Tool/1.0 (educational research)"}
TIMEOUT = 8

_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)


def _is_valid_ip(s):
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False


def _is_valid_domain(s):
    return bool(_DOMAIN_RE.match(s)) and len(s) <= 253


def _fetch_ip_geo(ip):
    errors = []
    result = None
    try:
        r = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={
                "fields": "status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                result = data
            else:
                errors.append(f"ip-api.com: {data.get('message', 'consulta fallida')}.")
        else:
            errors.append(f"ip-api.com: respuesta inesperada ({r.status_code}).")
    except requests.exceptions.ConnectionError:
        errors.append("ip-api.com: error de conexión.")
    except requests.exceptions.Timeout:
        errors.append("ip-api.com: tiempo de espera agotado.")
    except requests.exceptions.RequestException as e:
        errors.append(f"ip-api.com: error ({e}).")
    return result, errors


def _fetch_domain_rdap(domain):
    errors = []
    result = None
    try:
        r = requests.get(
            f"https://rdap.org/domain/{domain}",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            result = r.json()
        elif r.status_code == 404:
            errors.append(f"RDAP: dominio '{domain}' no encontrado.")
        else:
            errors.append(f"RDAP: respuesta inesperada ({r.status_code}).")
    except requests.exceptions.ConnectionError:
        errors.append("RDAP: error de conexión.")
    except requests.exceptions.Timeout:
        errors.append("RDAP: tiempo de espera agotado.")
    except requests.exceptions.RequestException as e:
        errors.append(f"RDAP: error ({e}).")
    return result, errors


def _fetch_crt_sh(domain):
    errors = []
    certs = []
    try:
        r = requests.get(
            "https://crt.sh/",
            params={"q": domain, "output": "json"},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            raw = r.json()
            seen = set()
            for entry in raw[:50]:
                name = entry.get("name_value", "")
                for sub in name.split("\n"):
                    sub = sub.strip()
                    if sub and sub not in seen:
                        seen.add(sub)
                        certs.append(
                            {
                                "name": sub,
                                "issuer": entry.get("issuer_name", ""),
                                "not_before": entry.get("not_before", ""),
                                "not_after": entry.get("not_after", ""),
                            }
                        )
        else:
            errors.append(f"crt.sh: respuesta inesperada ({r.status_code}).")
    except requests.exceptions.ConnectionError:
        errors.append("crt.sh: error de conexión.")
    except requests.exceptions.Timeout:
        errors.append("crt.sh: tiempo de espera agotado.")
    except requests.exceptions.RequestException as e:
        errors.append(f"crt.sh: error ({e}).")
    return certs, errors


def _parse_rdap(data):
    if not data:
        return {}
    parsed = {
        "handle": data.get("handle"),
        "ldhName": data.get("ldhName"),
        "status": data.get("status", []),
        "events": [],
        "nameservers": [],
        "entities": [],
    }
    for ev in data.get("events", []):
        parsed["events"].append({"action": ev.get("eventAction"), "date": ev.get("eventDate", "")[:10]})
    for ns in data.get("nameservers", []):
        parsed["nameservers"].append(ns.get("ldhName", ""))
    for ent in data.get("entities", []):
        roles = ent.get("roles", [])
        vcard = ent.get("vcardArray", [None, []])[1]
        name = next((v[3] for v in vcard if v[0] == "fn"), None) if vcard else None
        parsed["entities"].append({"roles": roles, "name": name})
    return parsed


_ENGINE = UniversalOsintEngine()


def _collect_errors(collectors: dict) -> list[str]:
    errors: list[str] = []
    for payload in collectors.values():
        errors.extend(payload.get("errors", []))
    return errors


@opendata_osint_bp.route("/lookup")
@login_required
def lookup():
    query = request.args.get("q", "").strip()
    source = request.args.get("source", "both")

    if not query:
        return render_template(
            "osint/opendata_fragment.html",
            query=query,
            source=source,
            errors=["No se proporcionó una consulta."],
        )

    response = _ENGINE.search(
        target=query,
        source_hint=source,
        persist=True,
        created_by="system",
    )
    collectors = response.get("collectors", {})
    ip_data = collectors.get("ip", {}).get("data")
    domain_collector = collectors.get("domain", {})
    rdap_data = domain_collector.get("rdap_data")
    crt_data = (domain_collector.get("crt_data") or {}).get("certs")
    errors = _collect_errors(collectors)

    return render_template(
        "osint/opendata_fragment.html",
        query=query,
        source=source,
        ip_data=ip_data,
        rdap_data=rdap_data,
        crt_data=crt_data,
        errors=errors,
        findings=response.get("findings", []),
        risk=response.get("risk", {}),
        target_type=response.get("target_type", "unknown"),
    )
