# modules/auth/routes.py
from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from modules.auth import auth_bp
from modules.auth.decorators import login_required
from models.nexo147 import Usuario


@auth_bp.route("/")
@login_required
def home():
    return render_template("casos/console.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("auth.home"))
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()
        user = Usuario.query.filter_by(username=usuario, activo=True).first()
        if user and check_password_hash(user.password_hash, password):
            session["user"] = user.username
            session["role"] = user.rol
            session["name"] = user.nombre
            return redirect(url_for("auth.home"))
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
