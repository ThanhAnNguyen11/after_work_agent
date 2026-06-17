import json
from backend.app.agents.llm import llm_client


def extract_optional_fields(text: str) -> dict:
    """
    Parses optional activity details from a follow-up user message.
    Returns dict with keys: participant_limit (int|None), difficulty (str|None), guidelines (str|None).
    User can skip any or all fields — always returns something safe to merge.
    """
    system_prompt = """You are an Activity Detail Extractor. Parse optional fields from a short message.
Return ONLY a valid JSON object. No markdown, no extra text.

Fields:
1. "participant_limit": integer total max participants (INCLUDING the host).
   If user says "5 người" or "need 4 more" (host + 4 = 5) → use total count.
   If not stated or user skips → null.
2. "difficulty": one of "Beginner", "Intermediate", "Advanced", "All Levels".
   Map: chill / nhẹ / dễ / easy / beginner → "Beginner"
        vừa / trung bình / medium / moderate → "Intermediate"
        khó / nâng cao / hard / advanced → "Advanced"
        tất cả / mọi người / all / anyone → "All Levels"
   If not stated or user skips → null.
3. "guidelines": string with rules/notes the host provides for participants.
   If user says "không có", "bỏ qua", "skip", "none", or provides nothing → null.

Examples:
"10 người, mức trung bình, mang giày thể thao"
→ {"participant_limit":10,"difficulty":"Intermediate","guidelines":"Mang giày thể thao"}

"cần 5 người nữa, dễ thôi"
→ {"participant_limit":6,"difficulty":"Beginner","guidelines":null}

"bỏ qua hết"
→ {"participant_limit":null,"difficulty":null,"guidelines":null}

"không có gì đặc biệt, thoải mái"
→ {"participant_limit":null,"difficulty":null,"guidelines":null}
"""
    result_str = llm_client.run_agent(system_prompt, f"Message: '{text}'")
    cleaned = result_str.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        data = json.loads(cleaned)
        pl = data.get("participant_limit")
        return {
            "participant_limit": int(pl) if pl is not None else None,
            "difficulty": data.get("difficulty"),
            "guidelines": data.get("guidelines") or None,
        }
    except Exception:
        return {"participant_limit": None, "difficulty": None, "guidelines": None}

_VI_DAY_MAP = {
    "chủ nhật": "Sunday",
    "chu nhat": "Sunday",
    "thứ hai": "Monday",
    "thu hai": "Monday",
    "thứ 2": "Monday",
    "thu 2": "Monday",
    "thứ ba": "Tuesday",
    "thu ba": "Tuesday",
    "thứ 3": "Tuesday",
    "thu 3": "Tuesday",
    "thứ tư": "Wednesday",
    "thu tu": "Wednesday",
    "thứ 4": "Wednesday",
    "thu 4": "Wednesday",
    "thứ năm": "Thursday",
    "thu nam": "Thursday",
    "thứ 5": "Thursday",
    "thu 5": "Thursday",
    "thứ sáu": "Friday",
    "thu sau": "Friday",
    "thứ 6": "Friday",
    "thu 6": "Friday",
    "thứ bảy": "Saturday",
    "thu bay": "Saturday",
    "thứ 7": "Saturday",
    "thu 7": "Saturday",
}


def _predetect_day(text: str):
    """Return the English weekday name if a Vietnamese/English day name is found in text, else None."""
    t = text.lower()
    if any(w in t for w in ("tối nay", "hôm nay", "tonight", "today", "bây giờ", "ngay bây giờ", "ngay lúc này", "lúc này", "right now", "ngay", "luôn")):
        return "today"
    if any(w in t for w in ("ngày mai", "tomorrow")):
        return "tomorrow"
    for vi, en in _VI_DAY_MAP.items():
        if vi in t:
            return en
    return None


def extract_activity_from_text(text: str) -> dict:
    """
    Parses unstructured text to extract activity properties.
    Returns null for required fields that are genuinely missing, and a
    "missing_fields" list so callers know what still needs to be collected.

    Required fields: activity_type, start_time, location
    Optional fields: required_players (default 2), title (auto-generated)
    """
    predetected_day = _predetect_day(text)

    system_prompt = """You are an Activity Extraction Agent. Extract structured fields from a short activity message.
Return ONLY a valid JSON object. No markdown, no extra text.

Fields:
1. "activity_type": string, lower-case (e.g. "football", "badminton", "yoga", "board games", "swimming"). If genuinely unclear, use null.
2. "start_time": string, HH:MM 24-hour format (e.g. "18:00", "19:30"). If not stated, use null.
3. "location": string (e.g. "Rooftop", "Gym Room A"). If not stated, use null.
4. "required_players": integer, additional players needed. If not stated, use 2.
5. "title": short English title (e.g. "Football Session", "Swimming with Friends", "Board Game Night"). MUST be in English regardless of input language. Derive from activity_type; use null only if activity_type is also null.
6. "location_type": "on_campus" if the location is a company/VNG facility (company pool, rooftop, gym, yoga studio, football field, meeting room, canteen, any VNG building), otherwise "off_campus". Default to "off_campus" if unclear.
7. "missing_fields": list of required field names whose value is null. Only include: "activity_type", "start_time", "location".
8. "day_of_week": the day the user wants the activity on. Use English weekday names exactly:
   - "today" if user says "tối nay", "hôm nay", "tonight", "today"
   - "tomorrow" if user says "ngày mai", "tomorrow"
   - "Monday" for thứ 2 / thứ hai / Monday
   - "Tuesday" for thứ 3 / thứ ba / Tuesday
   - "Wednesday" for thứ 4 / thứ tư / Wednesday
   - "Thursday" for thứ 5 / thứ năm / Thursday
   - "Friday" for thứ 6 / thứ sáu / Friday
   - "Saturday" for thứ 7 / thứ bảy / Saturday
   - "Sunday" for chủ nhật / Sunday
   - null if no specific day is mentioned

Example — Friday evening:
{"activity_type":"football","start_time":"19:00","location":"Rooftop","required_players":3,"title":"Football Session","location_type":"on_campus","day_of_week":"Friday","missing_fields":[]}

Example — all present, off-campus, no day:
{"activity_type":"football","start_time":"18:00","location":"Rooftop","required_players":3,"title":"Football Session","location_type":"on_campus","day_of_week":null,"missing_fields":[]}

Example — time and location missing:
{"activity_type":"badminton","start_time":null,"location":null,"required_players":2,"title":"Badminton Game","location_type":"off_campus","day_of_week":null,"missing_fields":["start_time","location"]}

Example — off-campus swim tomorrow:
{"activity_type":"swimming","start_time":"18:00","location":"Tao Dan Pool","required_players":2,"title":"Swimming Session","location_type":"off_campus","day_of_week":"tomorrow","missing_fields":[]}
"""

    day_hint = f'\n\nIMPORTANT: The pre-detected day from the text is "{predetected_day}". Set "day_of_week" to exactly this value.' if predetected_day else ""
    user_prompt = f"Extract details from this text: '{text}'{day_hint}"

    result_str = llm_client.run_agent(system_prompt, user_prompt)

    cleaned = result_str.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        required = ["activity_type", "start_time", "location"]
        missing = [f for f in required if data.get(f) is None]
        # Always trust pre-detected day over LLM output — LLM misreads Vietnamese day names
        day_of_week = predetected_day if predetected_day else data.get("day_of_week")
        return {
            "activity_type": data.get("activity_type"),
            "start_time": data.get("start_time"),
            "location": data.get("location"),
            "required_players": int(data.get("required_players") or 2),
            "title": data.get("title"),
            "location_type": data.get("location_type", "off_campus"),
            "day_of_week": day_of_week,
            "missing_fields": missing,
        }
    except Exception as e:
        print(f"Error parsing JSON from Extraction Agent: {e}. Raw: {cleaned}")
        activity_type = "football" if "foot" in text.lower() else "swimming" if "swim" in text.lower() else None
        fallback_missing = ["start_time", "location"]
        if activity_type is None:
            fallback_missing.insert(0, "activity_type")
        return {
            "activity_type": activity_type,
            "start_time": None,
            "location": None,
            "required_players": 2,
            "title": f"{activity_type.capitalize()} Session" if activity_type else None,
            "location_type": "off_campus",
            "day_of_week": None,
            "missing_fields": fallback_missing,
        }
