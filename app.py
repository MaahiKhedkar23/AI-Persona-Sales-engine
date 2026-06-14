"""
app.py — SalesAI Platform
Supports: local dev (HTTP) + Render/Railway production (HTTPS)
"""
import os
from datetime import timedelta
from flask import Flask
from dotenv import load_dotenv

load_dotenv()   
from authlib.integrations.flask_client import OAuth
from models import init_db
from routes.main_routes import main_bp

oauth = OAuth()


def create_app():
    app = Flask(__name__)

    # ── SECRET KEY ────────────────────────────────────
    app.secret_key = os.environ.get("SECRET_KEY", "salesai-dev-secret-xK9mQ-2025")
    app.permanent_session_lifetime = timedelta(days=7)

    # ── ALLOW HTTP ON LOCALHOST (fixes OAuth locally) ─
    # On Render/production this env var won't be set, so HTTPS is enforced
    if os.environ.get("FLASK_ENV") != "production":
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # ── PROXY FIX for Render/Railway ──────────────────
    # Needed so url_for() generates https:// behind a proxy
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # ── OAUTH ─────────────────────────────────────────
    oauth.init_app(app)

    oauth.register(
        name                = "google",
        client_id           = os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret       = os.environ.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs       = {"scope": "openid email profile"},
    )

    oauth.register(
        name              = "github",
        client_id         = os.environ.get("GITHUB_CLIENT_ID"),
        client_secret     = os.environ.get("GITHUB_CLIENT_SECRET"),
        access_token_url  = "https://github.com/login/oauth/access_token",
        authorize_url     = "https://github.com/login/oauth/authorize",
        api_base_url      = "https://api.github.com/",
        client_kwargs     = {"scope": "user:email"},
    )

    app.register_blueprint(main_bp)
    app.extensions["oauth"] = oauth

    return app


if __name__ == "__main__":
    init_db()
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    print(f"🚀 SalesAI → http://127.0.0.1:{port}")
    app.run(debug=debug, host="0.0.0.0", port=port)
