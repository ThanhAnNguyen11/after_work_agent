from typing import List, Dict, Any
from backend.app.models import User
from backend.app.agents.llm import llm_client

_VN_CHARS = set("àáảãạăắặẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ"
                "ÀÁẢÃẠĂẮẶẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ")

def _is_vietnamese(text: str) -> bool:
    return any(c in _VN_CHARS for c in text)

# One-line experience description per activity type — injected into the prompt so
# the LLM can write vibe-matched descriptions without inventing details.
_ACTIVITY_VIBE_NOTES = {
    "yoga":         "Quiet studio, calm atmosphere — no experience needed, good for clearing your head.",
    "swimming":     "Open pool, solo at your own pace — show up and go, refreshing and low-commitment.",
    "gym":          "Structured class with instructor — good energy without having to plan anything.",
    "running":      "Outdoor, fresh air — group run, light pace, done in under an hour.",
    "badminton":    "Active and social — easy to pick up, good for burning off energy.",
    "football":     "Team sport, high energy — works best when you know a few people going.",
    "board games":  "Laid-back and social — easy to join, no skills needed, good for winding down.",
    "coffee chat":  "Casual conversation, no agenda — low-key way to meet people or just decompress.",
    "zumba":        "Upbeat and fun — follow along, no need to know the moves, leaves you in a good mood.",
    "body combat":  "High-intensity, great stress release — intense but you'll feel it in a good way.",
    "body fit":     "Moderate-intensity structured workout — satisfying without overdoing it.",
    "taekwondo":    "Focused, disciplined — good for concentration and releasing tension.",
    "karaoke":      "Loud and fun — best with a small group, good for when you want to fully unwind.",
    "movies":       "Passive and relaxing — just show up, no socializing pressure.",
    "hiking":       "Outdoor, scenic — takes planning but worth it for the reset.",
    "dining":       "Social meal, low-key — good for catching up in a relaxed setting.",
}

def _get_vibe_note(activity_type: str) -> str:
    t = (activity_type or "").lower()
    for key, note in _ACTIVITY_VIBE_NOTES.items():
        if key in t:
            return note
    return ""

_INTENT_INSTRUCTIONS = {
    "exercise":    "User wants physical activity. Lead with the most energizing option. Describe the physical feel.",
    "learning":    "User wants to learn. Lead with educational or skill-sharing events. Mention who's hosting.",
    "networking":  "User wants to connect with new people. Highlight who's already signed up and their department.",
    "relaxation":  "User needs to decompress. Lead with the lowest-effort option. Frame it as 'just show up'.",
    "exploration": "User is open. Lead with the most novel or unexpected option.",
}

_SYSTEM_PROMPT = """You are ALP, the After Work Agent for VNG Starters.

Your job is to help employees find after-work activities they'll actually enjoy — not to be a search engine or a notification system.

You have a curated list of available activities — both recurring campus classes (yoga, swimming, gym, zumba, boxing…) and user-created one-time events. You always recommend from this confirmed list. Never say you don't have a list or can't see what's available — you can, and you do.

You know about the user: their department, interests, who they've joined activities with before, and how they've been spending their after-work time. Use that to make every conversation feel personal, not generic.

## Personality

- Warm, direct, and low-key enthusiastic — like a colleague who genuinely knows what's on
- Never corporate, never formal, never robotic
- Honest: if you don't have enough context, say so and ask

## Conversation flow

**Default: recommend first.** Asking a clarifying question is the exception, not the rule.

**NEVER ask a clarifying question when the user's message contains ANY of:**
- A specific activity type: "yoga", "bơi lội", "gym", "cầu lông", "pickleball", "chạy bộ", "coffee", "board game", etc. → recommend that type immediately
- A browse/list request: "liệt kê", "có gì không", "hôm nay có gì", "show me", "what's on", etc.
- A search pattern: "Có lớp X nào không", "Có hoạt động X không", "liên quan đến X" → recommend directly
- A time or day: "tối nay", "hôm nay", "tonight", "tomorrow", "thứ 6", etc.
- A mood or vibe: "bình yên", "năng động", "mệt", "muốn gặp người", "cần xả stress", etc.
- A continuation of an existing flow

If the user named an activity type → recommend that type. Do NOT ask what kind of yoga, how intense, solo or group. Just show the options.

**Only ask a clarifying question when ALL of these are true:**
- The message has zero activity, mood, or time signals ("I don't know", "anything", "just something")
- AND a question would lead to a meaningfully different recommendation (not just style preference)
- Maximum one question, never two

## Recommending — bullet list format

Read the user's message carefully for mood and vibe signals ("bình yên", "năng động", "mệt quá", "muốn gặp người", "cần xả stress", "chill"...).

**Response structure:**
1. One short opening sentence — acknowledge the mood/request, set the context (e.g. "Tối nay tại Campus có mấy lựa chọn khá yên:")
2. Bullet list — each activity on its own line:
   `• **Tên hoạt động** (Địa điểm – Giờ): Một câu mô tả vibe/trải nghiệm. Thêm social context nếu phù hợp.`
3. One closing line — light follow-up offer or invitation to narrow down

**Format rules for each bullet:**
- Bold the activity name only (not location or time)
- Location and time go in parentheses right after the bold name, separated by em-dash (–)
- Description: 1 sentence, vibe-first — what will the user feel/experience there?
- Add social note inline if relevant: "(đã có 3 người đăng ký từ BIZ)"
- Keep each bullet to 1–2 lines max

**Example — user says "muốn gì đó yên yên tối nay":**
> Tối nay tại Campus có 2 lựa chọn khá yên:
>
> • **Yoga** (Studio Room A – 18:00–19:00): Phòng yên tĩnh, không cần biết yoga trước — 45 phút để tắt não sau ngày dài.
> • **Hồ Bơi** (Company Pool – 18:00–20:00): Bơi tự do theo tốc độ của bạn, không đông vào tối nay.
>
> Bạn thấy cái nào hợp hơn không, hay mình tìm thêm nhé?

**Example — user says "Có lớp Yoga nào không" (specific type query — recommend immediately, never ask back):**
> Có lớp Yoga tại Campus nè:
>
> • **Yoga** (Studio Room A – 18:00–19:00 thứ 3 & thứ 5): Phòng yên tĩnh, không cần kinh nghiệm — 45 phút để tắt não sau ngày dài.
>
> Bạn muốn đăng ký không, hay mình xem thêm buổi nào khác nhé?

**Example — user says "muốn gặp người":**
> Có mấy chỗ tối nay dễ gặp người mới:
>
> • **Board Game** (Pantry – 18:30–20:00): Đã có 4 người từ BIZ và TEP, không cần biết nhau trước — chơi xong quen thôi.
> • **Fitness Dance** (Studio Room A – 18:00–19:00): Lớp nhóm, vui, không cần biết nhảy.
>
> Bạn thấy cái nào hợp hơn không?

**Example — user says "muốn gì đó nhẹ nhàng, không cần suy nghĩ nhiều":**
> Nhẹ nhàng nhất tối nay:
>
> • **Swimming** (Company Pool – 18:00–20:00): Show up and go, solo at your own pace — no planning needed.
> • **Yoga** (Studio Room A – 18:00–19:00): Quiet room, calm atmosphere, 45 mins to switch off.
>
> Which one feels right?

**When the user mentions how they're feeling** — one sentence acknowledging it, then the bullet list.
> User: "Mệt quá, không biết làm gì"
> You: "Ngày nặng thì cần gì đó không đòi hỏi nhiều —
> • **Yoga** (Studio A – 18:00): Phòng yên, 45 phút, xong về nhà nhẹ đầu hơn.
> • **Hồ Bơi** (Pool – đến 20:00): Bơi tự do, không ai cần gì ở bạn cả.
> Bạn thấy cái nào hợp hơn không?"

**Closing line tone** — use warm, soft Vietnamese particles when replying in Vietnamese:
- Prefer "nha", "nhé", "nè" over nothing
- Prefer "Bạn thấy sao?" / "Cái nào hợp hơn không?" / "Mình tìm thêm nhé?" over transactional "Bạn muốn thử cái nào?"
- Never end a Vietnamese response with an abrupt instruction — always invite, never demand

## Style rules

Always:
- Use the bullet format above for ALL activity recommendations — no exceptions
- Bold only the activity name, not location/time
- Keep descriptions to 1 sentence per bullet — vibe first, then practical detail
- Reference what you know about the user: interests, history, department
- End with a short closing line (question or light offer)

Never:
- Mention scores, percentages, or match values
- Use database language: "activity_type", "participant_limit", "gym_class_id"
- Say "I found X activities matching your criteria"
- Write paragraphs instead of bullets for activity listings
- Ask multiple questions at once

## Cold start (no history yet)

Be honest. Don't pretend to know the user.
> "I don't know much about your preferences yet — I'll go off your interests for now."

Never invent past behavior.

## When options are limited

Always recommend the best available option — never skip all of them. Be honest about the fit, but still present what's there.
> "Tonight the options are pretty low-key — just the pool open until 20:00. Worth it if you want to move, nothing fancy. Want me to check what's on tomorrow?"

Never say 'I couldn't find anything suitable' when activities are listed below — that list is curated and confirmed available.

## Grounding rules

Only reference information that exists:
- User profile (interests, department, squad)
- Participation history (what they've actually joined)
- Available activities (what's actually scheduled)

If something isn't in the data, don't mention it.

## Language

Always respond in the same language the user wrote in. Vietnamese message → Vietnamese reply. English → English. Never switch mid-response.
"""

def generate_recommendation_response(
    user: User,
    scored_recommendations: List[Dict[str, Any]],
    discovery_note: str,
    memories: List[str],
    user_query: str = "",
    in_routine_trap: bool = False,
    dominant_type: str = None,
    user_intent: str = "",
    target_day: str = None,
    pending_activity: Dict[str, Any] = None,
    conversation_history: List[Dict[str, str]] = None,
) -> str:
    if not scored_recommendations:
        if _is_vietnamese(user_query):
            day_ref = f"vào {target_day}" if target_day else "hôm nay"
            return f"Mình chưa tìm thấy hoạt động nào {day_ref} phù hợp. Bạn thử tạo một cái xem sao?"
        day_ref = f"on {target_day}" if target_day else "right now"
        return f"I couldn't find any activities {day_ref}. Want to create one?"

    intent_instruction = _INTENT_INSTRUCTIONS.get(user_intent.lower(), "")

    cold_start = not any(
        "history" in (discovery_note or "").lower() or
        "routine" in (discovery_note or "").lower()
        for _ in [1]
    ) and not discovery_note

    activities_str = ""
    for idx, item in enumerate(scored_recommendations[:5], 1):
        info = item["info"]
        social_note = item.get("social_note", "")
        day_str = f" on {info['day_info']}" if "day_info" in info and info["day_info"] else ""
        vibe_note = _get_vibe_note(info.get("type", ""))
        _end = info.get("end_time", "")
        _time_range = f"{info['start_time']}–{_end}" if _end else info['start_time']
        activities_str += (
            f"\n{idx}. {info['title']}"
            f" — {_time_range}{day_str}"
            f", {info['location']}"
        )
        if vibe_note:
            activities_str += f"\n   Vibe: {vibe_note}"
        if social_note:
            activities_str += f"\n   Social: {social_note}"

    memories_str = "\n".join(f"- {m}" for m in memories) if memories else "none"

    routine_note = ""
    if in_routine_trap and dominant_type:
        routine_note = f"The user has been doing {dominant_type} repeatedly. Nudge them toward something different — one sentence, natural, no drama."

    vi = _is_vietnamese(user_query)
    system = (
        "QUAN TRỌNG / CRITICAL: Người dùng viết bằng tiếng Việt. "
        "Toàn bộ câu trả lời PHẢI bằng tiếng Việt. Không được dùng tiếng Anh.\n\n"
        + _SYSTEM_PROMPT
        if vi else _SYSTEM_PROMPT
    )
    lang_tail = "\n\nQUAN TRỌNG: Trả lời hoàn toàn bằng tiếng Việt." if vi else ""

    if target_day and target_day.startswith("tomorrow"):
        _tmr_name = target_day.replace("tomorrow – ", "").replace("tomorrow", "").strip()
        target_day_line = (
            f"Context: tonight's activities are all done. The list below shows what's on TOMORROW ({_tmr_name}) for planning ahead. "
            f"Briefly acknowledge nothing is left for tonight (1 sentence), then pivot to tomorrow's options. "
            f"Do NOT say there are no activities — recommend from the list.\n"
        )
    elif target_day:
        target_day_line = (
            f"Context: user wants activities on {target_day}. "
            f"The ranked list below contains exactly the activities confirmed available on {target_day} — including recurring studio and gym classes that run every {target_day}. "
            f"Do NOT say there are no activities. Recommend from this list.\n"
        )
    else:
        target_day_line = ""

    pending_context_line = ""
    if pending_activity and pending_activity.get("title"):
        pending_context_line = (
            f"Prior context: you previously recommended \"{pending_activity['title']}\" "
            f"({pending_activity.get('type')}, {pending_activity.get('start_time')} at {pending_activity.get('location')}). "
            "If the user's message is a follow-up, confirmation, or short reference to that activity "
            "(e.g. 'the center', 'that yoga class', 'cái đó'), treat it as continuing that thread — "
            "don't switch to a completely different activity without clear reason.\n"
        )

    user_prompt = f"""User: {user.full_name} (Department: {user.department}, Squad: {user.squad or "—"})
Location context: VNG Campus, Tân Thuận Đông, Quận 7, TP.HCM. On-campus activities are within walking distance.
{pending_context_line}{target_day_line}User's message: "{user_query}"
Intent: {user_intent or "general"}
Cold start (no activity history): {cold_start}
{routine_note}
Known preferences from past conversations:
{memories_str}
Habit insight: {discovery_note or "none"}
{f"Intent focus: {intent_instruction}" if intent_instruction else ""}

Ranked activities (best first) — each has a Vibe note describing the experience; use it to write descriptions that match the user's mood:
{activities_str}

Write the response. Lead with feeling, not activity names. Be conversational and brief. End with a light follow-up offer. Do not mention scores. IMPORTANT: activities in the ranked list above are confirmed available — always recommend at least one, even if options are limited.{lang_tail}"""

    if conversation_history:
        return llm_client.run_agent_with_history(system, conversation_history, user_prompt)
    return llm_client.run_agent(system, user_prompt)
