# modules/__init__.py
import os
from flask import Flask
from werkzeug.security import generate_password_hash
from modules.extensions import db
from modules.config import Config


def create_app(config=None):
    _basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app = Flask(__name__, template_folder=os.path.join(_basedir, "templates"), static_folder=os.path.join(_basedir, "static"))
    app.config.from_object(config or Config)

    db.init_app(app)

    from flask import jsonify

    @app.errorhandler(413)
    def request_too_large(e):
        lim = app.config.get("MAX_CONTENT_LENGTH", 0) // 1024 // 1024
        return jsonify({"ok": False, "error": f"Archivo supera el límite de {lim} MB"}), 413

    @app.after_request
    def disable_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    _register_blueprints(app)

    with app.app_context():
        _data_dir = "/tmp/data" if os.environ.get("VERCEL") else os.path.join(_basedir, "data")
        os.makedirs(_data_dir, exist_ok=True)
        db.create_all()
        if not app.config.get("TESTING"):
            _seed_db()

    return app


def _register_blueprints(app):
    from modules.auth        import auth_bp
    from modules.casos       import casos_bp
    from modules.inteligencia import intel_bp
    from modules.dashboard   import dashboard_bp
    from modules.dataset     import dataset_bp
    from modules.osint.search   import search_osint_bp
    from modules.osint.history  import history_osint_bp
    from modules.osint.dashboard import dashboard_osint_bp
    from modules.osint.social    import social_osint_bp
    from modules.osint.analytics  import analytics_osint_bp
    from modules.osint.watchlists import watchlists_osint_bp
    from modules.osint.opendata  import opendata_bp
    from modules.chatbot import chatbot_bp
    from modules.placas import placas_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(casos_bp)
    app.register_blueprint(intel_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(dataset_bp)
    app.register_blueprint(search_osint_bp,    url_prefix="/osint")
    app.register_blueprint(history_osint_bp,   url_prefix="/osint")
    app.register_blueprint(dashboard_osint_bp, url_prefix="/osint")
    app.register_blueprint(social_osint_bp,    url_prefix="/osint/social")
    app.register_blueprint(analytics_osint_bp, url_prefix="/osint/analytics")
    app.register_blueprint(watchlists_osint_bp, url_prefix="/osint/watchlists")
    app.register_blueprint(opendata_bp,         url_prefix="/osint/opendata")
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(placas_bp, url_prefix="/placas")


def _seed_db():
    from models.nexo147 import Usuario, UnidadGaula
    from models.osint import FuenteOsint, ConsultaOsint, CacheConsulta, ResultadoOsint, IndicadorRiesgo, WatchlistOsint  # noqa: F401
    from models.osint_graph import Node as OsintNode, OsintEdge  # noqa: F401

    if Usuario.query.count() == 0:
        for username, pwd, nombre, rol in [
            ("admin",    "Admin147*",    "Administrador NEXO-147", "admin"),
            ("director", "Director147*", "Director GAULA",         "director"),
            ("analista", "Analista147*", "Analista Operacional",   "analista"),
            ("operador", "Operador147*", "Operador Linea 147",     "operador"),
        ]:
            db.session.add(Usuario(
                username=username,
                password_hash=generate_password_hash(pwd),
                nombre=nombre,
                rol=rol,
                created_by="seed",
            ))
        db.session.commit()

    if UnidadGaula.query.count() == 0:
        for nombre, ciudad, depto in [
            ("GAULA Bogota D.C.",  "Bogota",       "Cundinamarca"),
            ("GAULA Medellin",     "Medellin",     "Antioquia"),
            ("GAULA Cali",         "Cali",         "Valle del Cauca"),
            ("GAULA Barranquilla", "Barranquilla", "Atlantico"),
            ("GAULA Bucaramanga",  "Bucaramanga",  "Santander"),
        ]:
            db.session.add(UnidadGaula(nombre=nombre, ciudad=ciudad, departamento=depto, created_by="seed"))
        db.session.commit()

    from modules.osint.plugins.registry import discover_plugins
    discover_plugins()
