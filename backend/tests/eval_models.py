"""
Model Evaluation Script
Runs all 10 scenarios from docs/evaluation.md against two models and generates a comparison report.

Usage:
    python3 backend/tests/eval_models.py

The two models are read from docs/evaluation.md (qwen/qwen3-5-27b and google/gemma-4-31b-it).
API key and base URL are loaded from .env.

Output: docs/evaluation_report_<timestamp>.md
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.app.config import settings

# ── Models to compare ────────────────────────────────────────────────────────

MODELS = [
    "qwen/qwen3-5-27b",
    "google/gemma-4-31b-it",
]

# ── System prompts ────────────────────────────────────────────────────────────

RECOMMENDATION_SYSTEM_PROMPT = """You are ALP, the After Work Agent for VNG Starters.

Your job is to help employees find after-work activities they'll actually enjoy — not to be a search engine or a notification system.

You know about the user: their department, interests, who they've joined activities with before, and how they've been spending their after-work time. Use that to make every conversation feel personal, not generic.

## Personality

- Warm, direct, and low-key enthusiastic — like a colleague who genuinely knows what's on
- Never corporate, never formal, never robotic
- Honest: if you don't have enough context, say so and ask
- Curious: if the user's message is vague, ask one good follow-up instead of guessing

## Conversation flow

You are in a conversation, not a query-response loop.

**When the user's intent is clear** — recommend directly. No need to ask more questions.
**When the user's intent is vague** — ask ONE focused question to narrow it down.
**When the user mentions how they're feeling** — acknowledge it first, then recommend.
**When recommending:** lead with the best 1-2 options, describe naturally, mention social context, end with a call to action.

## Style rules

Always: use contractions, be specific (times, locations), reference what you know about the user.
Never: mention scores/percentages, use database language, say "I found X activities", list more than 3-4 options, ask multiple questions at once.

## Grounding rules

Only reference information that exists in the data provided. Do not invent past habits, past attendance, or preferences not in the data.

## Recommendation principles

1. Match available activities to current user intent
2. Use participation history over declared interests when there's enough history (3+ activities)
3. Use declared interests when history is thin
4. Factor in social context
5. Prefer variety over repetition if the user is in a routine"""

CONVERSATION_STARTER_SYSTEM_PROMPT = """You are ALP, the After Work Agent for VNG Starters.
The user just opened the app. Your job is to start a warm, brief conversation.

If there is unresolved participation from yesterday (no record of what the user did), ask about it first before recommending anything.

Rules:
- Be warm and brief (1-2 sentences max for the opener)
- If asking about yesterday, ask naturally — not like a form
- Do not recommend activities until you know if participation needs to be collected
- Never invent past behavior"""

# ── Scenario definitions ──────────────────────────────────────────────────────

def build_rec_prompt(user_name, department, interests, history_note, cold_start,
                     message, intent, activities, discovery_note="", routine_note=""):
    activities_str = ""
    for i, a in enumerate(activities, 1):
        activities_str += f"\n{i}. {a['title']} — {a['time']}, {a['location']}"
        if a.get("spots"):
            activities_str += f" ({a['spots']})"
        if a.get("note"):
            activities_str += f"\n   Note: {a['note']}"

    interests_str = ", ".join(interests) if interests else "none declared"
    memories_str = "\n".join(f"- {h}" for h in history_note) if history_note else "none"

    return f"""User: {user_name} (Department: {department})
User's message: "{message}"
Intent: {intent}
Cold start (no activity history): {cold_start}
{routine_note}
Known interests: {interests_str}
Participation history notes:
{memories_str}
Habit insight: {discovery_note or "none"}

Ranked activities (best first):
{activities_str}

Write the response. Be conversational, specific, and brief. Do not mention scores."""


SCENARIOS = [
    {
        "id": 1,
        "title": "Cold Start User",
        "type": "recommendation",
        "system_prompt": RECOMMENDATION_SYSTEM_PROMPT,
        "user_prompt": build_rec_prompt(
            user_name="Minh Tran", department="TEP",
            interests=["Football", "AI"],
            history_note=[],
            cold_start=True,
            message="What should I do tonight?",
            intent="exploration",
            activities=[
                {"title": "Football Match", "time": "18:00", "location": "Rooftop Field", "spots": "2 slots left"},
                {"title": "AI Sharing Session", "time": "18:30", "location": "Meeting Room B"},
                {"title": "Yoga Class", "time": "19:00", "location": "Studio A"},
            ],
            discovery_note="No participation history yet.",
        ),
        "forbidden": ["you usually", "you attended", "you always", "last time you", "you've been"],
        "required": [],
        "check_description": "Must not invent participation history. Should acknowledge cold start.",
    },
    {
        "id": 2,
        "title": "Missing Participation Follow-up (App Open)",
        "type": "conversation_starter",
        "system_prompt": CONVERSATION_STARTER_SYSTEM_PROMPT,
        "user_prompt": """User: Minh Tran (Department: TEP)
Interests: Football
Situation: User just opened the app. There is NO participation record for yesterday evening.
Available activities tonight: Football Match (18:00), Yoga Class (19:00)

Generate the opening message. Ask about yesterday first — do not immediately recommend tonight's activities.""",
        "forbidden": ["here are activities", "tonight there's", "i found", "football match at"],
        "required": ["yesterday"],
        "check_description": "Must ask about yesterday before recommending. Should not jump to tonight's activities.",
    },
    {
        "id": 3,
        "title": "Exercise Intent",
        "type": "recommendation",
        "system_prompt": RECOMMENDATION_SYSTEM_PROMPT,
        "user_prompt": build_rec_prompt(
            user_name="Minh Tran", department="TEP",
            interests=["Football"],
            history_note=[],
            cold_start=True,
            message="I want to exercise tonight.",
            intent="exercise",
            activities=[
                {"title": "Football Match", "time": "18:00", "location": "Rooftop Field"},
                {"title": "Yoga Class", "time": "19:00", "location": "Studio A"},
                {"title": "AI Sharing Session", "time": "18:30", "location": "Meeting Room B"},
            ],
        ),
        "forbidden": ["ai sharing"],
        "required": ["football", "yoga"],
        "check_description": "Must prioritize Football and Yoga. Should not lead with AI Sharing.",
    },
    {
        "id": 4,
        "title": "Learning Intent",
        "type": "recommendation",
        "system_prompt": RECOMMENDATION_SYSTEM_PROMPT,
        "user_prompt": build_rec_prompt(
            user_name="Minh Tran", department="TEP",
            interests=["AI"],
            history_note=[],
            cold_start=True,
            message="I want to learn something new tonight.",
            intent="learning",
            activities=[
                {"title": "Football Match", "time": "18:00", "location": "Rooftop Field"},
                {"title": "Yoga Class", "time": "19:00", "location": "Studio A"},
                {"title": "AI Sharing Session", "time": "18:30", "location": "Meeting Room B"},
            ],
        ),
        "forbidden": [],
        "required": ["ai sharing"],
        "check_description": "Must lead with AI Sharing Session. Should explain why it matches learning intent.",
    },
    {
        "id": 5,
        "title": "Relaxation Intent (Tired User)",
        "type": "recommendation",
        "system_prompt": RECOMMENDATION_SYSTEM_PROMPT,
        "user_prompt": build_rec_prompt(
            user_name="Minh Tran", department="TEP",
            interests=["Yoga"],
            history_note=[],
            cold_start=True,
            message="I'm feeling tired today.",
            intent="relaxation",
            activities=[
                {"title": "Football Match", "time": "18:00", "location": "Rooftop Field"},
                {"title": "Yoga Class", "time": "19:00", "location": "Studio A"},
                {"title": "Coffee Chat", "time": "17:30", "location": "Pantry"},
            ],
        ),
        "forbidden": [],
        "required": ["yoga", "coffee"],
        "check_description": "Must acknowledge tiredness first. Should not lead with Football. Should recommend Yoga or Coffee Chat.",
    },
    {
        "id": 6,
        "title": "Full Activity Excluded",
        "type": "recommendation",
        "system_prompt": RECOMMENDATION_SYSTEM_PROMPT,
        "user_prompt": build_rec_prompt(
            user_name="Minh Tran", department="TEP",
            interests=["Football"],
            history_note=[],
            cold_start=True,
            message="What should I do tonight?",
            intent="exploration",
            activities=[
                {"title": "Yoga Class", "time": "19:00", "location": "Studio A"},
            ],
            discovery_note="Football Match is full (inactive) and has been excluded from candidates.",
        ),
        "forbidden": ["football match", "football at", "join the football"],
        "required": ["yoga"],
        "check_description": "Football is full — must NOT recommend it. Should recommend Yoga.",
    },
    {
        "id": 7,
        "title": "Routine Trap — User Wants New Experiences",
        "type": "recommendation",
        "system_prompt": RECOMMENDATION_SYSTEM_PROMPT,
        "user_prompt": build_rec_prompt(
            user_name="Minh Tran", department="TEP",
            interests=["Football"],
            history_note=["Joined Football Match 10 times in the past month"],
            cold_start=False,
            message="I want to try something different.",
            intent="exploration",
            activities=[
                {"title": "Football Match", "time": "18:00", "location": "Rooftop Field"},
                {"title": "AI Sharing Session", "time": "18:30", "location": "Meeting Room B"},
                {"title": "Board Game Night", "time": "19:00", "location": "Pantry"},
            ],
            discovery_note="User has joined Football 10 times in a row — strong routine trap signal.",
            routine_note="The user has been doing Football repeatedly. Nudge them toward something different — one sentence, natural, no drama.",
        ),
        "forbidden": [],
        "required": [],
        "required_any": ["ai sharing", "board game"],
        "check_description": "Must suggest at least one of: AI Sharing Session, Board Game Night. Should not only recommend Football.",
    },
    {
        "id": 8,
        "title": "Networking Intent",
        "type": "recommendation",
        "system_prompt": RECOMMENDATION_SYSTEM_PROMPT,
        "user_prompt": build_rec_prompt(
            user_name="Minh Tran", department="TEP",
            interests=["Networking"],
            history_note=[],
            cold_start=True,
            message="I want to meet new people.",
            intent="networking",
            activities=[
                {"title": "Football Match", "time": "18:00", "location": "Rooftop Field",
                 "note": "3 people from BIZ team already signed up"},
                {"title": "AI Sharing Session", "time": "18:30", "location": "Meeting Room B",
                 "note": "Mixed group from 4 different departments"},
                {"title": "Coffee Chat", "time": "17:30", "location": "Pantry",
                 "note": "Open to all, 2 slots left"},
            ],
        ),
        "forbidden": [],
        "required": [],
        "check_description": "Should highlight social/networking value. Should mention who's going (cross-department context).",
    },
    {
        "id": 9,
        "title": "Normal App Open (No Missing Participation)",
        "type": "conversation_starter",
        "system_prompt": CONVERSATION_STARTER_SYSTEM_PROMPT,
        "user_prompt": """User: Minh Tran (Department: TEP)
Interests: Football, AI
Situation: User just opened the app. Participation history is up to date — no missing records.
Available activities tonight: Football Match (18:00), AI Sharing Session (18:30)

Generate a warm, brief opening message to engage the user.""",
        "forbidden": ["what did you do yesterday", "yesterday evening"],
        "required": [],
        "check_description": "Participation is resolved — must NOT ask about yesterday. Should start a contextual conversation.",
    },
    {
        "id": 10,
        "title": "Hallucination Test — Football Interest, No Football Available",
        "type": "recommendation",
        "system_prompt": RECOMMENDATION_SYSTEM_PROMPT,
        "user_prompt": build_rec_prompt(
            user_name="Minh Tran", department="TEP",
            interests=["Football"],
            history_note=[],
            cold_start=True,
            message="What should I do tonight?",
            intent="exploration",
            activities=[
                {"title": "Yoga Class", "time": "19:00", "location": "Studio A"},
            ],
            discovery_note="Only Yoga is available tonight. No football activity exists.",
        ),
        "forbidden": ["football match", "football at", "football session", "football game",
                      "you usually play", "you've played", "you attended"],
        "required": ["yoga"],
        "check_description": "CRITICAL: Must only recommend Yoga. Must NOT invent a Football activity or past football attendance.",
    },
]

# ── LLM caller ────────────────────────────────────────────────────────────────

def call_model(model_name: str, system_prompt: str, user_prompt: str) -> str:
    # qwen3 is a thinking model — it generates internal reasoning tokens before the actual
    # response. A simple "Hello" can consume ~1100 tokens just for thinking, so we need a
    # large budget. gemma uses far fewer tokens but the higher limit doesn't hurt.
    max_tokens = 8000 if "qwen3" in model_name else 1000

    client = ChatOpenAI(
        openai_api_base=settings.AI_PLATFORM_API_BASE,
        openai_api_key=settings.AI_PLATFORM_API_KEY,
        model_name=model_name,
        temperature=0.2,
        max_tokens=max_tokens,
        timeout=60.0,
    )
    try:
        response = client.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        return response.content.strip()
    except Exception as e:
        return f"[ERROR: {e}]"

# ── Auto-checker ──────────────────────────────────────────────────────────────

def check_response(response: str, forbidden: list, required: list, required_any: list = None) -> dict:
    text = response.lower()
    failed_forbidden = [f for f in forbidden if f.lower() in text]
    failed_required = [r for r in required if r.lower() not in text]
    failed_required_any = (
        required_any
        if required_any and not any(r.lower() in text for r in required_any)
        else []
    )
    passed = not failed_forbidden and not failed_required and not failed_required_any
    return {
        "passed": passed,
        "failed_forbidden": failed_forbidden,
        "failed_required": failed_required,
        "failed_required_any": failed_required_any,
    }

# ── Report builder ────────────────────────────────────────────────────────────

def score_line(check: dict) -> str:
    if check["passed"]:
        return "PASS"
    parts = []
    if check["failed_forbidden"]:
        parts.append(f"HALLUCINATION: mentioned {check['failed_forbidden']}")
    if check["failed_required"]:
        parts.append(f"MISSING: expected {check['failed_required']}")
    if check.get("failed_required_any"):
        parts.append(f"MISSING: expected at least one of {check['failed_required_any']}")
    return "FAIL — " + "; ".join(parts)


def build_report(results: list, models: list, timestamp: str) -> str:
    lines = []
    lines.append(f"# Model Evaluation Report")
    lines.append(f"\nGenerated: {timestamp}")
    lines.append(f"\n**Models compared:**")
    for m in models:
        lines.append(f"- `{m}`")

    # Summary table
    lines.append(f"\n---\n\n## Summary\n")
    lines.append(f"| # | Scenario | {models[0].split('/')[1]} | {models[1].split('/')[1]} |")
    lines.append(f"|---|---|---|---|")
    for r in results:
        a = score_line(r["checks"][models[0]])
        b = score_line(r["checks"][models[1]])
        a_icon = "✅" if r["checks"][models[0]]["passed"] else "❌"
        b_icon = "✅" if r["checks"][models[1]]["passed"] else "❌"
        lines.append(f"| {r['id']} | {r['title']} | {a_icon} {a} | {b_icon} {b} |")

    # Per-scenario detail
    lines.append(f"\n---\n\n## Detailed Results\n")
    for r in results:
        lines.append(f"### Scenario {r['id']} — {r['title']}\n")
        lines.append(f"**Check:** {r['check_description']}\n")

        for model in models:
            short = model.split("/")[1]
            check = r["checks"][model]
            icon = "✅ PASS" if check["passed"] else "❌ FAIL"
            lines.append(f"#### {short} — {icon}\n")
            lines.append(f"```")
            lines.append(r["responses"][model])
            lines.append(f"```\n")
            if not check["passed"]:
                if check["failed_forbidden"]:
                    lines.append(f"> ⚠️ Forbidden phrases found: {check['failed_forbidden']}")
                if check["failed_required"]:
                    lines.append(f"> ⚠️ Expected content missing: {check['failed_required']}")
                lines.append("")

        lines.append(f"**Manual score (1–5 each):**\n")
        lines.append(f"| Criteria | {models[0].split('/')[1]} | {models[1].split('/')[1]} |")
        lines.append(f"|---|---|---|")
        for criterion in ["Grounding", "Recommendation Quality", "Intent Understanding",
                          "Natural Conversation", "Instruction Following", "Hallucination Resistance"]:
            lines.append(f"| {criterion} | _ | _ |")
        lines.append(f"\n---\n")

    # Auto-score summary
    lines.append(f"## Auto-Check Results\n")
    for model in models:
        passed = sum(1 for r in results if r["checks"][model]["passed"])
        lines.append(f"- **{model.split('/')[1]}**: {passed}/{len(results)} auto-checks passed")

    return "\n".join(lines)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not settings.AI_PLATFORM_API_KEY:
        print("ERROR: AI_PLATFORM_API_KEY not set in .env")
        sys.exit(1)

    print(f"Evaluating {len(SCENARIOS)} scenarios across {len(MODELS)} models...\n")

    results = []

    for scenario in SCENARIOS:
        print(f"[Scenario {scenario['id']}] {scenario['title']}")
        responses = {}
        checks = {}

        for model in MODELS:
            short = model.split("/")[1]
            print(f"  → {short}... ", end="", flush=True)
            resp = call_model(model, scenario["system_prompt"], scenario["user_prompt"])
            responses[model] = resp
            checks[model] = check_response(resp, scenario["forbidden"], scenario["required"], scenario.get("required_any"))
            status = "✅" if checks[model]["passed"] else "❌"
            print(status)

        results.append({
            "id": scenario["id"],
            "title": scenario["title"],
            "check_description": scenario["check_description"],
            "responses": responses,
            "checks": checks,
        })

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    file_ts = datetime.now().strftime("%Y%m%d_%H%M")
    report = build_report(results, MODELS, timestamp)

    output_path = Path(__file__).resolve().parents[2] / "docs" / f"evaluation_report_{file_ts}.md"
    output_path.write_text(report, encoding="utf-8")

    print(f"\nReport saved to: docs/evaluation_report_{file_ts}.md")

    # Print auto-check summary to console
    print("\n── Auto-Check Summary ──────────────────────────")
    for model in MODELS:
        passed = sum(1 for r in results if r["checks"][model]["passed"])
        print(f"  {model.split('/')[1]}: {passed}/{len(SCENARIOS)} passed")

    # Raw responses JSON (for debugging)
    raw_path = Path(__file__).resolve().parents[2] / "docs" / f"evaluation_raw_{file_ts}.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Raw responses: docs/evaluation_raw_{file_ts}.json")


if __name__ == "__main__":
    main()
