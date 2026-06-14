"""
routes/main_routes.py — All Flask routes.
Data isolation: every campaign query filtered by session user_id.
OAuth: Google + GitHub callbacks included.
"""
from flask import (Blueprint, render_template, request, jsonify,
                   session, redirect, url_for, current_app)
from functools import wraps

from services.ai_service       import generate_sales_strategy, get_hierarchy, get_behaviors
from services.analytics_service import generate_mock_analytics, generate_optimization_tips
from services.strategy_service  import (save_campaign, get_all_campaigns,
                                         get_campaign_full, delete_campaign)
from services.auth_service      import (register_user, login_user,
                                         oauth_get_or_create, get_user_by_id,
                                         get_user_count)
from services.tracking_service  import (compute_real_analytics, generate_campaign_links,
                                         get_campaign_links, record_click,
                                         record_email_open, record_page_view)

main_bp = Blueprint("main", __name__)


# ══════════════════════════════════════════════════════
# AUTH HELPERS
# ══════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.login_page", next=request.path))
        return f(*args, **kwargs)
    return decorated


def current_user():
    uid = session.get("user_id")
    return get_user_by_id(uid) if uid else None


def current_uid():
    return session.get("user_id")


def _set_session(user: dict):
    """Store user info in session."""
    session["user_id"]      = user["id"]
    session["username"]     = user["username"]
    session["avatar_url"]   = user.get("avatar_url", "")
    session["oauth_provider"]= user.get("oauth_provider", "")
    session.permanent       = True


# ══════════════════════════════════════════════════════
# PAGE ROUTES (all protected)
# ══════════════════════════════════════════════════════

@main_bp.route("/")
@login_required
def home():
    uid       = current_uid()
    campaigns = get_all_campaigns(user_id=uid)
    return render_template("home.html", campaigns=campaigns[:3],
                           total=len(campaigns), user=current_user())


@main_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", hierarchy=get_hierarchy(),
                           user=current_user())


@main_bp.route("/campaigns")
@login_required
def campaigns_page():
    campaigns = get_all_campaigns(user_id=current_uid())
    return render_template("campaigns.html", campaigns=campaigns,
                           user=current_user())


@main_bp.route("/campaigns/<int:cid>")
@login_required
def campaign_detail(cid):
    data = get_campaign_full(cid)
    if not data or data["campaign"].get("user_id") != current_uid():
        return render_template("404.html"), 404
    # Real analytics — no mock data
    real_an = compute_real_analytics(cid)
    data["analytics"] = real_an
    c = data["campaign"]
    data["optimization_tips"] = generate_optimization_tips(
        c["persona"], c["behavior"], real_an.get("tactic_data", []))
    return render_template("campaign_detail.html", data=data, user=current_user())


@main_bp.route("/execution/<int:cid>")
@login_required
def execution_workspace(cid):
    data = get_campaign_full(cid)
    if not data or data["campaign"].get("user_id") != current_uid():
        return render_template("404.html"), 404
    return render_template("execution_workspace.html", data=data,
                           campaign_id=cid, user=current_user())


@main_bp.route("/tracking/<int:cid>")
@login_required
def tracking_dashboard(cid):
    data = get_campaign_full(cid)
    if not data or data["campaign"].get("user_id") != current_uid():
        return render_template("404.html"), 404
    links     = generate_campaign_links(cid)
    analytics = compute_real_analytics(cid)
    return render_template("tracking_dashboard.html", data=data,
                           campaign_id=cid, links=links,
                           analytics=analytics, an=analytics,
                           user=current_user())


@main_bp.route("/personas")
@login_required
def personas_page():
    return render_template("personas.html", hierarchy=get_hierarchy(),
                           behaviors=get_behaviors(), user=current_user())


@main_bp.route("/analytics")
@login_required
def analytics_page():
    campaigns = get_all_campaigns(user_id=current_uid())
    return render_template("analytics.html", campaigns=campaigns,
                           user=current_user())


@main_bp.route("/about")
def about_page():
    return render_template("about.html", user=current_user())


# ══════════════════════════════════════════════════════
# API ROUTES
# ══════════════════════════════════════════════════════

@main_bp.route("/api/hierarchy")
def api_hierarchy():
    return jsonify(get_hierarchy())


@main_bp.route("/api/generate", methods=["POST"])
@login_required
def api_generate():
    import traceback
    body     = request.get_json() or {}
    product  = (body.get("product")  or "").strip()
    category = (body.get("category") or "").strip()
    persona  = (body.get("persona")  or "").strip()
    behavior = (body.get("behavior") or "").strip()

    errors = []
    if not product:  errors.append("Product name required.")
    if not category: errors.append("Category required.")
    if not persona:  errors.append("Persona required.")
    if not behavior: errors.append("Behavior required.")
    if errors:
        return jsonify({"success": False, "error": " | ".join(errors)}), 400

    h = get_hierarchy()
    if category not in h:
        return jsonify({"success": False, "error": "Invalid category."}), 400
    if persona not in h[category]["personas"]:
        return jsonify({"success": False, "error": "Invalid persona."}), 400

    try:
        result = generate_sales_strategy(product, category, persona, behavior)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

    if not result["success"]:
        return jsonify(result), 500

    ai_data  = result["data"]
    analytics = generate_mock_analytics(category, persona, behavior)
    opt_tips  = generate_optimization_tips(persona, behavior, analytics["tactic_data"])

    try:
        campaign_id = save_campaign(
            product, category, persona, behavior,
            ai_data, analytics, opt_tips,
            user_id=current_uid()       # ← data isolation
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": f"DB error: {e}"}), 500

    return jsonify({"success": True, "campaign_id": campaign_id,
                    "data": ai_data, "analytics": analytics, "opt_tips": opt_tips})


@main_bp.route("/api/campaigns")
@login_required
def api_campaigns():
    return jsonify(get_all_campaigns(user_id=current_uid()))


@main_bp.route("/api/campaigns/<int:cid>")
@login_required
def api_campaign(cid):
    data = get_campaign_full(cid)
    if not data or data["campaign"].get("user_id") != current_uid():
        return jsonify({"success": False, "error": "Not found"}), 404
    return jsonify({"success": True, "data": data})


@main_bp.route("/api/campaigns/<int:cid>/delete", methods=["POST"])
@login_required
def api_delete_campaign(cid):
    data = get_campaign_full(cid)
    if not data or data["campaign"].get("user_id") != current_uid():
        return jsonify({"success": False, "error": "Not found"}), 404
    ok = delete_campaign(cid)
    return jsonify({"success": ok})


@main_bp.route("/api/campaigns/<int:cid>/launch", methods=["POST"])
@login_required
def api_launch_campaign(cid):
    data = get_campaign_full(cid)
    if not data or data["campaign"].get("user_id") != current_uid():
        return jsonify({"success": False, "error": "Not found"}), 404
    from models import Session, Campaign
    db = Session()
    try:
        c = db.query(Campaign).filter_by(id=cid).first()
        c.execution_status = "launched"
        db.commit()
        links = generate_campaign_links(cid)
        return jsonify({"success": True, "status": "launched",
                        "links": links, "tracking_url": f"/tracking/{cid}"})
    finally:
        db.close()


@main_bp.route("/api/campaigns/<int:cid>/start-tracking", methods=["POST"])
@login_required
def api_start_tracking(cid):
    data = get_campaign_full(cid)
    if not data or data["campaign"].get("user_id") != current_uid():
        return jsonify({"success": False, "error": "Not found"}), 404
    from models import Session, Campaign
    db = Session()
    try:
        c = db.query(Campaign).filter_by(id=cid).first()
        c.execution_status = "tracking"
        db.commit()
        links     = generate_campaign_links(cid)
        analytics = compute_real_analytics(cid)
        opt_tips  = generate_optimization_tips(
            data["campaign"]["persona"],
            data["campaign"]["behavior"],
            analytics.get("tactic_data", []))
        return jsonify({"success": True, "status": "tracking",
                        "analytics": analytics, "opt_tips": opt_tips,
                        "links": links, "tracking_url": f"/tracking/{cid}"})
    finally:
        db.close()


@main_bp.route("/api/campaigns/<int:cid>/links")
@login_required
def api_campaign_links(cid):
    data = get_campaign_full(cid)
    if not data or data["campaign"].get("user_id") != current_uid():
        return jsonify({"success": False}), 404
    return jsonify({"success": True, "links": get_campaign_links(cid)})


@main_bp.route("/api/campaigns/<int:cid>/real-analytics")
@login_required
def api_real_analytics(cid):
    data = get_campaign_full(cid)
    if not data or data["campaign"].get("user_id") != current_uid():
        return jsonify({"success": False}), 404
    return jsonify({"success": True, "data": compute_real_analytics(cid)})


@main_bp.route("/api/track/view", methods=["POST"])
def api_track_view():
    body = request.get_json() or {}
    cid  = body.get("campaign_id")
    if not cid:
        return jsonify({"success": False}), 400
    record_page_view(int(cid), body.get("stage",""), request)
    return jsonify({"success": True})


@main_bp.route("/api/test")
def api_test():
    import os
    from models import Session, Campaign
    key = os.environ.get("GROQ_API_KEY","")
    try:
        db = Session()
        count = db.query(Campaign).count()
        db.close()
        db_ok = True
    except Exception as e:
        db_ok = False; count = 0
    return jsonify({"groq_key_set": bool(key),
                    "groq_key_prefix": (key[:8]+"...") if key else "NOT SET",
                    "db_ok": db_ok, "campaign_count": count,
                    "logged_in": "user_id" in session})


@main_bp.route("/api/auth/me")
def api_auth_me():
    user = current_user()
    if not user:
        return jsonify({"logged_in": False}), 401
    return jsonify({"logged_in": True, "user": user})


# ══════════════════════════════════════════════════════
# TRACKING ROUTES
# ══════════════════════════════════════════════════════

@main_bp.route("/t/<token>")
def track_click(token):
    from flask import Response
    result = record_click(token, request)
    if not result:
        return "Link not found", 404
    dest = result.get("destination") or f"/campaigns/{result['campaign_id']}"
    return redirect(dest)


@main_bp.route("/pixel/<token>.gif")
def tracking_pixel(token):
    from flask import Response
    record_email_open(token, request)
    gif = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
           b"!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
           b"\x00\x00\x02\x02D\x01\x00;")
    return Response(gif, mimetype="image/gif",
                    headers={"Cache-Control": "no-cache, no-store"})


# ══════════════════════════════════════════════════════
# AUTH ROUTES — Email/Password
# ══════════════════════════════════════════════════════

@main_bp.route("/login", methods=["GET","POST"])
def login_page():
    if "user_id" in session:
        return redirect(url_for("main.home"))
    error = None
    if request.method == "POST":
        result = login_user(
            request.form.get("identifier",""),
            request.form.get("password","")
        )
        if result["success"]:
            _set_session(result["user"])
            return redirect(request.args.get("next") or url_for("main.dashboard"))
        error = result["error"]
    return render_template("login.html", error=error)


@main_bp.route("/register", methods=["GET","POST"])
def register_page():
    if "user_id" in session:
        return redirect(url_for("main.home"))
    error = None
    if request.method == "POST":
        p1 = request.form.get("password","")
        p2 = request.form.get("password2","")
        if p1 != p2:
            error = "Passwords do not match."
        else:
            result = register_user(
                request.form.get("username",""),
                request.form.get("email",""),
                p1
            )
            if result["success"]:
                _set_session(result["user"])
                return redirect(url_for("main.dashboard"))
            error = result["error"]
    return render_template("register.html", error=error)


@main_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login_page"))


# ══════════════════════════════════════════════════════
# OAUTH ROUTES — Google
# ══════════════════════════════════════════════════════

@main_bp.route("/auth/google")
def auth_google():
    oauth = current_app.extensions["oauth"]
    redirect_uri = url_for("main.auth_google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@main_bp.route("/auth/google/callback")
def auth_google_callback():
    try:
        oauth    = current_app.extensions["oauth"]
        token    = oauth.google.authorize_access_token()
        userinfo = token.get("userinfo") or oauth.google.userinfo()

        result = oauth_get_or_create(
            provider   = "google",
            oauth_id   = userinfo["sub"],
            email      = userinfo["email"],
            username   = userinfo.get("name", userinfo["email"].split("@")[0]),
            avatar_url = userinfo.get("picture"),
        )
        if result["success"]:
            _set_session(result["user"])
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.login_page") + "?error=oauth_failed")
    except Exception as e:
        print(f"Google OAuth error: {e}")
        return redirect(url_for("main.login_page") + "?error=oauth_failed")


# ══════════════════════════════════════════════════════
# OAUTH ROUTES — GitHub
# ══════════════════════════════════════════════════════

@main_bp.route("/auth/github")
def auth_github():
    oauth = current_app.extensions["oauth"]
    redirect_uri = url_for("main.auth_github_callback", _external=True)
    return oauth.github.authorize_redirect(redirect_uri)


@main_bp.route("/auth/github/callback")
def auth_github_callback():
    try:
        oauth    = current_app.extensions["oauth"]
        token    = oauth.github.authorize_access_token()
        profile  = oauth.github.get("user").json()

        # GitHub may hide email — fetch from emails endpoint
        email = profile.get("email")
        if not email:
            emails = oauth.github.get("user/emails").json()
            primary = next((e for e in emails if e.get("primary")), None)
            email = primary["email"] if primary else f"{profile['login']}@github.local"

        result = oauth_get_or_create(
            provider   = "github",
            oauth_id   = profile["id"],
            email      = email,
            username   = profile.get("login", "githubuser"),
            avatar_url = profile.get("avatar_url"),
        )
        if result["success"]:
            _set_session(result["user"])
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.login_page") + "?error=oauth_failed")
    except Exception as e:
        print(f"GitHub OAuth error: {e}")
        return redirect(url_for("main.login_page") + "?error=oauth_failed")


# ══════════════════════════════════════════════════════
# 404
# ══════════════════════════════════════════════════════

@main_bp.app_errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404
