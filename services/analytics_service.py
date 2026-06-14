"""
services/analytics_service.py
Generates realistic mock analytics and AI optimization recommendations.
"""
import random, json
from datetime import datetime

# Tactic performance profiles per behavior type
BEHAVIOR_PERFORMANCE = {
    "Budget Sensitive":  {"social": (70,90), "email": (60,80), "paid": (40,65), "content": (65,85)},
    "Premium Buyer":     {"social": (55,75), "email": (70,90), "paid": (75,92), "content": (60,80)},
    "Impulsive":         {"social": (80,95), "email": (50,70), "paid": (72,88), "content": (45,65)},
    "Research-Oriented": {"social": (45,65), "email": (75,90), "paid": (55,72), "content": (80,95)},
    "ROI-Focused":       {"social": (40,60), "email": (70,88), "paid": (60,80), "content": (75,92)},
}

STAGE_WEIGHTS = {
    "Awareness": 0.95, "Interest": 0.80,
    "Consideration": 0.65, "Conversion": 0.45, "Retention": 0.60,
}

TACTIC_CHANNELS = [
    "Instagram Reels", "LinkedIn Posts", "Email Drip",
    "Google Ads", "YouTube Shorts", "Twitter/X Threads",
    "Blog Content", "Webinar", "Retargeting Ads", "WhatsApp Broadcast",
]


def generate_mock_analytics(category, persona, behavior):
    """Generate realistic mock campaign analytics."""
    perf = BEHAVIOR_PERFORMANCE.get(behavior, {"social":(60,80),"email":(60,80),"paid":(60,80),"content":(60,80)})

    base_reach       = random.randint(8_000,  45_000) if category == "B2C" else random.randint(1_500, 12_000)
    engagement_rate  = round(random.uniform(2.5, 8.4), 1)
    clicks           = int(base_reach * engagement_rate / 100 * random.uniform(0.3, 0.7))
    conversion_score = round(random.uniform(38, 82), 1)
    progress         = round(random.uniform(25, 78), 1)

    # Per-tactic table (6 tactics)
    channels  = random.sample(TACTIC_CHANNELS, 6)
    statuses  = ["Active", "Active", "Paused", "Active", "Draft", "Active"]
    tactic_data = []
    for i, ch in enumerate(channels):
        channel_type = "social" if any(x in ch for x in ["Instagram","LinkedIn","Twitter","YouTube"]) \
                       else "email" if "Email" in ch or "WhatsApp" in ch \
                       else "paid" if "Ads" in ch or "Retarget" in ch else "content"
        lo, hi = perf[channel_type]
        score  = random.randint(lo, hi)
        tactic_data.append({
            "tactic":  ch,
            "status":  statuses[i],
            "score":   score,
            "label":   "🔥 High" if score >= 75 else "⚡ Medium" if score >= 50 else "❄️ Low",
            "trend":   random.choice(["↑", "↑", "→", "↓"]),
        })

    # Weekly reach trend (7 days)
    trend = []
    val = base_reach // 7
    for d in range(7):
        val = max(200, int(val * random.uniform(0.85, 1.25)))
        trend.append({"day": f"D{d+1}", "reach": val})

    return {
        "reach":            base_reach,
        "engagement":       engagement_rate,
        "clicks":           clicks,
        "conversion_score": conversion_score,
        "progress":         progress,
        "tactic_data":      tactic_data,
        "trend":            trend,
        "generated_at":     datetime.utcnow().isoformat(),
    }


def generate_optimization_tips(persona, behavior, tactic_data):
    """Generate AI optimization recommendations based on analytics."""
    sorted_tactics = sorted(tactic_data, key=lambda x: x["score"], reverse=True)
    best   = sorted_tactics[0]  if sorted_tactics else None
    worst  = sorted_tactics[-1] if sorted_tactics else None

    tips = []

    if best:
        tips.append({
            "priority": "high",
            "icon": "🚀",
            "title": f"Double down on {best['tactic']}",
            "text": f"{best['tactic']} is your top performer at {best['score']}% efficiency. "
                    f"Increase posting frequency by 40% and A/B test 2-3 variations of your best-performing content.",
        })

    if worst and worst["score"] < 50:
        tips.append({
            "priority": "medium",
            "icon": "⚠️",
            "title": f"Reassess {worst['tactic']}",
            "text": f"{worst['tactic']} is underperforming at {worst['score']}%. "
                    f"Either revise the content angle or reallocate budget to higher-performing channels.",
        })

    if behavior == "Budget Sensitive":
        tips.append({
            "priority": "high",
            "icon": "💰",
            "title": "Lead with value, not price",
            "text": f"Your {persona} audience is price-conscious. "
                    "Add a value-stack section to all content showing the total worth of what they get.",
        })
    elif behavior == "Impulsive":
        tips.append({
            "priority": "high",
            "icon": "⏰",
            "title": "Add countdown urgency",
            "text": "Impulsive buyers respond to real deadlines. "
                    "Add 24-hour flash sale mechanics and countdown timers to your highest-traffic landing pages.",
        })
    elif behavior == "Research-Oriented":
        tips.append({
            "priority": "medium",
            "icon": "📊",
            "title": "Publish comparison content",
            "text": f"{persona}s who research do deep comparison shopping. "
                    "Create a detailed comparison page vs. top 3 competitors and promote it heavily.",
        })
    elif behavior == "ROI-Focused":
        tips.append({
            "priority": "high",
            "icon": "📈",
            "title": "Build an ROI calculator",
            "text": "ROI-focused buyers need to justify spend internally. "
                    "A simple interactive ROI calculator on your landing page can increase conversion by 30-45%.",
        })

    tips.append({
        "priority": "low",
        "icon": "🔄",
        "title": "Retargeting window optimization",
        "text": "Set up 7-day and 30-day retargeting audiences separately. "
                "Use different creative for each window — urgency for 7-day, social proof for 30-day.",
    })

    return tips
