from typing import Dict, Any, Optional, List
from backend.app.agents.llm import llm_client


WELLBEING_GROUPS = {
    "burnout": {
        "symptoms": [
            "overwhelmed", "too much", "no mental space", "exhausted", "burnt out", "burn out",
            "burned out", "no energy for anything",
            "quá tải", "kiệt sức", "không còn sức", "hết năng lượng", "burnout",
        ],
        "advice_theme": "gentle solo low-intensity activity",
    },
    "isolation": {
        "symptoms": [
            "lonely", "disconnected", "unseen", "no one to talk", "feeling alone", "isolated",
            "cô đơn", "không ai nói chuyện", "một mình mãi", "cô lập", "không kết nối",
        ],
        "advice_theme": "small familiar group activity",
    },
    "career_anxiety": {
        "symptoms": [
            "unsure", "path", "direction", "motivation", "career", "what am i doing", "lost",
            "lo lắng về tương lai", "không biết đi đâu", "mất định hướng", "deadline", "áp lực công việc",
            "không có động lực", "chán việc",
        ],
        "advice_theme": "learning track with senior peers",
    },
    "fatigue": {
        "symptoms": [
            "body tired", "physically tired", "sore", "aching", "need rest", "tired body",
            "mệt mỏi", "mệt lắm", "mệt quá", "mệt rồi", "mệt", "người mệt", "cơ thể mệt",
            "buồn ngủ", "kiệt", "không có sức",
        ],
        "advice_theme": "physical recovery activity",
    },
    "emotional_stress": {
        "symptoms": [
            "stressed", "personal", "hard week", "rough day", "anxious", "worried", "stress",
            "căng thẳng", "lo lắng", "áp lực", "bức bối", "khó chịu", "buồn", "không vui",
            "chán", "bực bội", "tâm trạng không tốt", "không ổn",
        ],
        "advice_theme": "quiet creative or outdoor solo activity",
    },
}


def detect_wellbeing_group(message: str) -> Optional[str]:
    """Heuristic detection of wellbeing group from user message."""
    lowered = message.lower()
    for group, data in WELLBEING_GROUPS.items():
        if any(symptom in lowered for symptom in data["symptoms"]):
            return group
    return None


def run_wellbeing_agent(
    user: Any,
    message: str,
    scored_recommendations: List[Dict],
    existing_group: Optional[str] = None
) -> Dict[str, Any]:
    """
    Attempt 3 wellbeing-focused response.
    Detects which wellbeing group the user belongs to, generates 2-3 empathetic advice pieces,
    then re-frames the Top 5 recommendations as wellbeing support.
    Returns: {"response": str, "wellbeing_group": str}
    """
    group = existing_group or detect_wellbeing_group(message)
    if not group:
        group = "emotional_stress"

    group_data = WELLBEING_GROUPS.get(group, WELLBEING_GROUPS["emotional_stress"])

    recs_str = ""
    for i, item in enumerate(scored_recommendations[:5], 1):
        info = item["info"]
        recs_str += f"\n{i}. {info['title']} — {info['start_time']} at {info['location']}"

    if llm_client.is_mock:
        return {
            "response": (
                "I hear you — sometimes the hardest part is just getting started.\n\n"
                "A few thoughts that might actually help:\n"
                "1. Give yourself permission to do something that asks very little of you tonight.\n"
                "2. Even light movement tends to shift how you feel faster than you'd expect.\n"
                "3. You don't have to enjoy it — just show up.\n\n"
                "With that in mind, here are a few options I think could genuinely help with what you're going through:"
                f"{recs_str}"
            ),
            "wellbeing_group": group
        }

    user_name = getattr(user, "full_name", "there") or "there"
    given_name = user_name.split()[-1] if user_name else "there"
    department = getattr(user, "department", "") or ""

    system_prompt = f"""You are After Work Agent, acting as a warm and supportive companion — not a salesperson.
The user has declined all activity recommendations twice. They need empathy, not more selling.

Detected wellbeing context: {group} — {group_data['advice_theme']}.

Tone: warm, human, honest, non-clinical. No corporate wellness clichés.
Structure:
1. One sentence acknowledging what they might be going through (without diagnosing or being presumptuous)
2. Two or three short, genuine pieces of advice that relate to their situation
3. A single gentle transition sentence that re-frames the Top 5 as support — NOT as "recommendations"

Rules:
- Do NOT use the word "recommendation" anywhere
- Do NOT list scores or technical match details
- Do NOT be overly cheerful or use exclamation marks
- After the transition sentence, list the activities naturally (just name, time, location)"""

    from backend.app.agents.recommendation import _is_vietnamese
    vi = _is_vietnamese(message)
    effective_system = (
        "QUAN TRỌNG / CRITICAL: Người dùng viết bằng tiếng Việt. "
        "Toàn bộ câu trả lời PHẢI bằng tiếng Việt. Không được dùng tiếng Anh.\n\n"
        + system_prompt
        if vi else system_prompt
    )
    lang_tail = "\n\nQUAN TRỌNG: Trả lời hoàn toàn bằng tiếng Việt." if vi else ""

    user_prompt = f"""User: {user_name} ({department})
Detected wellbeing group: {group}
User's message: "{message}"

Activities to gently offer:
{recs_str}

Write the complete response following the structure above.{lang_tail}"""

    response = llm_client.run_agent(effective_system, user_prompt)
    return {"response": response, "wellbeing_group": group}
