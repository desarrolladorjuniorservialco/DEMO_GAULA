# modules/auth/decorators.py
from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") != "admin":
            flash("Acceso restringido a administradores.", "error")
            return redirect(url_for("auth.home"))
        return f(*args, **kwargs)
    return wrapper


def director_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") not in ["admin", "director"]:
            flash("Acceso restringido a directores y administradores.", "error")
            return redirect(url_for("auth.home"))
        return f(*args, **kwargs)
    return wrapper


def analista_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") not in ["admin", "analista"]:
            flash("Acceso restringido a analistas y administradores.", "error")
            return redirect(url_for("auth.home"))
        return f(*args, **kwargs)
    return wrapper


def operador_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") not in ["admin", "operador"]:
            flash("Acceso restringido a operadores y administradores.", "error")
            return redirect(url_for("auth.home"))
        return f(*args, **kwargs)
    return wrapper
