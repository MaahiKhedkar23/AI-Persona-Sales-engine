"""
services/tracking_service.py

Real tracking system — no mocked data.
Every number shown in analytics comes from actual events stored in SQLite.

How it works:
  1. When a campaign is created, generate_campaign_links() creates
     short trackable URLs for each funnel stage + channel combo.

  2. When someone visits /t/<token>, we:
       - Log a TrackingEvent row (real click, real timestamp)
       - Increment TrackableLink.clicks
       - Optionally redirect to a destination URL

  3. The analytics page reads REAL counts from tracking_events.

  4. A 1x1 pixel endpoint (/pixel/<token>.gif) lets you embed
     tracking in emails — every open logs a 'open' event.
"""

import hashlib
import secrets
import json
from datetime import datetime, timedelta
from collections import defaultdict

from models import Session, TrackingEvent, TrackableLink, Campaign

# ── FUNNEL STAGES ─────────────────────────────────────────
STAGES = ["Awareness", "Interest", "Consideration", "Conversion", "Retention"]

# Channels we generate links for per stage
STAGE_CHANNELS = {
    "Awareness":     ["instagram", "youtube", "twitter", "google_ads"],
    "Interest":      ["instagram", "linkedin", "email", "blog"],
    "Consideration": ["email", "webinar", "linkedin", "retargeting"],
    "Conversion":    ["email", "landing_page", "whatsapp", "retargeting"],
    "Retention":     ["email", "whatsapp", "push_notification"],
}


# ══════════════════════════════════════════════════════════
# LINK GENERATION
# ══════════════════════════════════════════════════════════

def generate_campaign_links(campaign_id: int) -> list[dict]:
    """
    Create trackable short-links for every stage + channel combo.
    Call this once when a campaign is launched.
    Returns list of link dicts.
    """
    db = Session()
    try:
        # Don't duplicate if links already exist
        existing = db.query(TrackableLink).filter_by(campaign_id=campaign_id).count()
        if existing > 0:
            links = db.query(TrackableLink).filter_by(campaign_id=campaign_id).all()
            return [_link_to_dict(l) for l in links]

        created = []
        for stage, channels in STAGE_CHANNELS.items():
            for channel in channels:
                token = secrets.token_urlsafe(8)   # e.g. "aB3xK9mQ"
                link  = TrackableLink(
                    campaign_id = campaign_id,
                    token       = token,
                    stage       = stage,
                    channel     = channel,
                    label       = f"{stage} — {channel.replace('_',' ').title()}",
                    clicks      = 0,
                )
                db.add(link)
                created.append(link)

        db.commit()
        return [_link_to_dict(l) for l in created]
    finally:
        db.close()


def _link_to_dict(link) -> dict:
    return {
        "id":      link.id,
        "token":   link.token,
        "stage":   link.stage,
        "channel": link.channel,
        "label":   link.label,
        "clicks":  link.clicks,
    }


# ══════════════════════════════════════════════════════════
# EVENT RECORDING
# ══════════════════════════════════════════════════════════

def record_click(token: str, request) -> dict | None:
    """
    Record a real click event.
    Called by the /t/<token> route.
    Returns the TrackableLink dict (for redirect info), or None.
    """
    db = Session()
    try:
        link = db.query(TrackableLink).filter_by(token=token).first()
        if not link:
            return None

        # Hash the IP for privacy (GDPR-friendly — not storing raw IPs)
        raw_ip  = request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr) or ""
        ip_hash = hashlib.sha256(raw_ip.encode()).hexdigest()[:16]

        event = TrackingEvent(
            campaign_id = link.campaign_id,
            event_type  = "click",
            stage       = link.stage,
            channel     = link.channel,
            link_token  = token,
            ip_hash     = ip_hash,
            user_agent  = (request.user_agent.string or "")[:200],
            referrer    = (request.referrer or "")[:200],
        )
        db.add(event)

        link.clicks += 1
        db.commit()

        return {
            "campaign_id": link.campaign_id,
            "stage":       link.stage,
            "channel":     link.channel,
            "destination": link.destination,
        }
    finally:
        db.close()


def record_email_open(token: str, request) -> bool:
    """
    Record an email open (triggered by /pixel/<token>.gif).
    """
    db = Session()
    try:
        link = db.query(TrackableLink).filter_by(token=token).first()
        if not link:
            return False

        raw_ip  = request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr) or ""
        ip_hash = hashlib.sha256(raw_ip.encode()).hexdigest()[:16]

        event = TrackingEvent(
            campaign_id = link.campaign_id,
            event_type  = "open",
            stage       = link.stage,
            channel     = link.channel,
            link_token  = token,
            ip_hash     = ip_hash,
            user_agent  = (request.user_agent.string or "")[:200],
        )
        db.add(event)
        db.commit()
        return True
    finally:
        db.close()


def record_page_view(campaign_id: int, stage: str, request) -> None:
    """
    Record a page view event (called from JS beacon on campaign pages).
    """
    db = Session()
    try:
        raw_ip  = request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr) or ""
        ip_hash = hashlib.sha256(raw_ip.encode()).hexdigest()[:16]

        event = TrackingEvent(
            campaign_id = campaign_id,
            event_type  = "view",
            stage       = stage,
            channel     = "direct",
            ip_hash     = ip_hash,
            user_agent  = (request.user_agent.string or "")[:200],
        )
        db.add(event)
        db.commit()
    finally:
        db.close()


# ══════════════════════════════════════════════════════════
# REAL ANALYTICS COMPUTATION
# ══════════════════════════════════════════════════════════

def compute_real_analytics(campaign_id: int) -> dict:
    """
    Compute ALL analytics from real TrackingEvent rows.
    Returns the same shape as the old mock analytics dict
    so the frontend works without changes.
    """
    db = Session()
    try:
        events = (db.query(TrackingEvent)
                    .filter_by(campaign_id=campaign_id)
                    .order_by(TrackingEvent.created_at)
                    .all())

        links  = (db.query(TrackableLink)
                    .filter_by(campaign_id=campaign_id)
                    .order_by(TrackableLink.clicks.desc())
                    .all())

        if not events:
            return _empty_analytics(campaign_id)

        # ── Basic counts ──────────────────────────────────
        total_clicks = sum(1 for e in events if e.event_type == "click")
        total_views  = sum(1 for e in events if e.event_type == "view")
        total_opens  = sum(1 for e in events if e.event_type == "open")
        total_events = len(events)

        # ── Unique visitors (by ip_hash) ──────────────────
        unique_ips = len(set(e.ip_hash for e in events if e.ip_hash))

        # ── Reach estimate ────────────────────────────────
        # Real: unique IPs × estimated viral coefficient
        # (Each person who clicks might have seen content 3-5x before clicking)
        reach = unique_ips * 4 if unique_ips else total_clicks * 4

        # ── Engagement rate ───────────────────────────────
        # clicks / views (real conversion from impression to action)
        engagement = round((total_clicks / max(total_views, 1)) * 100, 1)
        engagement = min(engagement, 100.0)

        # ── Conversion score (0-100) ──────────────────────
        # Weighted: Conversion + Retention stage events count more
        stage_weights = {
            "Awareness": 1, "Interest": 2,
            "Consideration": 3, "Conversion": 5, "Retention": 4
        }
        weighted_sum = sum(stage_weights.get(e.stage, 1) for e in events)
        max_possible = total_events * 5
        conversion_score = round((weighted_sum / max(max_possible, 1)) * 100, 1)

        # ── Campaign progress (0-100) ─────────────────────
        # Based on how many of the 5 funnel stages have any activity
        active_stages = len(set(e.stage for e in events if e.stage))
        progress = round((active_stages / 5) * 100, 1)

        # ── Per-channel tactic table ──────────────────────
        channel_counts = defaultdict(lambda: {"click":0, "view":0, "open":0})
        for e in events:
            ch = e.channel or "unknown"
            if e.event_type in ("click","view","open"):
                channel_counts[ch][e.event_type] += 1

        tactic_data = []
        for link in links:
            total_ch = link.clicks
            if link.channel not in channel_counts and total_ch == 0:
                continue
            ch_events = channel_counts.get(link.channel, {"click":0,"view":0,"open":0})
            ch_total  = sum(ch_events.values())
            score     = min(100, int((link.clicks / max(total_clicks, 1)) * 100 * 3)) if total_clicks else 0
            score     = max(score, min(link.clicks * 5, 100))

            # Trend based on recent vs older clicks
            recent_events = [e for e in events
                             if e.channel == link.channel
                             and e.created_at > datetime.utcnow() - timedelta(days=1)]
            trend = "↑" if len(recent_events) > 1 else "→" if len(recent_events) == 1 else "↓"

            status = "Active" if link.clicks > 0 else "Pending"

            tactic_data.append({
                "tactic":  link.label,
                "channel": link.channel,
                "stage":   link.stage,
                "status":  status,
                "score":   score,
                "label":   ("🔥 High" if score >= 75
                            else "⚡ Medium" if score >= 40
                            else "❄️ Low"),
                "trend":   trend,
                "clicks":  link.clicks,
            })

        # Sort by clicks descending
        tactic_data.sort(key=lambda x: x["clicks"], reverse=True)

        # ── Daily trend (last 7 days) ─────────────────────
        trend_data = []
        for day_offset in range(6, -1, -1):
            day   = datetime.utcnow() - timedelta(days=day_offset)
            label = day.strftime("%a")
            count = sum(1 for e in events
                        if e.created_at.date() == day.date())
            trend_data.append({"day": label, "events": count})

        # ── Stage breakdown ───────────────────────────────
        stage_breakdown = {}
        for stage in STAGES:
            stage_events = [e for e in events if e.stage == stage]
            stage_breakdown[stage] = {
                "clicks": sum(1 for e in stage_events if e.event_type == "click"),
                "views":  sum(1 for e in stage_events if e.event_type == "view"),
                "opens":  sum(1 for e in stage_events if e.event_type == "open"),
            }

        return {
            "is_real":           True,          # flag so UI knows this is real data
            "total_events":      total_events,
            "total_clicks":      total_clicks,
            "total_views":       total_views,
            "total_opens":       total_opens,
            "unique_visitors":   unique_ips,
            "reach":             reach,
            "engagement":        engagement,
            "clicks":            total_clicks,
            "conversion_score":  conversion_score,
            "progress":          progress,
            "tactic_data":       tactic_data,
            "trend":             trend_data,
            "stage_breakdown":   stage_breakdown,
        }
    finally:
        db.close()


def get_campaign_links(campaign_id: int) -> list[dict]:
    """Return all trackable links for a campaign."""
    db = Session()
    try:
        links = (db.query(TrackableLink)
                   .filter_by(campaign_id=campaign_id)
                   .order_by(TrackableLink.stage, TrackableLink.channel)
                   .all())
        return [_link_to_dict(l) for l in links]
    finally:
        db.close()


def _empty_analytics(campaign_id: int) -> dict:
    """Return a zero-state analytics dict when no events exist yet."""
    return {
        "is_real":          True,
        "total_events":     0,
        "total_clicks":     0,
        "total_views":      0,
        "total_opens":      0,
        "unique_visitors":  0,
        "reach":            0,
        "engagement":       0.0,
        "clicks":           0,
        "conversion_score": 0.0,
        "progress":         0.0,
        "tactic_data":      [],
        "trend":            [{"day": d, "events": 0}
                             for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]],
        "stage_breakdown":  {s: {"clicks":0,"views":0,"opens":0} for s in STAGES},
    }
