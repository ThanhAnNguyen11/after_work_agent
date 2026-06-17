import os
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models import User, Activity, FixedActivity, ActivityParticipant, Memory, RecommendationLog
from backend.app.org_utils import calculate_recommendation_score, organization_distance
from backend.app.agents.extraction import extract_activity_from_text, extract_optional_fields
from backend.app.agents.discovery import run_discovery_agent
from backend.app.agents.social_opp import run_social_opportunity_agent
from backend.app.agents.recommendation import generate_recommendation_response
from backend.app.agents.reflection import run_reflection_agent
from backend.app.agents.llm import llm_client

# Define the state shape
class AgentState(TypedDict):
    user_id: int
    message: str
    conversation_history: List[Dict[str, str]]  # [{role, content}, ...] — prior turns in this session
    intent: str       # "extract" or "recommend"
    user_intent: str  # "exercise" | "learning" | "networking" | "relaxation" | "exploration"
    response: str
    activity_created: bool  # True when extraction_node successfully created a new activity
    activity_type: Optional[str]  # activity type of the just-created activity

    # Internal variables passed between nodes
    user_data: Optional[Dict[str, Any]]
    available_activities: List[Dict[str, Any]]
    discovery_note: str
    social_notes: Dict[int, str]  # activity_id -> note
    scored_recommendations: List[Dict[str, Any]]
    memories: List[str]

    # Target day for temporal queries (e.g. "Monday, 2026-06-16"); None = today
    target_day: Optional[str]

    # 3-attempt flow state (loaded from DB at start of each turn)
    attempt_number: int
    attempt1_shown_ids: List[int]
    attempt2_filters: Dict[str, str]
    attempt2_substate: Optional[str]
    wellbeing_group: Optional[str]
    is_rejection: bool

    # Last top-recommended activity — persisted so next turn can reference it by context
    pending_activity: Optional[Dict[str, Any]]

    # Pending extraction state (loaded from DB at start of each turn)
    has_pending_extraction: bool
    pending_partial_data: Dict[str, Any]
    pending_missing_fields: List[str]

# --- NODES ---

def session_load_node(state: AgentState) -> Dict[str, Any]:
    """
    Loads RecommendationSession and PendingExtraction from DB at the start of every turn.
    Hydrates all stateful fields into AgentState so downstream nodes have full context.
    """
    from backend.app.session_utils import load_session, get_attempt1_shown_ids, get_attempt2_filters, get_pending_activity
    from backend.app.extraction_utils import load_pending, get_partial_data, get_missing_fields
    db = SessionLocal()
    try:
        session = load_session(state["user_id"], db)
        pending = load_pending(state["user_id"], db)
        # Only carry pending_activity into an ongoing conversation.
        # If conversation_history is empty this is a fresh chat — ignore stale DB state.
        # Also treat standalone greetings as session reset: old localStorage history can bleed
        # into new conversations when the browser reloads without clicking "New Chat".
        # Empty conversation_history = genuine New Chat (frontend cleared localStorage).
        # Clear all stale DB state so the new conversation starts clean.
        is_fresh_conversation = not state.get("conversation_history")
        if is_fresh_conversation and pending is not None:
            from backend.app.extraction_utils import clear_pending
            clear_pending(state["user_id"], db)
            pending = None

        # Abort in-flight extraction when user explicitly signals they want to FIND, not CREATE.
        # These phrases override has_pending_extraction so the router can reach recommendation flow.
        _ABORT_EXTRACTION_SIGNALS = [
            "mình ko tổ chức", "mình không tổ chức", "tôi ko tổ chức", "tôi không tổ chức",
            "ko muốn tổ chức", "không muốn tổ chức", "không định tổ chức", "ko định tổ chức",
            "muốn tham gia hoạt động có sẵn", "tham gia hoạt động có sẵn", "hoạt động có sẵn",
            "xem thử có", "có hoạt động sẵn chưa", "có hoạt động nào sẵn",
            "i don't want to create", "i don't want to host", "not creating", "not hosting",
            "just want to join", "want to join existing", "looking for existing",
        ]
        if pending is not None:
            _msg_lower = (state.get("message") or "").lower()
            if any(sig in _msg_lower for sig in _ABORT_EXTRACTION_SIGNALS):
                from backend.app.extraction_utils import clear_pending
                clear_pending(state["user_id"], db)
                pending = None
        return {
            "attempt_number": session.attempt_number,
            "attempt1_shown_ids": get_attempt1_shown_ids(session),
            "attempt2_filters": get_attempt2_filters(session),
            "attempt2_substate": session.attempt2_substate,
            "wellbeing_group": session.wellbeing_group,
            "is_rejection": False,
            "has_pending_extraction": pending is not None,
            "pending_partial_data": get_partial_data(pending) if pending else {},
            "pending_missing_fields": get_missing_fields(pending) if pending else [],
            "pending_activity": None if is_fresh_conversation else get_pending_activity(session),
        }
    finally:
        db.close()


def intent_detector(state: AgentState) -> Dict[str, Any]:
    """
    Classifies the user input into routing intent (extract/recommend) and
    semantic user intent (exercise/learning/networking/relaxation/exploration).
    Also detects rejection signals for the 3-attempt flow.
    """
    message = state["message"].lower()

    # --- Heuristic: detect casual/social messages directed at the agent ---
    chat_signals = [
        "what did you do", "how are you", "who are you", "what are you",
        "how's your day", "how was your day", "good morning", "good evening",
        "good afternoon", "what's up", "hey alp", "hi alp",
        # Creation inquiry — "what can I create?" / "how do I create?" — route to chat, not extraction
        "tôi có thể tạo", "tạo được gì", "tạo hoạt động gì", "làm sao tạo", "cách tạo",
        "what can i create", "how do i create", "how to create an activity", "can i create",
        # Request for more details about recommended activities — always a follow-up, not a new query
        "cho tôi thông tin", "thông tin về", "thông tin thêm", "kể thêm", "nói thêm",
        "chi tiết hơn", "cụ thể hơn", "biết thêm", "cho biết thêm",
        "hoạt động này thế nào", "hoạt động đó thế nào", "2 hoạt động này", "hai hoạt động",
        "tell me more about", "more details about", "more info about", "give me details",
        "what's the", "describe the", "can you tell me more",
    ]
    is_chat = any(sig in message for sig in chat_signals)

    # Explicit join/confirm signals — always route to chat_node where _auto_join_activity runs.
    # Must be detected BEFORE the LLM rejection classifier so they're never misclassified.
    _EXPLICIT_JOIN_SIGNALS = [
        "tôi sẽ tham gia", "mình sẽ tham gia", "tôi muốn tham gia lớp", "mình muốn tham gia lớp",
        "tôi đăng ký lớp", "mình đăng ký lớp", "tôi sẽ đăng ký", "mình sẽ đăng ký",
        "tôi đăng ký cái", "mình đăng ký cái", "đăng ký cho tôi", "đăng ký giúp tôi",
        "tôi tham gia lớp", "mình tham gia lớp",
        "i'll join", "i want to join", "sign me up", "count me in", "i'm joining",
    ]
    if not is_chat and any(sig in message for sig in _EXPLICIT_JOIN_SIGNALS):
        is_chat = True

    # Follow-up questions about the last recommended activity (pending_activity context).
    # These reference the activity by pronoun ("lớp đó") rather than name — route to chat_node
    # so the agent answers with pending_activity context instead of treating as filter answers.
    _PENDING_FOLLOWUP_SIGNALS = [
        "lớp đó", "cái đó", "hoạt động đó", "chỗ đó", "nó có",
        "bao nhiêu người", "có mấy người", "số người",
        "tell me more", "more info", "how many", "how many people", "that class",
    ]
    _pending_act = state.get("pending_activity") or {}
    if not is_chat and _pending_act and any(sig in message for sig in _PENDING_FOLLOWUP_SIGNALS):
        is_chat = True

    # "tham gia" / "đăng ký" with a pending activity → route to chat_node for join handling.
    # This catches "tôi muốn tham gia Fitness dance" (no "lớp" keyword) which bypassed _EXPLICIT_JOIN_SIGNALS.
    if not is_chat and _pending_act and any(sig in message for sig in ["tham gia", "đăng ký"]):
        is_chat = True

    # User replies with the activity title (e.g. "ăn tối cùng an") → treat as join confirmation.
    # Without this, LLM misclassifies the title as a new EXTRACT request.
    if not is_chat and _pending_act:
        _act_title = (_pending_act.get("title") or "").lower().strip()
        if _act_title and len(_act_title) >= 4 and _act_title in message:
            is_chat = True

    # --- Heuristic: detect guidelines/rules questions and class schedule queries ---
    guidelines_signals = [
        "quy định", "nội quy", "quy tắc", "hướng dẫn sử dụng", "cách sử dụng",
        "điều kiện sử dụng", "được phép", "không được", "giờ mở cửa", "giờ hoạt động",
        "có được mang", "có cần", "rules", "guidelines", "regulations", "policy",
        "how to use", "am i allowed", "can i bring",
        # Class schedule queries
        "có lớp nào", "có những lớp", "những lớp gì", "lớp nào không", "lịch lớp",
        "các lớp", "lớp học", "class nào", "có class", "có lớp gì",
        "gym có gì", "upfit có gì", "phòng tập có", "studio có",
        "what classes", "class schedule", "which classes",
    ]
    is_guidelines = any(sig in message for sig in guidelines_signals)

    # --- Heuristic: detect activity-creation signals ---
    creation_signals = [
        "at 6pm", "at 6 pm", "at 7pm", "at 5pm", "at 18:00", "at 19:00",
        "need 2 more", "need 3 more", "need more players", "need players",
        "anyone want to play", "football at", "badminton at", "board games at",
        "swimming at", "pool at", "swim at",
        # Vietnamese explicit create/host intent
        "tôi muốn tạo", "mình muốn tạo", "tôi muốn tổ chức", "mình muốn tổ chức",
        "tôi định tổ chức", "mình định tổ chức", "tôi định tạo", "mình định tạo",
        "muốn rủ mọi người", "tôi muốn rủ", "mình muốn rủ",
    ]
    is_extraction = any(sig in message for sig in creation_signals)

    # --- Heuristic: map keywords to semantic intent ---
    user_intent = "exploration"  # default
    if any(k in message for k in ["meet", "network", "connect", "new people", "other team", "other department", "outside my team"]):
        user_intent = "networking"
    elif any(k in message for k in ["learn", "study", "ai talk", "sharing", "knowledge", "workshop", "seminar"]):
        user_intent = "learning"
    elif any(k in message for k in ["relax", "chill", "unwind", "coffee", "board game", "casual", "hang out"]):
        user_intent = "relaxation"
    elif any(k in message for k in ["exercise", "workout", "gym", "run", "swim", "football", "badminton", "yoga", "sport", "fitness", "body"]):
        user_intent = "exercise"

    # --- Explicit browse/list/query signals — these are NEVER rejections ---
    # Includes: list requests, browse requests, and new specific-topic queries
    # ("Có hoạt động nào X không" / "liên quan đến X" = new query, not dissatisfaction with prior results)
    _BROWSE_SIGNALS = [
        "liệt kê", "tham khảo", "list all", "show all", "xem tất", "cho xem tất",
        "cho mình xem", "có hoạt động gì", "có gì không", "hôm nay có gì",
        "tất cả hoạt động", "browse", "show me everything",
        # New-topic query patterns — user is searching for something specific
        "có hoạt động nào", "liên quan đến", "có gì về", "about ", "related to",
        "muốn tìm hoạt động", "tìm hoạt động", "hoạt động về",
        # Temporal queries — asking about a specific day is ALWAYS a new search, never a rejection
        "ngày mai", "ngày kia", "tuần tới", "tuần sau", "tomorrow", "next week",
        "thứ 2", "thứ hai", "thứ 3", "thứ ba", "thứ 4", "thứ tư",
        "thứ 5", "thứ năm", "thứ 6", "thứ sáu", "thứ 7", "thứ bảy", "chủ nhật",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    ]
    is_explicit_browse = any(sig in message for sig in _BROWSE_SIGNALS)

    # --- Rejection detection (heuristic) ---
    rejection_signals = [
        "none of these", "not interested", "show me something else", "try again",
        "i don't like these", "don't like any", "nothing appeals", "these don't work",
        "none of them", "something else", "other options", "not for me",
        "don't want any", "pass on all", "skip all", "reject all",
        "no thanks", "none work", "nothing works", "not suitable",
        "không cái nào", "không thích", "cái khác", "thử lại",
    ]
    is_rejection = False if is_explicit_browse else any(sig in message for sig in rejection_signals)

    # Positive reaction signals — user reacted favorably to a recommendation; never a rejection.
    # is_positive_reaction flag also prevents LLM rejection classifier from running and overriding.
    _POSITIVE_REACTION_SIGNALS = [
        "thú vị nhỉ", "thú vị đó", "thú vị quá", "hay nhỉ", "hay đó", "hay quá",
        "nghe hay", "có vẻ hay", "nghe có vẻ hay", "nghe ổn", "ổn nhỉ", "ổn đó",
        "tốt nhỉ", "tốt đó", "cũng hay", "cũng ổn", "nghe tốt",
        "sounds good", "sounds fun", "sounds nice", "sounds great", "sounds interesting",
        "interesting", "that's cool", "nice one",
    ]
    is_positive_reaction = any(sig in message for sig in _POSITIVE_REACTION_SIGNALS)
    if is_positive_reaction:
        is_rejection = False
        # If there's a pending activity and user reacts positively, treat as chat follow-up
        # so the agent can respond in context rather than re-running the full recommendation pipeline.
        if not is_chat and _pending_act:
            is_chat = True

    # --- LLM classification (overrides heuristics when API is available) ---
    if not llm_client.is_mock:
        system_prompt = """You are an Intent Classifier for an after-work activity assistant.

Classify the user message into exactly ONE of these labels:
- EXTRACT: user wants to CREATE or HOST an activity (e.g. "Football at 6PM, need 2 more players", "tôi muốn tạo buổi chạy bộ tối nay", "tôi muốn tổ chức board game", "mình muốn rủ mọi người đi bơi")
- CHAT: casual conversation or social questions directed at you as an agent (e.g. "how are you?", "what did you do yesterday?", "who are you?", "tôi có thể tạo hoạt động gì?")
- EXERCISE: user wants physical activity (gym, football, yoga, running, swimming, badminton...)
- LEARNING: user wants educational or skill-building events (AI talk, study group, workshop...)
- NETWORKING: user wants to meet new people or connect cross-department
- RELAXATION: user wants to unwind (coffee chat, board games, casual hangout...)
- EXPLORATION: user has no specific preference or is just browsing what's available

Key distinctions:
- EXTRACT = user explicitly wants to HOST/CREATE (uses words like "tôi muốn tổ chức", "mình muốn tạo", "tôi định tổ chức", "I want to host", "I'll organize")
- Asking "X hay Y?" (which one?) is NOT EXTRACT — it's a preference question → classify by activity type (e.g. EXERCISE for badminton/pickleball)
- "Có hoạt động X sẵn chưa?" / "bạn xem thử có X không?" = user searching for existing activities → NOT EXTRACT → EXERCISE/EXPLORATION
- "mình ko tổ chức, muốn tham gia hoạt động có sẵn" = clearly NOT EXTRACT → EXERCISE/EXPLORATION
- CHAT = asking what they CAN create (generic inquiry, no specific activity)

Respond with exactly one word from the list above. No explanation."""

        llm_response = llm_client.run_agent(system_prompt, f"Message: '{state['message']}'").strip().upper()

        if "EXTRACT" in llm_response:
            is_extraction = True
        elif "CHAT" in llm_response:
            is_chat = True
        elif "EXERCISE" in llm_response:
            user_intent = "exercise"
        elif "LEARNING" in llm_response:
            user_intent = "learning"
        elif "NETWORKING" in llm_response:
            user_intent = "networking"
        elif "RELAXATION" in llm_response:
            user_intent = "relaxation"
        elif "EXPLORATION" in llm_response:
            user_intent = "exploration"

        # LLM rejection check for attempts beyond 1 (when user already received recommendations).
        # Skip entirely for: explicit browse, confirmed chat (join/follow-up), positive reactions.
        if not is_rejection and not is_extraction and not is_explicit_browse and not is_chat and not is_positive_reaction:
            attempt = state.get("attempt_number", 1)
            shown = state.get("attempt1_shown_ids", [])
            if attempt > 1 or shown:
                rej_system = """You are a Rejection Classifier for an activity recommendation chatbot.
The user has just received activity recommendations. Classify whether their reply is a REJECTION of all shown recommendations.

REJECTION means: the user explicitly declines ALL shown options with phrases like "not interested", "none of these", "something else", "thử lại", "không thích cái nào".

NOT_REJECTION means ANY of:
- The user is joining or confirming one of the recommendations ("Tôi sẽ tham gia", "I'll join", "đăng ký", "sign me up")
- The user reacted positively ("thú vị nhỉ", "hay đó", "sounds good", "interesting") — positive ≠ rejection
- The user is asking a follow-up question about one of the recommendations ("bao nhiêu người", "lớp đó ở đâu")
- The user gives a new specific query: a topic ("books", "yoga", "sách", "bơi"), a day ("tomorrow", "Friday"), a mood ("something relaxing")
- The user asks "Có hoạt động nào X không?" or "liên quan đến X" — these are new searches, not rejections
- The user wants to list/browse all activities
- The message is unrelated to the recommendations

Critical rules:
- Join/confirm messages ("Tôi sẽ tham gia", "I'll join", "đăng ký") are ALWAYS NOT_REJECTION
- Positive reactions ("thú vị", "hay đó", "sounds good") are ALWAYS NOT_REJECTION
- "Có hoạt động nào X không?" is ALWAYS NOT_REJECTION — it's a new specific search
- "liên quan đến X" is ALWAYS NOT_REJECTION — the user is narrowing their search to a new topic
- Any message containing a new activity type or topic is NOT_REJECTION
- Browse/explore requests ("liệt kê tất cả", "cho tôi xem tất cả") are ALWAYS NOT_REJECTION

When in doubt, choose NOT_REJECTION.

Respond with exactly one word: REJECTION or NOT_REJECTION."""
                rej_response = llm_client.run_agent(rej_system, f"User message: '{state['message']}'").strip().upper()
                if "REJECTION" in rej_response:
                    is_rejection = True

    intent = "extract" if is_extraction else "guidelines" if is_guidelines else "chat" if is_chat else "recommend"
    return {"intent": intent, "user_intent": user_intent, "is_rejection": is_rejection}


def _reset_session_for_user(user_id: int) -> None:
    """Reset RecommendationSession to attempt 1 for a fresh query."""
    from backend.app.session_utils import load_session, reset_session
    db = SessionLocal()
    try:
        session = load_session(user_id, db)
        reset_session(session, db)
    finally:
        db.close()


def reset_and_load_node(state: AgentState) -> Dict[str, Any]:
    """Resets session to attempt 1 and updates state, then hands off to load_user_context."""
    _reset_session_for_user(state["user_id"])
    return {"attempt_number": 1}


def attempt_router(state: AgentState) -> str:
    """
    Determines which sub-graph to route to based on attempt state and rejection signal.
    Returns a string route key consumed by add_conditional_edges.
    """
    # Pending extraction takes priority — even if intent was mis-classified,
    # follow-up messages belong to the in-flight creation flow.
    if state.get("has_pending_extraction"):
        return "extraction_node"

    intent = state.get("intent", "recommend")

    if intent == "chat":
        return "chat_node"

    if intent == "guidelines":
        return "guidelines_node"

    if intent == "extract":
        return "extraction_node"

    attempt = state.get("attempt_number", 1)
    is_rejection = state.get("is_rejection", False)
    substate = state.get("attempt2_substate")

    if attempt == 2:
        if substate == "awaiting_answers":
            return "attempt2_collect_answers_node"
        elif is_rejection:
            return "advance_to_attempt3_node"
        else:
            # Fresh query while in attempt 2 — reset to attempt 1 and re-recommend
            return "reset_and_load_node"

    if attempt == 3:
        if is_rejection:
            return "post_attempt3_node"
        else:
            # Fresh query while in attempt 3 — reset to attempt 1 and re-recommend
            return "reset_and_load_node"

    # attempt == 1
    if is_rejection:
        return "advance_to_attempt2_node"

    return "load_user_context"


def _auto_join_activity(user_id: int, pending_act: dict) -> str:
    """
    Joins a dynamic activity or gym class on behalf of the user when they confirm.
    Returns a status string for use in the LLM prompt.
    """
    if not pending_act:
        return ""
    from backend.app.models import ActivityParticipant, Activity, FixedActivityParticipant, Notification
    from backend.app.session_utils import load_session, save_attempt1_shown, get_attempt1_shown_ids
    from datetime import date as _date, timedelta as _td

    db = SessionLocal()
    try:
        class_type = pending_act.get("class_type")
        act_id = pending_act.get("id")
        if not act_id:
            return ""

        if class_type == "dynamic":
            activity = db.query(Activity).filter(Activity.id == act_id).first()
            if not activity or activity.status == "inactive":
                return "already_full"
            exists = db.query(ActivityParticipant).filter(
                ActivityParticipant.activity_id == act_id,
                ActivityParticipant.user_id == user_id,
            ).first()
            if exists:
                return "already_joined"
            if activity.current_participants >= activity.participant_limit:
                return "already_full"
            p = ActivityParticipant(activity_id=act_id, user_id=user_id)
            db.add(p)
            activity.current_participants += 1
            if activity.created_by != user_id:
                db.add(Notification(
                    user_id=activity.created_by,
                    message=f"{db.query(User).filter(User.id == user_id).first().full_name} đã tham gia hoạt động của bạn: '{activity.title}'."
                ))
            if activity.current_participants >= activity.participant_limit:
                activity.status = "inactive"
            db.commit()

        elif class_type == "gym_class":
            from backend.app.models import FixedActivity
            gc = db.query(FixedActivity).filter(FixedActivity.id == act_id).first()
            if not gc:
                return "not_found"
            today = _date.today()
            week_start = today - _td(days=today.weekday())
            exists = db.query(FixedActivityParticipant).filter(
                FixedActivityParticipant.user_id == user_id,
                FixedActivityParticipant.gym_class_id == act_id,
                FixedActivityParticipant.week_start == week_start,
            ).first()
            if exists:
                return "already_joined"
            db.add(FixedActivityParticipant(
                user_id=user_id, gym_class_id=act_id, week_start=week_start
            ))
            db.commit()
        else:
            return ""

        # Mark activity as shown so it won't be recommended again this session
        session = load_session(user_id, db)
        shown = get_attempt1_shown_ids(session)
        if act_id not in shown:
            shown.append(act_id)
            save_attempt1_shown(session, shown, db)

        return "joined"
    except Exception as e:
        db.rollback()
        print(f"[auto_join] error: {e}")
        return "error"
    finally:
        db.close()


def chat_node(state: AgentState) -> Dict[str, Any]:
    """
    Handles casual/social messages directed at the agent.
    Skips the full activity pipeline — just a lightweight LLM call.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == state["user_id"]).first()
        user_name = user.full_name.split()[-1] if user else "there"
        user_interests = list(user.interests) if user and user.interests else []
        user_dept = user.department or ""
        user_squad = user.squad or ""
    finally:
        db.close()

    # Confirmation/follow-up signals — user is referring to the last recommended activity
    _CONFIRM_SIGNALS = [
        "đăng ký", "tham gia", "cái đó", "cái kia", "cái đầu tiên", "cái thứ nhất",
        "cái 1", "option 1", "lựa chọn 1", "ok đi", "được rồi", "nghe hay đó",
        "thử cái đó", "tôi sẽ thử", "mình đăng ký", "sign me up", "i'll join",
        "i'll go", "i want to join", "let's do it", "that one",
    ]
    msg_lower = state["message"].lower()
    pending_act = state.get("pending_activity") or {}
    is_confirm = pending_act and any(sig in msg_lower for sig in _CONFIRM_SIGNALS)

    pending_context = ""
    if pending_act:
        act_title = pending_act.get('title', '')
        act_type = pending_act.get('type', '')
        act_time = pending_act.get('start_time', '')
        act_loc = pending_act.get('location', '')
        if is_confirm:
            pending_context = (
                f"\n\nContext: the user is confirming they want to join \"{act_title}\" "
                f"({act_type}, {act_time} at {act_loc}). "
                "Do this in order:\n"
                "1. Acknowledge their choice warmly (1 short sentence).\n"
                "2. Give any practical tip if relevant (e.g. 'arrive 5 min early', 'bring your ID card').\n"
                "3. Proactively write a short, ready-to-copy invite message they can forward to friends — "
                "format it as a standalone shareable text (e.g. 'Tối nay mình đi Yoga 18h ở Studio A. "
                "Ai muốn join không? 😊'). Introduce it with 'Đây là tin nhắn bạn có thể gửi cho bạn bè:' "
                "(Vietnamese) or 'Here's a quick invite you can send:' (English).\n"
                "Keep the whole response under 4 sentences plus the invite text."
            )
        else:
            pending_context = (
                f"\n\nContext: you just recommended \"{act_title}\" "
                f"({act_type}, {act_time} at {act_loc}). "
                "If the user is asking a follow-up about this activity (location details, "
                "what to bring, dress code, etc.), answer based on what you know about that activity. "
                "Don't recommend something different unless the user clearly asks for alternatives."
            )

    _interests_line = (
        f"User's interests (from onboarding): {', '.join(user_interests)}"
        if user_interests else "User has not set interests yet."
    )
    _profile_line = f"Department: {user_dept}" + (f", Squad: {user_squad}" if user_squad else "")

    system_prompt = f"""You are ALP, the After Work Agent for VNG Starters.

What you know about this user:
- {_interests_line}
- {_profile_line}

If the user asks what you know about them (interests, preferences, profile), answer using the info above — don't say you don't know if the data exists.

If the user asks for more information or details about activities mentioned earlier in the conversation, answer based on the conversation history — describe the activity, time, location, vibe, what to expect. Be helpful and specific.

Respond naturally and warmly. Keep it brief (1–3 sentences unless the user is asking for details).
Never claim to have done things or have a personal life. Be honest that you're an AI agent.

If the user asks what activities they can create or how to create one, explain briefly:
on-campus (book a campus venue — football field, badminton court, yoga studio, meeting room, etc.)
or off-campus (propose anything outside campus — dinner, hiking, coffee catch-up, etc.).
Then invite them to share the details so you can help set it up.

Tone: warm, direct, light — like a colleague, not a customer service bot.

Language: always respond in the same language the user wrote in. Vietnamese message → Vietnamese reply. English message → English reply.{pending_context}"""

    from backend.app.agents.recommendation import _is_vietnamese
    msg = state["message"]
    vi = _is_vietnamese(msg)
    effective_system = (
        "QUAN TRỌNG / CRITICAL: Người dùng viết bằng tiếng Việt. "
        "Toàn bộ câu trả lời PHẢI bằng tiếng Việt. Không được dùng tiếng Anh.\n\n"
        + system_prompt
        if vi else system_prompt
    )
    lang_tail = "\n\nQUAN TRỌNG: Trả lời hoàn toàn bằng tiếng Việt." if vi else ""
    now = datetime.now()
    _VN_DAYS = {"Monday": "thứ Hai", "Tuesday": "thứ Ba", "Wednesday": "thứ Tư",
                "Thursday": "thứ Năm", "Friday": "thứ Sáu", "Saturday": "thứ Bảy", "Sunday": "Chủ nhật"}
    en_day = now.strftime("%A")
    vn_day = _VN_DAYS.get(en_day, en_day)
    date_context = f"Current date/time: {now.strftime('%Y-%m-%d %H:%M')} ({en_day} / {vn_day})"

    # Auto-join on confirmation before generating response
    join_status = ""
    if is_confirm and pending_act:
        join_status = _auto_join_activity(state["user_id"], pending_act)

    _JOIN_STATUS_HINTS = {
        "joined":        " [SYSTEM: User has been SUCCESSFULLY joined to this activity. Confirm the join in your response — don't say 'I'll help you join', say 'You're in!'. Then offer the invite message.]",
        "already_joined": " [SYSTEM: User was already registered for this activity this week.]",
        "already_full":  " [SYSTEM: This activity is now full — user could not join. Mention this and suggest alternatives.]",
        "error":         " [SYSTEM: Join attempt failed due to a technical error. Apologize briefly.]",
    }
    confirm_hint = _JOIN_STATUS_HINTS.get(join_status, " [User appears to be confirming the last recommended activity.]") if is_confirm else ""
    user_prompt = f"{date_context}\nUser's name: {user_name}\nUser's message: \"{msg}\"{confirm_hint}{lang_tail}"

    history = state.get("conversation_history") or []
    if history:
        response = llm_client.run_agent_with_history(effective_system, history, user_prompt)
    else:
        response = llm_client.run_agent(effective_system, user_prompt)
    return {"response": response}


_GUIDELINES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "docs", "VNG_guidelines.md"
)

_ACTIVITY_SECTION_MAP = {
    "hồ bơi": "Hồ Bơi", "bơi": "Hồ Bơi", "swim": "Hồ Bơi", "swimming": "Hồ Bơi",
    "yoga": "Yoga",
    "zumba": "Zumba",
    "boxing": "Boxing", "box": "Boxing",
    "gym": "Gym", "phòng tập": "Gym",
}


def _load_guidelines_section(message: str) -> str:
    try:
        with open(_GUIDELINES_PATH, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return ""

    msg_lower = message.lower()
    target_section = None
    for keyword, section in _ACTIVITY_SECTION_MAP.items():
        if keyword in msg_lower:
            target_section = section
            break

    if not target_section:
        return content

    sections = content.split("\n## ")
    for sec in sections:
        if sec.strip().startswith(target_section):
            return "## " + sec.strip()

    return content


_CLASS_SCHEDULE_SIGNALS = [
    "có lớp nào", "có những lớp", "những lớp gì", "lớp nào không", "lịch lớp",
    "các lớp", "lớp học", "class nào", "có class", "có lớp gì",
    "gym có gì", "upfit có gì", "phòng tập có", "studio có",
    "what classes", "class schedule", "which classes",
]
_CLASS_DESCRIPTION_SIGNALS = [
    "là gì", "tập gì", "như thế nào", "gồm những gì", "nội dung", "bài tập",
    "có khó không", "phù hợp", "dành cho", "dễ không", "học gì",
    "what is", "what does", "how hard", "is it suitable", "for beginners",
    "describe", "tell me about", "explain",
]
# Free-access facilities — not listed as classes
_FREE_FACILITIES = {"gym", "swimming", "running"}


def _build_class_schedule_content(db) -> str:
    """Query DB and return all fixed classes (excluding free facilities) grouped by name + schedule."""
    from collections import defaultdict
    classes = db.query(FixedActivity).filter(FixedActivity.active == True).all()
    # Exclude free-access facilities
    classes = [c for c in classes if c.class_name.lower() not in _FREE_FACILITIES]

    # Group by (class_name, start_time, end_time, location) → collect weekdays
    schedule: dict = defaultdict(list)
    for c in classes:
        key = (c.class_name, c.start_time, c.end_time or "", c.location, c.instructor or "")
        schedule[key].extend([w.strip() for w in c.weekday.split(",")])

    if not schedule:
        return "Hiện không có lớp học cố định nào được lên lịch."

    lines = ["Lịch các lớp cố định tại VNG Campus:"]
    for (name, start, end, loc, instructor), days in sorted(schedule.items(), key=lambda x: x[0][1]):
        unique_days = list(dict.fromkeys(days))  # preserve order, deduplicate
        time_str = f"{start}–{end}" if end else start
        instructor_str = f" (GV: {instructor})" if instructor and instructor.lower() != "self-regulated" else ""
        lines.append(f"• **{name}** — {', '.join(unique_days)}, {time_str}, {loc}{instructor_str}")

    return "\n".join(lines)


def guidelines_node(state: AgentState) -> Dict[str, Any]:
    """Answers user questions about VNG Campus activity rules from VNG_guidelines.md,
    or returns class schedule from DB when user asks 'có lớp nào không'."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == state["user_id"]).first()
        user_name = user.full_name.split()[-1] if user else "there"

        from backend.app.agents.recommendation import _is_vietnamese
        msg = state["message"]
        vi = _is_vietnamese(msg)
        msg_lower = msg.lower()

        is_class_schedule = any(sig in msg_lower for sig in _CLASS_SCHEDULE_SIGNALS)
        is_class_description = (not is_class_schedule) and any(sig in msg_lower for sig in _CLASS_DESCRIPTION_SIGNALS)

        lang_prefix = "QUAN TRỌNG: Toàn bộ câu trả lời PHẢI bằng tiếng Việt.\n\n" if vi else ""
        lang_tail = "\n\nQUAN TRỌNG: Trả lời hoàn toàn bằng tiếng Việt." if vi else ""

        if is_class_schedule:
            # Return class schedule from DB
            schedule_content = _build_class_schedule_content(db)
            system = (
                lang_prefix
                + "You are ALP, the After Work Agent for VNG Starters.\n"
                "The user is asking about what classes or activities are available at VNG Campus.\n"
                "Use ONLY the schedule data provided below. Present it in a friendly, conversational way — "
                "not as a raw data dump. Group by time of day (trưa/tối) if helpful. "
                "Never invent classes not listed."
            )
            user_prompt = (
                f"User: {user_name}\n"
                f"Question: \"{msg}\"\n\n"
                f"{schedule_content}{lang_tail}"
            )

        elif is_class_description:
            # User asking what a class involves — use model knowledge + DB description as hint
            # Pull the description of matching class(es) from DB if available
            all_classes = db.query(FixedActivity).filter(FixedActivity.active == True).all()
            matching_desc = []
            for c in all_classes:
                if c.class_name.lower() in msg_lower or any(
                    w in msg_lower for w in c.class_name.lower().split()
                ):
                    if c.description and c.description not in [d for _, d in matching_desc]:
                        matching_desc.append((c.class_name, c.description))

            db_hint = ""
            if matching_desc:
                db_hint = "Context từ hệ thống:\n" + "\n".join(
                    f"- {name}: {desc}" for name, desc in matching_desc[:3]
                ) + "\n\n"

            system = (
                lang_prefix
                + "You are ALP, the After Work Agent for VNG Starters.\n"
                "Answer the user's question about a fitness class or activity type at VNG Campus.\n"
                "You may use your general knowledge about fitness and exercise classes to answer — "
                "this is not a rules question, it's a content question. "
                "If context from the system is provided, prioritize it; otherwise use your knowledge. "
                "Be friendly and helpful. Keep it concise — 2-4 sentences."
            )
            user_prompt = (
                f"User: {user_name}\n"
                f"Question: \"{msg}\"\n\n"
                f"{db_hint}"
                f"Answer the question naturally.{lang_tail}"
            )

        else:
            # Rules/regulations — strict: use only VNG_guidelines.md
            guidelines_content = _load_guidelines_section(msg)
            system = (
                lang_prefix
                + "You are ALP, the After Work Agent for VNG Starters.\n"
                "Answer the user's question about VNG Campus activity rules and guidelines.\n"
                "Use ONLY the content provided below — do not invent or assume any rules not listed.\n"
                "Be conversational and friendly. Summarize key points relevant to the question. "
                "Never say 'according to the guidelines' or cite the document — just answer naturally."
            )
            user_prompt = (
                f"User's name: {user_name}\n"
                f"User's question: \"{msg}\"\n\n"
                f"Relevant guidelines content:\n{guidelines_content}{lang_tail}"
            )

    finally:
        db.close()

    history = state.get("conversation_history") or []
    response = (llm_client.run_agent_with_history(system, history, user_prompt)
                if history else llm_client.run_agent(system, user_prompt))
    return {"response": response}


_MISSING_FIELD_LABELS_VI = {
    "activity_type": "loại hoạt động",
    "start_time": "thời gian bắt đầu",
    "location": "địa điểm",
}
_MISSING_FIELD_LABELS_EN = {
    "activity_type": "activity type",
    "start_time": "start time",
    "location": "location",
}

def _build_clarify_question(missing_fields: list, partial: dict = None, vi: bool = False, original_message: str = "") -> str:
    """Generate a friendly, context-aware clarifying question using the LLM."""
    labels = _MISSING_FIELD_LABELS_VI if vi else _MISSING_FIELD_LABELS_EN
    missing_str = " và ".join(labels.get(f, f) for f in missing_fields) if vi else " and ".join(labels.get(f, f) for f in missing_fields)

    # Build what we already know for context
    known_parts = []
    if partial:
        if partial.get("activity_type"):
            known_parts.append(f"activity type: {partial['activity_type']}")
        if partial.get("start_time"):
            known_parts.append(f"time: {partial['start_time']}")
        if partial.get("location"):
            known_parts.append(f"location: {partial['location']}")
    known_str = ", ".join(known_parts) if known_parts else "nothing yet"

    lang_prefix = "QUAN TRỌNG: Toàn bộ câu trả lời PHẢI bằng tiếng Việt.\n\n" if vi else ""
    lang_tail = "\n\nQUAN TRỌNG: Trả lời bằng tiếng Việt." if vi else ""
    system = (
        lang_prefix
        + "You are ALP, a friendly after-work activity assistant helping a user create an activity.\n"
        "Your response must:\n"
        "1. Start with a short enthusiastic reaction to what the user wants to create (1 sentence). "
        "Examples: 'Nghe thật thú vị!', 'Buổi chia sẻ về Agent nghe hay đó!', 'Sounds fun!', 'Great idea!'\n"
        "2. Then ask ONLY for the missing field(s) in one short, natural sentence — no lists, no bullet points.\n"
        "Keep the whole response under 2 sentences. Warm and casual, like a colleague."
    )
    user_prompt = (
        f"User's original message: \"{original_message}\"\n"
        f"What we already know: {known_str}\n"
        f"Still missing: {missing_str}\n"
        f"Generate a friendly 1-2 sentence response.{lang_tail}"
    )
    return llm_client.run_agent(system, user_prompt)


def _gc_effective_end(gc) -> str:
    """Return HH:MM end time for a FixedActivity — fallback to start + 1h if end_time not set."""
    if gc.end_time:
        return gc.end_time
    try:
        h, m = map(int, gc.start_time.split(":"))
        h = (h + 1) % 24
        return f"{h:02d}:{m:02d}"
    except Exception:
        return "23:59"


def _create_activity(user_id: int, data: dict, original_message: str, db) -> Dict[str, Any]:
    """Create an Activity from fully-populated extraction data and return a success response dict."""
    now = datetime.now()
    hour, minute = map(int, data["start_time"].split(":"))

    _WEEKDAY_IDX = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }
    dow = (data.get("day_of_week") or "").lower().strip()
    explicit_today = dow == "today"
    if dow == "tomorrow":
        target_date = (now + timedelta(days=1)).date()
    elif dow in _WEEKDAY_IDX:
        target_idx = _WEEKDAY_IDX[dow]
        days_ahead = target_idx - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        target_date = (now + timedelta(days=days_ahead)).date()
    else:
        target_date = now.date()

    start_time = datetime(target_date.year, target_date.month, target_date.day, hour, minute)
    if start_time < now:
        if explicit_today:
            # User said "today/tonight" — clamp to now rather than pushing to tomorrow
            start_time = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        else:
            start_time += timedelta(days=1)

    required_players = int(data.get("required_players") or 2)
    title = data.get("title") or f"{data['activity_type'].capitalize()} Session"

    _ON_CAMPUS_KEYWORDS = {"vng", "campus", "upfit", "rooftop", "công ty", "company pool", "hồ bơi vng", "gym vng"}
    _loc_lower = (data.get("location") or "").lower()
    location_type = "on_campus" if any(k in _loc_lower for k in _ON_CAMPUS_KEYWORDS) else data.get("location_type", "off_campus")

    # Optional fields collected in the second phase
    participant_limit = data.get("participant_limit")
    if participant_limit:
        participant_limit = max(int(participant_limit), 2)
    else:
        participant_limit = required_players + 1

    from backend.app.agents.recommendation import _is_vietnamese
    vi = _is_vietnamese(original_message)

    # Generate a short, human-readable description using what the model knows about this activity type
    _desc_system = (
        ("QUAN TRỌNG: Toàn bộ câu trả lời PHẢI bằng tiếng Việt.\n\n" if vi else "") +
        "You are writing a short activity description for a corporate after-work platform. "
        "Write exactly ONE sentence (max 15 words) that captures the vibe and appeal of this activity. "
        "Be specific to the activity type — draw on what you know about it (e.g. what it feels like, who it's for). "
        "Sound natural and inviting, not corporate. No quotes, no trailing punctuation."
    )
    _desc_prompt = (
        f'Activity: "{title}" — type: {data["activity_type"]}, location: {data["location"]}, '
        f'time: {start_time.strftime("%H:%M")}.'
        + (" Trả lời bằng tiếng Việt." if vi else "")
    )
    try:
        generated_desc = llm_client.run_agent(_desc_system, _desc_prompt).strip().strip('"').strip("'").rstrip(".")
    except Exception:
        generated_desc = None

    activity = Activity(
        title=title,
        description=generated_desc,
        activity_type=data["activity_type"],
        location_type=location_type,
        start_time=start_time,
        end_time=None,
        location=data["location"],
        participant_limit=participant_limit,
        current_participants=1,
        created_by=user_id,
        difficulty=data.get("difficulty"),
        guidelines=data.get("guidelines"),
    )
    db.add(activity)
    db.flush()
    db.add(ActivityParticipant(activity_id=activity.id, user_id=user_id))
    db.commit()

    lang_prefix = (
        "QUAN TRỌNG / CRITICAL: Người dùng viết bằng tiếng Việt. Toàn bộ câu trả lời PHẢI bằng tiếng Việt.\n\n"
        if vi else ""
    )
    lang_tail = "\n\nQUAN TRỌNG: Trả lời hoàn toàn bằng tiếng Việt." if vi else ""
    spots = participant_limit - 1
    difficulty_line = f"Difficulty: {activity.difficulty}. " if activity.difficulty else ""
    guidelines_line = f"Guidelines set: \"{activity.guidelines}\". " if activity.guidelines else ""
    sys_prompt = (
        lang_prefix
        + "You are ALP, a friendly after-work activity assistant. "
        "Confirm the activity was just created in a warm, natural 1–2 sentences. "
        "Mention the name, time, and location conversationally. "
        "Note that the user is the host and mention how many spots are open. "
        "If difficulty or guidelines were set, mention them briefly. "
        "End with a light suggestion to share or invite someone. "
        "Never use bullet points or headers — write it as natural chat."
    )
    detail_prompt = (
        f"Activity just created: \"{activity.title}\" ({activity.activity_type}), "
        f"at {activity.start_time.strftime('%H:%M')} on {activity.start_time.strftime('%A %d/%m')}, "
        f"location: {activity.location}. "
        f"Host (user) already joined. {spots} spots open for others. "
        f"{difficulty_line}{guidelines_line}"
        + lang_tail
    )
    msg = llm_client.run_agent(sys_prompt, detail_prompt)

    # Save newly created activity as pending so the next turn (e.g. "ok mình muốn tham gia")
    # references the right activity instead of a stale recommendation.
    try:
        from backend.app.session_utils import load_session, save_pending_activity
        _sess = load_session(user_id, db)
        save_pending_activity(_sess, {
            "id": activity.id,
            "title": activity.title,
            "type": activity.activity_type,
            "start_time": activity.start_time.strftime("%H:%M"),
            "location": activity.location,
            "class_type": "dynamic",
        }, db)
    except Exception:
        pass

    return {"response": msg, "activity_created": True, "activity_type": data["activity_type"]}


_OPTIONAL_SENTINEL = "__optional__"


_NO_DIFFICULTY_TYPES = {
    "coffee", "cafe", "coffee chat", "dinner", "lunch", "eating", "meal", "food",
    "social", "networking", "reading", "book", "book club", "board game", "board games",
    "movie", "karaoke", "party", "picnic", "workshop", "talk", "seminar",
    "ăn tối", "ăn trưa", "cà phê", "cà phê chat",
}

def _needs_difficulty(partial: dict) -> bool:
    atype = (partial.get("activity_type") or "").lower().strip()
    return not any(nd in atype for nd in _NO_DIFFICULTY_TYPES)


def _build_optional_question(partial: dict, vi: bool) -> str:
    activity_name = partial.get("title") or (partial.get("activity_type") or "hoạt động").capitalize()
    show_difficulty = _needs_difficulty(partial)
    if vi:
        if show_difficulty:
            return (
                f"Thêm vài thông tin cho buổi **{activity_name}** nhé — "
                "tối đa bao nhiêu người tham gia, mức độ (chill / vừa / khó), "
                "và có quy tắc hay hướng dẫn gì không? Bỏ qua được nha."
            )
        return (
            f"Thêm vài thông tin cho buổi **{activity_name}** nhé — "
            "tối đa bao nhiêu người tham gia, "
            "và có lưu ý hay hướng dẫn gì không? Bỏ qua được nha."
        )
    if show_difficulty:
        return (
            f"A few more details for **{activity_name}** — "
            "max participants, difficulty level (easy / medium / hard), "
            "and any rules or guidelines? Feel free to skip any."
        )
    return (
        f"A few more details for **{activity_name}** — "
        "max participants, and any notes or guidelines? Feel free to skip any."
    )


def extraction_node(state: AgentState) -> Dict[str, Any]:
    """
    Multi-turn activity creation with clarifying questions.

    Phase 1 — required fields: activity_type, start_time, location.
      Ask one question at a time until all are collected.

    Phase 2 — optional fields: participant_limit, difficulty, guidelines.
      After required fields are complete, ask one conversational question.
      User can answer any/all or skip entirely. Then create the activity.
    """
    from backend.app.extraction_utils import save_pending, clear_pending
    from backend.app.agents.recommendation import _is_vietnamese
    db = SessionLocal()
    try:
        user_id = state["user_id"]
        message = state["message"]
        vi = _is_vietnamese(message)
        has_pending = state.get("has_pending_extraction", False)
        pending_missing = list(state.get("pending_missing_fields", []))

        # --- Phase 2: collecting optional fields ---
        if has_pending and pending_missing == [_OPTIONAL_SENTINEL]:
            partial = dict(state.get("pending_partial_data", {}))
            original_msg = partial.pop("_original_message", message)
            optional = extract_optional_fields(message)
            partial.update({k: v for k, v in optional.items() if v is not None})
            clear_pending(user_id, db)
            _reset_session_for_user(user_id)
            return _create_activity(user_id, partial, original_msg, db)

        # --- Phase 1: collecting required fields ---
        new_data = extract_activity_from_text(message)

        if has_pending:
            partial = dict(state.get("pending_partial_data", {}))
            still_missing = [f for f in pending_missing if f != _OPTIONAL_SENTINEL]
            for field in still_missing[:]:
                if new_data.get(field) is not None:
                    partial[field] = new_data[field]
                    still_missing.remove(field)
            for field in ("required_players", "title", "location_type"):
                if field not in partial and new_data.get(field) is not None:
                    partial[field] = new_data[field]
        else:
            partial = {k: v for k, v in new_data.items() if k != "missing_fields"}
            still_missing = new_data.get("missing_fields", [])

        if still_missing:
            save_pending(user_id, partial, still_missing, db)
            return {"response": _build_clarify_question(still_missing, partial=partial, vi=vi, original_message=message)}

        # Required fields complete — move to optional phase
        partial["_original_message"] = message
        save_pending(user_id, partial, [_OPTIONAL_SENTINEL], db)
        return {"response": _build_optional_question(partial, vi=vi)}

    except Exception:
        db.rollback()
        if _is_vietnamese(state.get("message", "")):
            return {"response": "Có lỗi xảy ra khi tạo hoạt động, bạn thử lại nhé."}
        return {"response": "Something went wrong while creating the activity — please try again."}
    finally:
        db.close()


def advance_to_attempt2_node(state: AgentState) -> Dict[str, Any]:
    """
    Advances session to attempt 2, sets substate = awaiting_answers,
    returns bridge message with 4 filter questions.
    """
    from backend.app.session_utils import load_session, advance_attempt, set_attempt2_awaiting
    db = SessionLocal()
    try:
        session = load_session(state["user_id"], db)
        advance_attempt(session, db)
        set_attempt2_awaiting(session, db)

        from backend.app.agents.recommendation import _is_vietnamese
        vi = _is_vietnamese(state["message"])
        lang_prefix = (
            "QUAN TRỌNG / CRITICAL: Toàn bộ câu trả lời PHẢI bằng tiếng Việt.\n\n"
            if vi else ""
        )
        lang_tail = "\n\nQUAN TRỌNG: Trả lời bằng tiếng Việt." if vi else ""
        sys = (
            lang_prefix
            + "You are ALP, a friendly after-work activity assistant. "
            "The user wasn't satisfied with the first round of suggestions. You want to understand them better — not interrogate them. "
            "Ask TWO short questions in a warm, inviting way: "
            "one about energy level (nhẹ nhàng/thư giãn vs vận động/năng động) "
            "and one about going solo or with a group. "
            "Skip any dimension the user already mentioned. "
            "Weave both into a single natural sentence — no lists, no bullet points. "
            "Tone: like a colleague genuinely curious, not a form asking for data. "
            "Use soft Vietnamese particles (nha, nhé, nè) when writing in Vietnamese. "
            "Example Vietnamese: 'Để mình tìm đúng hơn nha — bạn đang muốn gì đó nhẹ nhàng hay muốn vận động thả ga? Và thích đi một mình hay rủ cả nhóm luôn?' "
            "Keep it under 2 sentences."
        )
        history = state.get("conversation_history") or []
        user_prompt = f"User message: \"{state['message']}\"{lang_tail}"
        bridge = (llm_client.run_agent_with_history(sys, history, user_prompt)
                  if history else llm_client.run_agent(sys, user_prompt))
        return {"response": bridge}
    finally:
        db.close()


def attempt2_collect_answers_node(state: AgentState) -> Dict[str, Any]:
    """
    Called when attempt2_substate == "awaiting_answers".
    Parses filter answers from user message, saves to DB.
    Routes to load_user_context so the full pipeline runs with filters applied.
    """
    from backend.app.agents.attempt2_filters import parse_attempt2_answers
    from backend.app.session_utils import load_session, save_attempt2_filters

    filters = parse_attempt2_answers(state["message"])

    db = SessionLocal()
    try:
        session = load_session(state["user_id"], db)
        save_attempt2_filters(session, filters, db)
    finally:
        db.close()

    return {
        "attempt2_filters": filters,
        "attempt2_substate": "filters_applied",
    }


def advance_to_attempt3_node(state: AgentState) -> Dict[str, Any]:
    """
    Advances session to attempt 3, returns empathetic bridge message.
    """
    from backend.app.session_utils import load_session, advance_attempt
    db = SessionLocal()
    try:
        session = load_session(state["user_id"], db)
        advance_attempt(session, db)

        from backend.app.agents.recommendation import _is_vietnamese
        vi = _is_vietnamese(state["message"])
        lang_prefix = (
            "QUAN TRỌNG / CRITICAL: Toàn bộ câu trả lời PHẢI bằng tiếng Việt.\n\n"
            if vi else ""
        )
        lang_tail = "\n\nQUAN TRỌNG: Trả lời bằng tiếng Việt." if vi else ""
        sys = (
            lang_prefix
            + "You are ALP, a friendly after-work activity assistant. "
            "The user has passed on suggestions twice. Stop offering activities entirely — just be human. "
            "Write 1 short, warm sentence acknowledging that nothing clicked (don't be dramatic about it), "
            "then ask ONE gentle open question about how they're doing or what kind of day they've had — "
            "about them as a person, not about activities. "
            "Tone: like a colleague checking in, not a chatbot running a script. "
            "Use soft Vietnamese particles (nha, nhé, à) when writing in Vietnamese. "
            "Example Vietnamese: 'Có vẻ chưa có cái nào hợp hôm nay nhỉ. Bạn hôm nay thế nào, có gì nặng nề không?' "
            "CRITICAL: your response MUST end with a question mark. Never list activities."
        )
        history = state.get("conversation_history") or []
        user_prompt = f"User message: \"{state['message']}\"{lang_tail}"
        bridge = (llm_client.run_agent_with_history(sys, history, user_prompt)
                  if history else llm_client.run_agent(sys, user_prompt))
        return {"response": bridge}
    finally:
        db.close()


def post_attempt3_node(state: AgentState) -> Dict[str, Any]:
    """
    Post-Attempt-3 fallback — pivots to activity creation. Resets session.
    """
    from backend.app.session_utils import load_session, reset_session
    db = SessionLocal()
    try:
        session = load_session(state["user_id"], db)
        reset_session(session, db)

        from backend.app.agents.recommendation import _is_vietnamese
        vi = _is_vietnamese(state["message"])
        lang_prefix = (
            "QUAN TRỌNG / CRITICAL: Toàn bộ câu trả lời PHẢI bằng tiếng Việt.\n\n"
            if vi else ""
        )
        lang_tail = "\n\nQUAN TRỌNG: Trả lời bằng tiếng Việt." if vi else ""
        sys = (
            lang_prefix
            + "You are ALP, a friendly after-work activity assistant. "
            "The recommendation flow has ended — none of the platform's activities matched the user. "
            "No matter what the user just said, your job NOW is to pivot to activity creation: "
            "warmly suggest they create their own activity (e.g. rủ bạn bè, tự đặt phòng, tự tổ chức). "
            "Tell them you can help set it up — on-campus (book a campus venue) or off-campus (anything outside). "
            "Write 2–3 sentences max. Warm, practical, not dramatic. "
            "Do NOT say goodbye. Do NOT just wish them a good day. Always end by inviting them to share what they have in mind."
        )
        history = state.get("conversation_history") or []
        user_prompt = f"User's last message: \"{state['message']}\"{lang_tail}"
        if history:
            msg = llm_client.run_agent_with_history(sys, history, user_prompt)
        else:
            msg = llm_client.run_agent(sys, user_prompt)
        return {"response": msg}
    finally:
        db.close()


def load_user_context(state: AgentState) -> Dict[str, Any]:
    """
    Loads user interests, history, memories, and available activities.
    Filters candidate activities and gym classes according to target date (today vs tomorrow).
    """
    db = SessionLocal()
    try:
        user_id = state["user_id"]
        message = state.get("message", "").lower()
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"response": "User not found."}

        participated_records = db.query(ActivityParticipant).filter(ActivityParticipant.user_id == user_id).all()
        history_ids = [p.activity_id for p in participated_records]

        history = db.query(Activity).filter(Activity.id.in_(history_ids)).all() if history_ids else []

        user_memories = db.query(Memory).filter(Memory.user_id == user_id).all()
        memories_list = [m.content for m in user_memories]

        now = datetime.now()
        target_date = now
        has_specific_day = False

        message_clean = message.lower()

        def _detect_day(text: str):
            """Returns (target_date, has_specific_day) from temporal keywords in text."""
            nonlocal now
            # Today signals — specific day but target = now
            if any(s in text for s in ["hôm nay", "tối nay", "buổi tối", "today", "tonight", "this evening", "bây giờ", "ngay bây giờ", "ngay lúc này", "lúc này", "right now", "ngay", "luôn"]):
                return now, True
            if "tomorrow" in text or "ngày mai" in text:
                return now + timedelta(days=1), True
            weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            for i, w in enumerate(weekdays):
                if w in text:
                    days_ahead = i - now.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    return now + timedelta(days=days_ahead), True
            vn_days = {
                "thứ 2": 0, "thứ hai": 0, "thu 2": 0,
                "thứ 3": 1, "thứ ba": 1, "thu 3": 1,
                "thứ 4": 2, "thứ tư": 2, "thu 4": 2,
                "thứ 5": 3, "thứ năm": 3, "thu 5": 3,
                "thứ 6": 4, "thứ sáu": 4, "thu 6": 4,
                "thứ 7": 5, "thứ bảy": 5, "thu 7": 5,
                "chủ nhật": 6, "chu nhat": 6,
                "cuối tuần": 5, "cuoi tuan": 5, "weekend": 5,
            }
            for vn, idx in vn_days.items():
                if vn in text:
                    days_ahead = idx - now.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    return now + timedelta(days=days_ahead), True
            return now, False

        # Priority: current message → most recent history message that mentions a day → no specific day (full week)
        target_date, has_specific_day = _detect_day(message_clean)
        if not has_specific_day:
            # Walk history newest-first to find the most recently mentioned day
            history_turns = [
                t for t in reversed((state.get("conversation_history") or []))
                if t.get("role") == "user"
            ]
            for turn in history_turns:
                _td, _found = _detect_day(turn.get("content", "").lower())
                if _found:
                    target_date, has_specific_day = _td, True
                    break

        grace_cutoff = now - timedelta(minutes=15)

        if has_specific_day:
            target_weekday = target_date.strftime("%A")
            target_date_only = target_date.date()
            effective_weekday = target_weekday
            _is_today = target_date_only == now.date()

            # For today: start from now (minus grace period) so expired activities are excluded.
            # For future days: full day window 00:00–23:59.
            _act_start = grace_cutoff if _is_today else datetime(target_date_only.year, target_date_only.month, target_date_only.day, 0, 0)
            _raw_acts = db.query(Activity).filter(
                Activity.start_time >= _act_start,
                Activity.start_time <= datetime(target_date_only.year, target_date_only.month, target_date_only.day, 23, 59),
                Activity.status == "active"
            ).all()
            # Also exclude activities whose end_time (or start + 1h fallback) has passed
            upcoming_activities = [
                a for a in _raw_acts
                if (a.end_time or a.start_time + timedelta(hours=1)) >= now
            ]

            gym_classes = db.query(FixedActivity).filter(FixedActivity.active == True).all()
            filtered_gym_classes = [gc for gc in gym_classes if target_weekday in gc.weekday]
            _gym_day_label: Dict[int, str] = {gc.id: target_weekday for gc in filtered_gym_classes}
            # For today's gym classes, filter out ones that have already ended
            if _is_today:
                now_hm_today = now.strftime("%H:%M")
                filtered_gym_classes = [gc for gc in filtered_gym_classes if _gc_effective_end(gc) > now_hm_today]
        else:
            effective_weekday = now.strftime("%A")
            # No specific day — pool = all activities from now through next 7 days
            _raw_acts = db.query(Activity).filter(
                Activity.start_time >= grace_cutoff,
                Activity.start_time <= now + timedelta(days=7),
                Activity.status == "active"
            ).all()
            upcoming_activities = [
                a for a in _raw_acts
                if (a.end_time or a.start_time + timedelta(hours=1)) >= now
            ]

            # Load gym classes for the next 7 days — each unique class appears once,
            # tagged with its next upcoming occurrence. This ensures classes like Yoga
            # that only run on specific days aren't missed when today's session has ended.
            gym_classes_all = db.query(FixedActivity).filter(FixedActivity.active == True).all()
            now_hm_temp = now.strftime("%H:%M")
            _gym_day_label: Dict[int, str] = {}  # gc.id → weekday label for display
            _seen_gym_ids: set = set()
            filtered_gym_classes = []
            for _day_offset in range(7):
                _check_dt = now + timedelta(days=_day_offset)
                _check_weekday = _check_dt.strftime("%A")
                for gc in gym_classes_all:
                    if gc.id in _seen_gym_ids:
                        continue
                    if _check_weekday not in gc.weekday:
                        continue
                    # Today: skip classes that have already ended
                    if _day_offset == 0 and _gc_effective_end(gc) <= now_hm_temp:
                        continue
                    _seen_gym_ids.add(gc.id)
                    filtered_gym_classes.append(gc)
                    _gym_day_label[gc.id] = _check_weekday
        # Exclude gym classes the user already joined this week
        from backend.app.models import FixedActivityParticipant
        from datetime import date as _date, timedelta as _td
        _today = now.date()
        _week_start = _today - _td(days=_today.weekday())
        _joined_gym_ids = {
            r.gym_class_id for r in db.query(FixedActivityParticipant).filter(
                FixedActivityParticipant.user_id == user_id,
                FixedActivityParticipant.week_start == _week_start,
            ).all()
        }
        if _joined_gym_ids:
            filtered_gym_classes = [gc for gc in filtered_gym_classes if gc.id not in _joined_gym_ids]

        candidate_activities = []

        for act in upcoming_activities:
            peer_ids = db.query(ActivityParticipant).filter(ActivityParticipant.activity_id == act.id).all()
            peers = []
            if peer_ids:
                peer_user_ids = [p.user_id for p in peer_ids]
                peers = db.query(User).filter(User.id.in_(peer_user_ids)).all()

            creator = db.query(User).filter(User.id == act.created_by).first()

            end_time_str = act.end_time.strftime("%H:%M") if act.end_time else (act.start_time + timedelta(hours=1)).strftime("%H:%M")

            candidate_activities.append({
                "type": "dynamic",
                "obj": act,
                "peers": peers,
                "creator": creator,
                "title": act.title,
                "activity_type": act.activity_type,
                "start_time": act.start_time.strftime("%H:%M"),
                "end_time": end_time_str,
                "location": act.location,
                "id": act.id,
                "day_info": act.start_time.strftime("%A (%Y-%m-%d)")
            })

        # Free-access facilities use friendlier display names
        _FACILITY_DISPLAY = {"Gym": "Tập luyện tự do", "Swimming": "Bơi tự do", "Running": "Chạy bộ tự do"}

        for gc in filtered_gym_classes:
            _gc_day = _gym_day_label.get(gc.id, effective_weekday) if not has_specific_day else effective_weekday
            candidate_activities.append({
                "type": "gym_class",
                "obj": gc,
                "peers": [],
                "creator": None,
                "title": _FACILITY_DISPLAY.get(gc.class_name, gc.class_name),
                "activity_type": gc.class_name.lower(),
                "start_time": gc.start_time,
                "end_time": gc.end_time if gc.end_time else "13:00",
                "location": gc.location,
                "id": gc.id,
                "day_info": _gc_day
            })

        # Weekend: exclude on-campus user-created activities (FixedActivities always kept)
        is_weekend = target_date.weekday() in (5, 6)
        if is_weekend:
            candidate_activities = [
                c for c in candidate_activities
                if not (c["type"] == "dynamic" and
                        getattr(c["obj"], "location_type", "off_campus") == "on_campus")
            ]

        # BU filter: hide same_bu-only activities from users outside that BU
        def _same_bu(user_a: User, user_b) -> bool:
            if not user_b:
                return True
            return (user_a.org_group or "").lower() == (user_b.org_group or "").lower()

        candidate_activities = [
            c for c in candidate_activities
            if c["type"] == "gym_class"
            or getattr(c["obj"], "open_to", "all") == "all"
            or _same_bu(user, c.get("creator"))
        ]

        user_dict = {
            "id": user.id,
            "full_name": user.full_name,
            "title": user.title,
            "interests": user.interests,
            "department": user.department,
            "squad": user.squad,
            "company": user.company,
            "org_group": user.org_group
        }

        print(f"[load_user_context] has_specific_day={has_specific_day}, target={target_date.strftime('%A %Y-%m-%d')}, candidates={len(candidate_activities)} (dynamic={len([c for c in candidate_activities if c['type']=='dynamic'])}, gym={len([c for c in candidate_activities if c['type']=='gym_class'])})")
        _target_day_val = target_date.strftime("%A") if has_specific_day else None
        return {
            "user_data": user_dict,
            "available_activities": candidate_activities,
            "memories": memories_list,
            "target_day": _target_day_val,
        }
    finally:
        db.close()


def discovery_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes the Discovery Agent to analyze habits and return routine-breaking insights.
    """
    db = SessionLocal()
    try:
        user_id = state["user_id"]
        user = db.query(User).filter(User.id == user_id).first()

        p_records = db.query(ActivityParticipant).filter(ActivityParticipant.user_id == user_id).all()
        history_ids = [p.activity_id for p in p_records]
        history = db.query(Activity).filter(Activity.id.in_(history_ids)).all() if history_ids else []

        note = run_discovery_agent(user.full_name, user.interests, history)
        return {"discovery_note": note}
    finally:
        db.close()


def social_opp_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes the Social Opportunity Agent for each upcoming dynamic activity.
    """
    db = SessionLocal()
    try:
        user_id = state["user_id"]
        user = db.query(User).filter(User.id == user_id).first()
        available = state["available_activities"]

        social_notes = {}
        for item in available:
            if item["type"] == "dynamic":
                act_id = item["id"]
                peer_ids = db.query(ActivityParticipant).filter(ActivityParticipant.activity_id == act_id).all()
                peers = []
                if peer_ids:
                    peer_user_ids = [p.user_id for p in peer_ids]
                    peers = db.query(User).filter(User.id.in_(peer_user_ids)).all()

                note = run_social_opportunity_agent(user, item["title"], peers)
                if note:
                    social_notes[act_id] = note

        return {"social_notes": social_notes}
    finally:
        db.close()


def recommendation_node(state: AgentState) -> Dict[str, Any]:
    """
    Ranks the available options based on scores and feeds them to the Recommendation Agent.
    For attempt 1, saves shown IDs to DB so rejection detection has them on the next turn.
    For attempt 2, applies user-provided filters before ranking.
    """
    from backend.app.session_utils import load_session, save_attempt1_shown
    db = SessionLocal()
    try:
        user_id = state["user_id"]
        user = db.query(User).filter(User.id == user_id).first()
        available = state["available_activities"]
        discovery_note = state["discovery_note"]
        social_notes = state.get("social_notes", {})
        memories = state["memories"]
        attempt_number = state.get("attempt_number", 1)
        attempt2_filters = state.get("attempt2_filters", {})
        attempt1_shown_ids = state.get("attempt1_shown_ids", [])

        p_records = db.query(ActivityParticipant).filter(ActivityParticipant.user_id == user_id).all()
        history_ids = [p.activity_id for p in p_records]
        history = db.query(Activity).filter(Activity.id.in_(history_ids)).all() if history_ids else []

        scored_list = []
        for item in available:
            obj = None
            if item["type"] == "dynamic":
                obj = db.query(Activity).filter(Activity.id == item["id"]).first()
                peer_records = db.query(ActivityParticipant).filter(ActivityParticipant.activity_id == obj.id).all()
                peers = db.query(User).filter(User.id.in_([p.user_id for p in peer_records])).all() if peer_records else []
                creator = db.query(User).filter(User.id == obj.created_by).first()
            else:
                obj = db.query(FixedActivity).filter(FixedActivity.id == item["id"]).first()
                peers = []
                creator = None

            scores = calculate_recommendation_score(
                user=user,
                activity_or_class=obj,
                user_history=history,
                participants=peers,
                creator=creator,
                user_query=state.get("message", ""),
                user_intent=state.get("user_intent", ""),
                db=db
            )

            info = {
                "title": item["title"],
                "type": item["activity_type"],
                "start_time": item["start_time"],
                "end_time": item.get("end_time", ""),
                "location": item["location"],
                "class_type": item["type"],
                "id": item["id"],
                "day_info": item.get("day_info", ""),
            }

            scored_list.append({
                "info": info,
                "scores": scores,
                "social_note": social_notes.get(item["id"], "") if item["type"] == "dynamic" else ""
            })

        scored_list.sort(key=lambda x: x["scores"]["final_score"], reverse=True)

        # Memory-based score adjustment: +0.1 for liked types, -0.1 for disliked types
        if memories:
            def _boost_from_memories(mems: list, act_type: str) -> float:
                positive_signals = ["likes", "enjoys", "loves", "interested in", "wants to try", "prefers"]
                negative_signals = ["doesn't like", "dislikes", "not interested", "avoids"]
                boost = 0.0
                for mem in mems:
                    m = mem.lower()
                    if act_type in m:
                        if any(s in m for s in positive_signals):
                            boost = max(boost, 0.1)
                        elif any(s in m for s in negative_signals):
                            boost = min(boost, -0.1)
                return boost

            for item in scored_list:
                mem_boost = _boost_from_memories(memories, item["info"]["type"].lower())
                if mem_boost != 0.0:
                    item["scores"]["final_score"] = max(0.0, min(1.0, item["scores"]["final_score"] + mem_boost))
            scored_list.sort(key=lambda x: x["scores"]["final_score"], reverse=True)

        # Save shown IDs on Attempt 1 so they're available when rejection arrives next turn
        if attempt_number == 1:
            rec_session = load_session(user_id, db)
            save_attempt1_shown(rec_session, [item["info"]["id"] for item in scored_list[:5]], db)

        # Apply Attempt 2 filters (exclude attempt 1 IDs + soft boosts)
        if attempt_number == 2 and attempt2_filters:
            from backend.app.org_utils import apply_attempt2_filters
            scored_list = apply_attempt2_filters(scored_list, attempt2_filters, attempt1_shown_ids)

        # If a pending_activity exists and the user is following up on it, bubble it to the top
        # so the LLM always has it in position 1 and stays consistent
        pending_act = state.get("pending_activity") or {}
        if pending_act and scored_list:
            pending_id = pending_act.get("id")
            pending_type = (pending_act.get("type") or "").lower()
            msg_lower_pa = state.get("message", "").lower()
            # Detect follow-up: user mentions the pending activity's type/title OR sends a short answer
            _is_followup = (
                pending_type and (pending_type in msg_lower_pa or len(msg_lower_pa.split()) <= 4)
            )
            if _is_followup and pending_id:
                match_idx = next(
                    (i for i, it in enumerate(scored_list) if it["info"].get("id") == pending_id),
                    None
                )
                if match_idx is not None and match_idx > 0:
                    scored_list.insert(0, scored_list.pop(match_idx))

        in_routine_trap = False
        dominant_type = None
        if scored_list:
            in_routine_trap = scored_list[0]["scores"].get("in_routine_trap", False)
            dominant_type = scored_list[0]["scores"].get("dominant_type", None)

            message = state.get("message", "")
            if message:
                msg_clean = message.lower()
                for item in scored_list:
                    act_name = item["info"]["title"].lower()
                    act_type = item["info"]["type"].lower()
                    if act_type in msg_clean or act_name in msg_clean or (act_type == "gym" and "yoga" in msg_clean) or "swim" in msg_clean or "pool" in msg_clean:
                        in_routine_trap = False
                        break

        print(f"[recommendation_node] available={len(available)}, scored={len(scored_list)}, target_day={state.get('target_day')}, top3={[i['info']['title'] for i in scored_list[:3]]}")
        response = generate_recommendation_response(
            user=user,
            scored_recommendations=scored_list,
            discovery_note=discovery_note,
            memories=memories,
            user_query=state.get("message", ""),
            in_routine_trap=in_routine_trap,
            dominant_type=dominant_type,
            user_intent=state.get("user_intent", ""),
            target_day=state.get("target_day"),
            pending_activity=state.get("pending_activity"),
            conversation_history=state.get("conversation_history") or [],
        )

        for item in scored_list[:3]:
            info = item["info"]
            act_id = info["id"] if info["class_type"] == "dynamic" else None
            gym_id = info["id"] if info["class_type"] == "gym_class" else None
            log = RecommendationLog(
                user_id=user_id,
                activity_id=act_id,
                gym_class_id=gym_id,
                status="shown"
            )
            db.add(log)
        db.commit()

        # Save the activity mentioned FIRST in the response as pending_activity so the
        # next confirmation turn references what the user actually saw, not just the top scorer.
        if scored_list:
            from backend.app.session_utils import load_session, save_pending_activity
            resp_lower = response.lower()
            first_item = scored_list[0]
            best_pos = len(resp_lower) + 1
            for item in scored_list[:5]:
                title = (item["info"].get("title") or "").lower()
                if title:
                    pos = resp_lower.find(title)
                    if pos != -1 and pos < best_pos:
                        best_pos = pos
                        first_item = item
            top_info = first_item["info"]
            pending_act = {
                "id": top_info.get("id"),
                "title": top_info.get("title"),
                "type": top_info.get("type"),
                "start_time": top_info.get("start_time"),
                "location": top_info.get("location"),
                "class_type": top_info.get("class_type"),
            }
            _sess = load_session(user_id, db)
            save_pending_activity(_sess, pending_act, db)

        return {
            "scored_recommendations": scored_list,
            "response": response
        }
    finally:
        db.close()


def attempt3_wellbeing_node(state: AgentState) -> Dict[str, Any]:
    """
    Attempt 3: re-frames scored recommendations with an empathetic, wellbeing-focused response.
    The scoring pipeline ran just before this node to populate scored_recommendations.
    """
    from backend.app.agents.wellbeing import run_wellbeing_agent
    from backend.app.session_utils import load_session, save_wellbeing_group
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == state["user_id"]).first()
        scored = state.get("scored_recommendations", [])
        existing_group = state.get("wellbeing_group")

        result = run_wellbeing_agent(
            user=user,
            message=state["message"],
            scored_recommendations=scored,
            existing_group=existing_group
        )

        session = load_session(state["user_id"], db)
        save_wellbeing_group(session, result["wellbeing_group"], db)

        return {"response": result["response"], "wellbeing_group": result["wellbeing_group"]}
    finally:
        db.close()


def reflection_node(state: AgentState) -> Dict[str, Any]:
    """
    Runs the Reflection Agent on the chat query to extract any new user preferences,
    and updates the database.
    """
    db = SessionLocal()
    try:
        user_id = state["user_id"]
        message = state["message"]
        memories_copy = list(state.get("memories", []))
        new_memory = run_reflection_agent(message)
        if new_memory:
            exists = db.query(Memory).filter(
                Memory.user_id == user_id,
                Memory.content == new_memory
            ).first()

            if not exists:
                mem = Memory(user_id=user_id, content=new_memory)
                db.add(mem)
                db.commit()
                memories_copy.append(new_memory)
                print(f"Reflection Agent: Saved new memory for user {user_id}: '{new_memory}'")
        return {"memories": memories_copy}
    except Exception as e:
        print(f"Reflection Agent error: {e}")
        return {}
    finally:
        db.close()


# --- ROUTING FUNCTIONS ---

def route_after_recommendation(state: AgentState) -> str:
    if state.get("attempt_number", 1) == 3:
        return "attempt3_wellbeing_node"
    return "reflection_node"


# --- DEFINE GRAPH ---

builder = StateGraph(AgentState)

# Add Nodes
builder.add_node("session_load_node", session_load_node)
builder.add_node("intent_detector", intent_detector)
builder.add_node("extraction_node", extraction_node)
builder.add_node("chat_node", chat_node)
builder.add_node("guidelines_node", guidelines_node)
builder.add_node("advance_to_attempt2_node", advance_to_attempt2_node)
builder.add_node("attempt2_collect_answers_node", attempt2_collect_answers_node)
builder.add_node("advance_to_attempt3_node", advance_to_attempt3_node)
builder.add_node("post_attempt3_node", post_attempt3_node)
builder.add_node("load_user_context", load_user_context)
builder.add_node("discovery_node", discovery_node)
builder.add_node("social_opp_node", social_opp_node)
builder.add_node("recommendation_node", recommendation_node)
builder.add_node("attempt3_wellbeing_node", attempt3_wellbeing_node)
builder.add_node("reflection_node", reflection_node)

# Entry point
builder.set_entry_point("session_load_node")
builder.add_edge("session_load_node", "intent_detector")

# Route after intent detection
builder.add_node("reset_and_load_node", reset_and_load_node)

builder.add_conditional_edges(
    "intent_detector",
    attempt_router,
    {
        "extraction_node": "extraction_node",
        "chat_node": "chat_node",
        "guidelines_node": "guidelines_node",
        "load_user_context": "load_user_context",
        "reset_and_load_node": "reset_and_load_node",
        "advance_to_attempt2_node": "advance_to_attempt2_node",
        "attempt2_collect_answers_node": "attempt2_collect_answers_node",
        "advance_to_attempt3_node": "advance_to_attempt3_node",
        "post_attempt3_node": "post_attempt3_node",
    }
)

builder.add_edge("reset_and_load_node", "load_user_context")

# Bridging nodes go straight to reflection then END
builder.add_edge("extraction_node", END)
builder.add_edge("chat_node", "reflection_node")
builder.add_edge("guidelines_node", END)
builder.add_edge("advance_to_attempt2_node", "reflection_node")
builder.add_edge("advance_to_attempt3_node", "reflection_node")
builder.add_edge("post_attempt3_node", "reflection_node")

# Attempt 2 answer collection feeds back into the main pipeline
builder.add_edge("attempt2_collect_answers_node", "load_user_context")

# Main pipeline
builder.add_edge("load_user_context", "discovery_node")
builder.add_edge("discovery_node", "social_opp_node")
builder.add_edge("social_opp_node", "recommendation_node")

# After recommendation: attempt 3 gets wellbeing framing, others go straight to reflection
builder.add_conditional_edges(
    "recommendation_node",
    route_after_recommendation,
    {
        "attempt3_wellbeing_node": "attempt3_wellbeing_node",
        "reflection_node": "reflection_node",
    }
)
builder.add_edge("attempt3_wellbeing_node", "reflection_node")
builder.add_edge("reflection_node", END)

# Compile
compiled_graph = builder.compile()


def run_agent_flow(user_id: int, message: str, conversation_history: list = None) -> str:
    """
    Main entry point to execute the LangGraph workflow.
    conversation_history: [{role, content}, ...] — prior turns in this chat session (not cross-session learning).
    """
    initial_state = {
        "user_id": user_id,
        "message": message,
        "conversation_history": (conversation_history or [])[-20:],  # cap at 20 messages
        "intent": "",
        "user_intent": "",
        "response": "",
        "user_data": None,
        "available_activities": [],
        "discovery_note": "",
        "social_notes": {},
        "scored_recommendations": [],
        "memories": [],
        "attempt_number": 1,
        "attempt1_shown_ids": [],
        "attempt2_filters": {},
        "attempt2_substate": None,
        "wellbeing_group": None,
        "is_rejection": False,
        "pending_activity": None,
        "target_day": None,
        "has_pending_extraction": False,
        "pending_partial_data": {},
        "pending_missing_fields": [],
        "activity_created": False,
        "activity_type": None,
    }

    final_state = compiled_graph.invoke(initial_state)
    return final_state["response"], final_state.get("activity_created", False), final_state.get("activity_type")
