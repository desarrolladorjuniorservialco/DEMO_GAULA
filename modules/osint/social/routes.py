import requests
from flask import render_template, request, session

from modules.osint.auth import login_required
from modules.osint.core.engine import UniversalOsintEngine
from modules.osint.social import social_osint_bp

GITHUB_HEADERS = {
    "User-Agent": "OSINT-Terminal/1.0 (educational research)",
    "Accept": "application/vnd.github+json",
}

REDDIT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://www.reddit.com/",
}

TIMEOUT = 10


def _fetch_github(username: str) -> tuple:
    errors = []
    profile = None
    repos = []

    try:
        r = requests.get(
            f"https://api.github.com/users/{username}",
            headers=GITHUB_HEADERS,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        profile = r.json()
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        if code == 404:
            errors.append(f"GitHub: usuario '{username}' no encontrado.")
        else:
            errors.append(f"GitHub: error HTTP {code}.")
    except requests.exceptions.ConnectionError:
        errors.append("GitHub: error de conexión.")
    except requests.exceptions.Timeout:
        errors.append("GitHub: tiempo de espera agotado.")
    except requests.exceptions.RequestException as e:
        errors.append(f"GitHub: {e}.")

    if profile:
        try:
            r2 = requests.get(
                f"https://api.github.com/users/{username}/repos",
                headers=GITHUB_HEADERS,
                params={"per_page": 10, "sort": "updated"},
                timeout=TIMEOUT,
            )
            if r2.status_code == 200:
                repos = r2.json()
        except requests.exceptions.RequestException as e:
            errors.append(f"GitHub repos: {e}.")

    return profile, repos, errors


def _fetch_reddit(username: str) -> tuple:
    errors = []
    profile = None
    posts = []

    try:
        r = requests.get(
            f"https://www.reddit.com/user/{username}/about.json",
            headers=REDDIT_HEADERS,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        profile = data.get("data", {})
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        if code == 403:
            errors.append("Reddit: acceso denegado (403).")
        elif code == 429:
            errors.append("Reddit: rate limit (429).")
        elif code == 404:
            errors.append(f"Reddit: usuario '{username}' no encontrado.")
        else:
            errors.append(f"Reddit: error HTTP {code}.")
    except requests.exceptions.ConnectionError:
        errors.append("Reddit: error de conexión.")
    except requests.exceptions.Timeout:
        errors.append("Reddit: tiempo de espera agotado.")
    except requests.exceptions.RequestException as e:
        errors.append(f"Reddit: {e}.")

    if profile:
        try:
            r2 = requests.get(
                f"https://www.reddit.com/user/{username}/submitted.json",
                headers=REDDIT_HEADERS,
                params={"limit": 10},
                timeout=TIMEOUT,
            )
            r2.raise_for_status()
            children = r2.json().get("data", {}).get("children", [])
            posts = [c["data"] for c in children]
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            errors.append(f"Reddit posts: error HTTP {code}.")
        except requests.exceptions.RequestException as e:
            errors.append(f"Reddit posts: {e}.")

    return profile, posts, errors


_ENGINE = UniversalOsintEngine()


def _collect_errors(collectors: dict) -> list[str]:
    errors: list[str] = []
    for payload in collectors.values():
        errors.extend(payload.get("errors", []))
    return errors


@social_osint_bp.route("/lookup")
@login_required
def lookup():
    username = request.args.get("q", "").strip()
    source = request.args.get("source", "all").strip() or "all"

    if not username:
        return render_template(
            "osint/social_fragment.html",
            username=username,
            source=source,
            errors=["No se proporcionó un nombre de usuario."],
        )

    response = _ENGINE.search(
        target=username,
        source_hint=source,
        persist=True,
        user_name=session.get("user"),
        created_by=str(session.get("user") or "system"),
    )

    collectors = response.get("collectors", {})
    github_profile = collectors.get("github", {}).get("profile")
    github_repos = collectors.get("github", {}).get("repos")
    reddit_profile = collectors.get("reddit", {}).get("profile")
    reddit_posts = collectors.get("reddit", {}).get("posts")
    facebook_data  = collectors.get("facebook",  {}).get("data")
    x_data         = collectors.get("x",         {}).get("data")
    tiktok_data    = collectors.get("tiktok",    {}).get("data")
    instagram_data = collectors.get("instagram", {}).get("data")
    linkedin_data  = collectors.get("linkedin",  {}).get("data")
    plugin_results = collectors.get("plugins", {}).get("plugins", [])
    errors = _collect_errors(collectors)

    return render_template(
        "osint/social_fragment.html",
        username=username,
        source=source,
        github_profile=github_profile,
        github_repos=github_repos,
        reddit_profile=reddit_profile,
        reddit_posts=reddit_posts,
        facebook_data=facebook_data,
        x_data=x_data,
        tiktok_data=tiktok_data,
        instagram_data=instagram_data,
        linkedin_data=linkedin_data,
        plugin_results=plugin_results,
        errors=errors,
        findings=response.get("findings", []),
        risk=response.get("risk", {}),
        target_type=response.get("target_type", "unknown"),
    )
