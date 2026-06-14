"""
services/ai_service.py
3-Level Persona Hierarchy + Groq AI Integration

FIX LOG:
  - max_tokens raised to 7000 (was 3000 — caused truncated JSON)
  - Prompt schema simplified to reduce output length
  - Auto-retry with even simpler prompt on JSON parse failure
  - JSON repair utility for common truncation patterns
"""
import os, json, re
from groq import Groq

# ══════════════════════════════════════════════════════════
# PERSONA HIERARCHY
# ══════════════════════════════════════════════════════════
HIERARCHY = {
    "B2C": {
        "label": "B2C — Business to Consumer",
        "description": "Selling directly to individual people",
        "icon": "🛍️",
        "personas": {
            "Student": {
                "desc": "Career-focused, price-sensitive, loves peer validation and social proof",
                "icon": "🎓",
                "behaviors": ["Budget Sensitive", "Research-Oriented", "Impulsive"],
            },
            "Working Professional": {
                "desc": "Time-poor, values convenience, quality, and efficiency above all",
                "icon": "💼",
                "behaviors": ["Premium Buyer", "Research-Oriented", "Budget Sensitive"],
            },
            "Fitness Enthusiast": {
                "desc": "Health-obsessed, motivated by visible results and community belonging",
                "icon": "💪",
                "behaviors": ["Premium Buyer", "Impulsive", "Research-Oriented"],
            },
            "Tech Enthusiast": {
                "desc": "Early adopter, loves specs and innovation, influenced by tech communities",
                "icon": "⚡",
                "behaviors": ["Premium Buyer", "Impulsive", "Research-Oriented"],
            },
        },
    },
    "B2B": {
        "label": "B2B — Business to Business",
        "description": "Selling to companies, teams and decision-makers",
        "icon": "🏢",
        "personas": {
            "Startup Founder": {
                "desc": "Growth-obsessed, resource-constrained, moves fast, hates bureaucracy",
                "icon": "🚀",
                "behaviors": ["Budget Sensitive", "ROI-Focused", "Impulsive"],
            },
            "Small Business Owner": {
                "desc": "Risk-averse, values trust and reliability, needs proof before committing",
                "icon": "🏪",
                "behaviors": ["Budget Sensitive", "ROI-Focused", "Research-Oriented"],
            },
            "Enterprise Manager": {
                "desc": "Process-driven, needs stakeholder consensus, focuses on risk reduction",
                "icon": "🏦",
                "behaviors": ["ROI-Focused", "Research-Oriented", "Premium Buyer"],
            },
        },
    },
}

BEHAVIOR_DESCRIPTIONS = {
    "Budget Sensitive":  "Price-conscious. Highlight value, savings, and free trials.",
    "Premium Buyer":     "Expects quality and prestige. Use aspirational, exclusive language.",
    "Impulsive":         "Emotion-driven, acts fast. Use urgency, FOMO, strong CTAs.",
    "Research-Oriented": "Does homework before buying. Needs data, comparisons, trust signals.",
    "ROI-Focused":       "Must justify spend. Lead with numbers, payback period, efficiency gains.",
}


# ══════════════════════════════════════════════════════════
# PROMPT BUILDER  (compact schema = fewer tokens)
# ══════════════════════════════════════════════════════════

def build_system_prompt(category, persona, behavior):
    p    = HIERARCHY[category]["personas"][persona]
    b    = BEHAVIOR_DESCRIPTIONS.get(behavior, "")
    tone = ("Professional, ROI-focused, data-backed." 
            if category == "B2B" 
            else "Human, emotional, relatable. Use 'you' frequently.")

    # ── IMPORTANT: schema uses SHORT placeholders to keep output compact ──
    return f"""You are an elite AI sales strategist. Generate a complete sales funnel strategy.

BUYER PROFILE:
  Category : {category}
  Persona  : {persona} — {p['desc']}
  Behavior : {behavior} — {b}
  Tone     : {tone}

RULES:
- Return ONLY valid JSON. No markdown. No code fences. No explanation.
- Keep each text value CONCISE: 1-2 sentences max (except email body: 3-4 sentences).
- Be specific to the persona and behavior in every field.

JSON SCHEMA (fill every field — keep values SHORT):
{{
  "product": "<product name>",
  "category": "{category}",
  "persona": "{persona}",
  "behavior": "{behavior}",
  "agent_intro": "<1 sentence: how you would sell this to a {behavior} {persona}>",
  "profile_summary": "<2 sentences: this buyer's psychology and decision-making>",
  "funnel": [
    {{
      "stage": "Awareness",
      "goal": "<measurable goal, 1 sentence>",
      "insight": "<1 sentence: why this persona needs special treatment here>",
      "tactics": [
        {{
          "name": "<tactic name>",
          "description": "<1 sentence>",
          "implementation": ["<step 1>", "<step 2>", "<step 3>"],
          "timing": "<brief timing>",
          "platform": "<platform name>"
        }},
        {{
          "name": "<tactic 2 name>",
          "description": "<1 sentence>",
          "implementation": ["<step 1>", "<step 2>", "<step 3>"],
          "timing": "<brief timing>",
          "platform": "<platform name>"
        }}
      ],
      "kpis": ["<KPI 1>", "<KPI 2>", "<KPI 3>"],
      "content": {{
        "sales_message": "<1-2 sentences>",
        "email": {{"subject": "<subject line>", "body": "<3-4 sentences>"}},
        "marketing_text": "<2 sentences>",
        "hook": "<1 punchy opening line>"
      }}
    }},
    {{
      "stage": "Interest",
      "goal": "<1 sentence>",
      "insight": "<1 sentence>",
      "tactics": [{{"name":"<name>","description":"<1 sentence>","implementation":["<s1>","<s2>","<s3>"],"timing":"<brief>","platform":"<platform>"}},{{"name":"<name>","description":"<1 sentence>","implementation":["<s1>","<s2>","<s3>"],"timing":"<brief>","platform":"<platform>"}}],
      "kpis": ["<KPI 1>","<KPI 2>","<KPI 3>"],
      "content": {{"sales_message":"<1-2 sentences>","email":{{"subject":"<subject>","body":"<3-4 sentences>"}},"marketing_text":"<2 sentences>","hook":"<1 line>"}}
    }},
    {{
      "stage": "Consideration",
      "goal": "<1 sentence>",
      "insight": "<1 sentence>",
      "tactics": [{{"name":"<name>","description":"<1 sentence>","implementation":["<s1>","<s2>","<s3>"],"timing":"<brief>","platform":"<platform>"}},{{"name":"<name>","description":"<1 sentence>","implementation":["<s1>","<s2>","<s3>"],"timing":"<brief>","platform":"<platform>"}}],
      "kpis": ["<KPI 1>","<KPI 2>","<KPI 3>"],
      "content": {{"sales_message":"<1-2 sentences>","email":{{"subject":"<subject>","body":"<3-4 sentences>"}},"marketing_text":"<2 sentences>","hook":"<1 line>"}}
    }},
    {{
      "stage": "Conversion",
      "goal": "<1 sentence>",
      "insight": "<1 sentence>",
      "tactics": [{{"name":"<name>","description":"<1 sentence>","implementation":["<s1>","<s2>","<s3>"],"timing":"<brief>","platform":"<platform>"}},{{"name":"<name>","description":"<1 sentence>","implementation":["<s1>","<s2>","<s3>"],"timing":"<brief>","platform":"<platform>"}}],
      "kpis": ["<KPI 1>","<KPI 2>","<KPI 3>"],
      "content": {{"sales_message":"<1-2 sentences>","email":{{"subject":"<subject>","body":"<3-4 sentences>"}},"marketing_text":"<2 sentences>","hook":"<1 line>"}}
    }},
    {{
      "stage": "Retention",
      "goal": "<1 sentence>",
      "insight": "<1 sentence>",
      "tactics": [{{"name":"<name>","description":"<1 sentence>","implementation":["<s1>","<s2>","<s3>"],"timing":"<brief>","platform":"<platform>"}},{{"name":"<name>","description":"<1 sentence>","implementation":["<s1>","<s2>","<s3>"],"timing":"<brief>","platform":"<platform>"}}],
      "kpis": ["<KPI 1>","<KPI 2>","<KPI 3>"],
      "content": {{"sales_message":"<1-2 sentences>","email":{{"subject":"<subject>","body":"<3-4 sentences>"}},"marketing_text":"<2 sentences>","hook":"<1 line>"}}
    }}
  ],
  "quick_wins": [
    {{"action": "<action>", "impact": "<expected result>", "effort": "Low"}},
    {{"action": "<action>", "impact": "<expected result>", "effort": "Medium"}},
    {{"action": "<action>", "impact": "<expected result>", "effort": "Low"}}
  ],
  "avoid": [
    {{"mistake": "<mistake>", "reason": "<why it backfires>"}},
    {{"mistake": "<mistake>", "reason": "<why>"}}
  ],
  "optimization_tips": ["<tip 1>", "<tip 2>", "<tip 3>"]
}}

Return ONLY the JSON object. Start with {{ and end with }}. Nothing else."""


# ══════════════════════════════════════════════════════════
# JSON REPAIR  — fixes common LLM truncation patterns
# ══════════════════════════════════════════════════════════

def attempt_json_repair(raw: str) -> str:
    """
    Salvage truncated JSON by replaying the open-structure stack.
    Tracks a stack of { and [ as we parse, so we close them in
    the correct inner-to-outer order (e.g. }]} not ]}} ).
    """
    # Step 1: close any open string
    in_string = False
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == "\\" and in_string:
            i += 2
            continue
        if ch == '"':
            in_string = not in_string
        i += 1

    work = raw.rstrip()
    if in_string:
        work += '"' # close the unclosed string

    # Step 2: remove trailing comma before we add closers
    work = re.sub(r",\s*$", "", work.rstrip())

    # Step 3: build open-structure stack (tracks nesting order)
    stack     = []
    in_string = False
    i = 0
    while i < len(work):
        ch = work[i]
        if ch == "\\" and in_string:
            i += 2
            continue
        if ch == '"':
            in_string = not in_string
        elif not in_string:
            if ch in ("{", "["):
                stack.append(ch)
            elif ch == "}" and stack and stack[-1] == "{":
                stack.pop()
            elif ch == "]" and stack and stack[-1] == "[":
                stack.pop()
        i += 1

    # Step 4: close structures from innermost outward
    CLOSER = {"{": "}", "[": "]"}
    for opener in reversed(stack):
        work += CLOSER[opener]

    return work


# ══════════════════════════════════════════════════════════
# GROQ CALL — with retry logic
# ══════════════════════════════════════════════════════════

def _call_groq(client, system_prompt: str, user_prompt: str,
               max_tokens: int = 7000, temperature: float = 0.65) -> str:
    """Make one Groq API call and return raw text."""
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    raw = completion.choices[0].message.content.strip()

    # Strip markdown fences if model adds them anyway
    if raw.startswith("```"):
        parts = raw.split("```")
        raw   = parts[1] if len(parts) > 1 else parts[0]
        if raw.startswith("json"):
            raw = raw[4:]

    return raw.strip()


def sanitize_json(raw: str) -> str:
    """
    Fix the most common LLM JSON bug:
    Raw control characters (newline, tab, carriage-return) inside string values.
    JSON spec requires these as \\n \\t \\r — LLMs sometimes emit literal ones.
    Walks character-by-character, only escaping inside JSON strings.
    """
    result    = []
    in_string = False
    i         = 0
    ESCAPE_MAP = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}

    while i < len(raw):
        ch = raw[i]
        if in_string:
            if ch == "\\":
                result.append(ch)
                if i + 1 < len(raw):
                    i += 1
                    result.append(raw[i])
            elif ch == '"':
                in_string = False
                result.append(ch)
            elif ch in ESCAPE_MAP:
                result.append(ESCAPE_MAP[ch])
            else:
                result.append(ch)
        else:
            if ch == '"':
                in_string = True
            result.append(ch)
        i += 1

    return "".join(result)


def _parse_or_repair(raw: str):
    """
    3-stage parse pipeline:
      1. Direct parse (fast path)
      2. Sanitize control characters -> parse
      3. Sanitize + structural repair (truncation) -> parse
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    try:
        return json.loads(sanitize_json(raw))
    except json.JSONDecodeError:
        pass

    try:
        repaired = attempt_json_repair(sanitize_json(raw))
        return json.loads(repaired)
    except json.JSONDecodeError:
        # Last resort: strip everything after the last valid closing brace
        sanitized = sanitize_json(raw)
        last_brace = sanitized.rfind("}")
        if last_brace > 0:
            return json.loads(sanitized[:last_brace + 1])
        raise


# ══════════════════════════════════════════════════════════
# MAIN FUNCTION
# ══════════════════════════════════════════════════════════

def generate_sales_strategy(product: str, category: str,
                            persona: str, behavior: str) -> dict:
    """
    Generate a full sales strategy using Groq.
    Strategy: attempt 1 with full prompt → attempt 2 with tighter prompt.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "GROQ_API_KEY not set. Get your free key at https://console.groq.com",
        }

    try:
        client      = Groq(api_key=api_key)
        system_p    = build_system_prompt(category, persona, behavior)
        user_p      = (
            f"Generate the complete sales funnel strategy for:\n"
            f"Product: {product}\nCategory: {category}\n"
            f"Persona: {persona}\nBehavior: {behavior}\n\n"
            f"Keep every text field SHORT (1-2 sentences). "
            f"Output ONLY the JSON object."
        )

        # ── ATTEMPT 1: full generation ────────────────────
        raw = _call_groq(client, system_p, user_p, max_tokens=7000)

        try:
            data = _parse_or_repair(raw)
            return {"success": True, "data": data}

        except json.JSONDecodeError as e1:
            print(f"[ai_service] Attempt 1 JSON parse failed: {e1}")
            print(f"[ai_service] Raw tail (last 200 chars): ...{raw[-200:]}")

            # ── ATTEMPT 2: retry with even stricter instructions ──
            print("[ai_service] Retrying with strict short-output prompt…")
            strict_user = (
                f"Product: {product}, Persona: {persona} ({category}), Behavior: {behavior}.\n"
                f"Generate the sales funnel JSON. "
                f"CRITICAL: Keep ALL text values under 20 words each. "
                f"Email body max 3 sentences. "
                f"Output ONLY the JSON. Start with {{ end with }}."
            )
            raw2 = _call_groq(client, system_p, strict_user,
                              max_tokens=7000, temperature=0.5)
            try:
                data2 = _parse_or_repair(raw2)
                return {"success": True, "data": data2}
            except json.JSONDecodeError as e2:
                print(f"[ai_service] Attempt 2 also failed: {e2}")
                return {
                    "success": False,
                    "error": (
                        "The AI response was too long and got cut off both times. "
                        "Please try again — it usually works on the next attempt."
                    ),
                }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def get_hierarchy():    return HIERARCHY
def get_behaviors():    return BEHAVIOR_DESCRIPTIONS
