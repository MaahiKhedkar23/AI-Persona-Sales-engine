"""
services/strategy_service.py
Saves AI-generated strategy into the database.
"""
import json
from models import Session, Campaign, StrategyStage, GeneratedPost, Analytics, Recommendation
from services.analytics_service import generate_mock_analytics, generate_optimization_tips


STAGE_ORDER = ["Awareness", "Interest", "Consideration", "Conversion", "Retention"]


def save_campaign(product, category, persona, behavior, ai_data, analytics_data, opt_tips, user_id=None):
    """
    Persist a full campaign (strategy + posts + analytics + recommendations) to SQLite.
    Returns the new Campaign.id
    """
    db = Session()
    try:
        # 1. Campaign row
        campaign = Campaign(
            user_id=user_id,
            product_name=product,
            category=category,
            persona=persona,
            behavior=behavior,
        )
        db.add(campaign)
        db.flush()  # get campaign.id before committing

        # 2. Strategy stages
        for i, stage_data in enumerate(ai_data.get("funnel", [])):
            stage_name = stage_data.get("stage", f"Stage {i+1}")
            tactics    = stage_data.get("tactics", [])

            stage = StrategyStage(
                campaign_id         = campaign.id,
                stage_name          = stage_name,
                goal                = stage_data.get("goal", ""),
                insight             = stage_data.get("insight", ""),
                tactics             = json.dumps(tactics),
                kpis                = json.dumps(stage_data.get("kpis", [])),
                stage_order         = STAGE_ORDER.index(stage_name) if stage_name in STAGE_ORDER else i,
            )
            db.add(stage)

            # 3. Generated posts for this stage
            content = stage_data.get("content", {})
            for ctype, value in [
                ("sales_message",  content.get("sales_message", "")),
                ("marketing_text", content.get("marketing_text", "")),
                ("hook",           content.get("hook", "")),
            ]:
                if value:
                    db.add(GeneratedPost(
                        campaign_id=campaign.id, stage_name=stage_name,
                        content_type=ctype, content=value,
                    ))

            # Email
            email = content.get("email", {})
            if email.get("body"):
                db.add(GeneratedPost(
                    campaign_id=campaign.id, stage_name=stage_name,
                    content_type="email",
                    subject=email.get("subject", ""),
                    content=email.get("body", ""),
                ))

        # 4. Analytics
        db.add(Analytics(
            campaign_id      = campaign.id,
            reach            = analytics_data["reach"],
            engagement       = analytics_data["engagement"],
            clicks           = analytics_data["clicks"],
            conversion_score = analytics_data["conversion_score"],
            progress         = analytics_data["progress"],
            tactic_data      = json.dumps(analytics_data["tactic_data"]),
        ))

        # 5. Recommendations
        for tip in opt_tips:
            db.add(Recommendation(
                campaign_id         = campaign.id,
                recommendation_text = f"{tip['title']}: {tip['text']}",
                priority            = tip.get("priority", "medium"),
            ))

        db.commit()
        return campaign.id

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_all_campaigns(user_id=None):
    """Return campaigns. If user_id given, only that user's campaigns."""
    db = Session()
    try:
        q = db.query(Campaign).order_by(Campaign.created_at.desc())
        if user_id is not None:
            q = q.filter_by(user_id=user_id)
        return [c.to_dict() for c in q.all()]
    finally:
        db.close()


def get_campaign_full(campaign_id):
    """Return complete campaign data as dict (for re-display)."""
    db = Session()
    try:
        c = db.query(Campaign).filter_by(id=campaign_id).first()
        if not c:
            return None

        stages = db.query(StrategyStage).filter_by(campaign_id=campaign_id).order_by(StrategyStage.stage_order).all()
        posts  = db.query(GeneratedPost).filter_by(campaign_id=campaign_id).all()
        an     = db.query(Analytics).filter_by(campaign_id=campaign_id).first()
        recs   = db.query(Recommendation).filter_by(campaign_id=campaign_id).all()

        stage_list = []
        for s in stages:
            stage_posts = [p for p in posts if p.stage_name == s.stage_name]
            content     = {}
            for p in stage_posts:
                if p.content_type == "email":
                    content["email"] = {"subject": p.subject or "", "body": p.content}
                else:
                    content[p.content_type] = p.content

            stage_list.append({
                "stage":   s.stage_name,
                "goal":    s.goal,
                "insight": s.insight,
                "tactics": json.loads(s.tactics or "[]"),
                "kpis":    json.loads(s.kpis    or "[]"),
                "content": content,
            })

        tactic_data = json.loads(an.tactic_data or "[]") if an else []
        opt_tips    = generate_optimization_tips(c.persona, c.behavior, tactic_data)

        return {
            "campaign": c.to_dict(),
            "funnel":   stage_list,
            "analytics": {
                "reach":            an.reach            if an else 0,
                "engagement":       an.engagement       if an else 0,
                "clicks":           an.clicks           if an else 0,
                "conversion_score": an.conversion_score if an else 0,
                "progress":         an.progress         if an else 0,
                "tactic_data":      tactic_data,
            } if an else {},
            "recommendations": [{"text": r.recommendation_text, "priority": r.priority} for r in recs],
            "optimization_tips": opt_tips,
        }
    finally:
        db.close()


def delete_campaign(campaign_id):
    db = Session()
    try:
        c = db.query(Campaign).filter_by(id=campaign_id).first()
        if c:
            db.delete(c)
            db.commit()
            return True
        return False
    finally:
        db.close()
