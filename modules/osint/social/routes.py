import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FutureTimeoutError
from flask import render_template, request
from modules.osint.auth import login_required
from modules.osint.social import social_osint_bp
from modules.osint.social.scrapers.facebook_playwright import scrape_facebook_profile
from modules.osint.services.search_engine import ejecutar_dork_universal
from modules.osint.services.x_osint import extract_x_profiles, persist_x_profiles
from modules.osint.services.tiktok_osint import extract_tiktok_profiles, persist_tiktok_profiles
from modules.osint.services.facebook_osint import persist_facebook_data
from modules.osint.plugins.registry import get_plugins

GITHUB_HEADERS = {
    "User-Agent": "OSINT-Terminal/1.0 (educational research)",
    "Accept":     "application/vnd.github+json",
}

REDDIT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/html, */*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Referer":         "https://www.reddit.com/",
}

TIMEOUT          = 10
PARALLEL_TIMEOUT = 30


def _fetch_github(username: str) -> tuple:
    errors  = []
    profile = None
    repos   = []

    try:
        r = requests.get(
            f"https://api.github.com/users/{username}",
            headers=GITHUB_HEADERS, timeout=TIMEOUT,
        )
        r.raise_for_status()
        profile = r.json()
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else "?"
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
    errors  = []
    profile = None
    posts   = []

    try:
        r = requests.get(
            f"https://www.reddit.com/user/{username}/about.json",
            headers=REDDIT_HEADERS, timeout=TIMEOUT,
        )
        r.raise_for_status()
        data    = r.json()
        profile = data.get("data", {})
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else "?"
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
                headers=REDDIT_HEADERS, params={"limit": 10}, timeout=TIMEOUT,
            )
            r2.raise_for_status()
            children = r2.json().get("data", {}).get("children", [])
            posts    = [c["data"] for c in children]
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response else "?"
            errors.append(f"Reddit posts: error HTTP {code}.")
        except requests.exceptions.RequestException as e:
            errors.append(f"Reddit posts: {e}.")

    return profile, posts, errors


def _task_github(username):
    profile, repos, errors = _fetch_github(username)
    return {"profile": profile, "repos": repos, "errors": errors}

def _task_reddit(username):
    profile, posts, errors = _fetch_reddit(username)
    return {"profile": profile, "posts": posts, "errors": errors}

def _task_facebook(username):
    data, errors = scrape_facebook_profile(username)
    return {"data": data, "errors": errors}

def _task_x(username):
    raw    = ejecutar_dork_universal(username, ["x"], max_results=30)
    res    = raw.get("x", {})
    x_data = extract_x_profiles(res.get("results", []), username)
    return {"data": x_data, "errors": res.get("errors", [])}

def _task_tiktok(username):
    raw         = ejecutar_dork_universal(username, ["tiktok"], max_results=30)
    res         = raw.get("tiktok", {})
    tiktok_data = extract_tiktok_profiles(res.get("results", []), username)
    return {"data": tiktok_data, "errors": res.get("errors", [])}


_ALL_TASKS = {
    "github":   _task_github,
    "reddit":   _task_reddit,
    "facebook": _task_facebook,
    "x":        _task_x,
    "tiktok":   _task_tiktok,
}


def _ejecutar_busqueda_paralela(username: str) -> dict:
    results: dict = {}
    with ThreadPoolExecutor(max_workers=5, thread_name_prefix="osint") as executor:
        futures = {
            executor.submit(fn, username): key
            for key, fn in _ALL_TASKS.items()
        }
        try:
            for future in as_completed(futures, timeout=PARALLEL_TIMEOUT + 10):
                key = futures[future]
                try:
                    results[key] = future.result(timeout=PARALLEL_TIMEOUT)
                except FutureTimeoutError:
                    results[key] = {"errors": [f"{key}: timeout ({PARALLEL_TIMEOUT}s)."]}
                except Exception as exc:
                    results[key] = {"errors": [f"{key}: error inesperado ({exc})."]}
        except FutureTimeoutError:
            pass

    for key in _ALL_TASKS:
        if key not in results:
            results[key] = {"errors": [f"{key}: no completó en el tiempo máximo."]}

    return results


@social_osint_bp.route("/lookup")
@login_required
def lookup():
    username = request.args.get("q", "").strip()
    source   = request.args.get("source", "github")

    if not username:
        return render_template(
            "osint/social_fragment.html",
            username=username, source=source,
            errors=["No se proporcionó un nombre de usuario."],
        )

    github_profile = github_repos = None
    reddit_profile = reddit_posts = None
    facebook_data  = None
    x_data         = None
    tiktok_data    = None
    errors: list   = []

    if source == "all":
        parallel = _ejecutar_busqueda_paralela(username)

        gh = parallel.get("github", {})
        github_profile = gh.get("profile")
        github_repos   = gh.get("repos", [])
        errors.extend(gh.get("errors", []))

        rd = parallel.get("reddit", {})
        reddit_profile = rd.get("profile")
        reddit_posts   = rd.get("posts", [])
        errors.extend(rd.get("errors", []))

        fb = parallel.get("facebook", {})
        facebook_data = fb.get("data")
        errors.extend(fb.get("errors", []))
        if facebook_data:
            try:
                facebook_data["saved_nodes"] = persist_facebook_data(facebook_data, username)
            except Exception as exc:
                errors.append(f"Facebook DB persist: {exc}")
                facebook_data["saved_nodes"] = 0

        x_res  = parallel.get("x", {})
        x_data = x_res.get("data")
        errors.extend(x_res.get("errors", []))
        if x_data:
            try:
                x_data["saved_nodes"] = persist_x_profiles(x_data, username)
            except Exception as exc:
                errors.append(f"X DB persist: {exc}")
                x_data["saved_nodes"] = 0

        tk_res      = parallel.get("tiktok", {})
        tiktok_data = tk_res.get("data")
        errors.extend(tk_res.get("errors", []))
        if tiktok_data:
            try:
                tiktok_data["saved_nodes"] = persist_tiktok_profiles(tiktok_data, username)
            except Exception as exc:
                errors.append(f"TikTok DB persist: {exc}")
                tiktok_data["saved_nodes"] = 0

    else:
        if source in ("github", "both"):
            github_profile, github_repos, gh_errors = _fetch_github(username)
            errors.extend(gh_errors)

        if source in ("reddit", "both"):
            reddit_profile, reddit_posts, rd_errors = _fetch_reddit(username)
            errors.extend(rd_errors)

        if source == "facebook":
            facebook_data, fb_errors = scrape_facebook_profile(username)
            errors.extend(fb_errors)
            if facebook_data:
                try:
                    facebook_data["saved_nodes"] = persist_facebook_data(facebook_data, username)
                except Exception as exc:
                    errors.append(f"Facebook DB persist: {exc}")
                    facebook_data["saved_nodes"] = 0

        plataformas_dork = []
        if source == "x":
            plataformas_dork.append("x")
        if source == "tiktok":
            plataformas_dork.append("tiktok")
        if source == "deep_all":
            plataformas_dork.extend(["x", "tiktok", "facebook"])
            facebook_data, fb_errors = scrape_facebook_profile(username)
            errors.extend(fb_errors)
            if facebook_data:
                try:
                    facebook_data["saved_nodes"] = persist_facebook_data(facebook_data, username)
                except Exception as exc:
                    errors.append(f"Facebook DB persist: {exc}")
                    facebook_data["saved_nodes"] = 0

        if plataformas_dork:
            dork_results = ejecutar_dork_universal(username, plataformas_dork, max_results=50)

            if "x" in dork_results:
                raw_x  = dork_results["x"].get("results", [])
                errors.extend(dork_results["x"].get("errors", []))
                x_data = extract_x_profiles(raw_x, username)
                try:
                    x_data["saved_nodes"] = persist_x_profiles(x_data, username)
                except Exception as exc:
                    errors.append(f"X DB persist: {exc}")
                    x_data["saved_nodes"] = 0

            if "tiktok" in dork_results:
                raw_tk      = dork_results["tiktok"].get("results", [])
                errors.extend(dork_results["tiktok"].get("errors", []))
                tiktok_data = extract_tiktok_profiles(raw_tk, username)
                try:
                    tiktok_data["saved_nodes"] = persist_tiktok_profiles(tiktok_data, username)
                except Exception as exc:
                    errors.append(f"TikTok DB persist: {exc}")
                    tiktok_data["saved_nodes"] = 0

    plugin_results = []
    for plugin in get_plugins():
        try:
            plugin_results.append(plugin.ejecutar(username))
        except Exception as exc:
            errors.append(f"Plugin {plugin.name}: {exc}")

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
        plugin_results=plugin_results,
        errors=errors,
    )
