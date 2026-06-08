import json
from backend.app.agents.llm import llm_client

def extract_activity_from_text(text: str) -> dict:
    """
    Parses unstructured text to extract activity properties.
    Input example: "Football at 6PM. Need 2 more players."
    Output example: {
        "activity_type": "football",
        "start_time": "18:00",
        "required_players": 2,
        "location": "Company Ground",
        "title": "Football Match"
    }
    """
    system_prompt = """
    You are an Activity Extraction Agent. Your task is to analyze a short message proposing an after-work activity and extract structured key fields.
    Return ONLY a valid JSON object. Do not include any introductory or concluding text, or markdown code blocks.
    
    Fields to extract:
    1. "activity_type": string, lower-case (e.g., "football", "gym", "badminton", "board games", "yoga", "running", "coffee", "ai"). If not specified, categorize it logically.
    2. "start_time": string, HH:MM format (24-hour clock, e.g. "18:00", "18:30"). If not specified, default to "18:00".
    3. "required_players": integer, the number of additional players/participants needed. If not specified or implied, use a default like 2.
    4. "title": string, a short catchy title for the activity (e.g., "Football Game", "Board Game Gather").
    5. "location": string, location if mentioned (e.g., "Pantry", "Gym Room A"). If not mentioned, default to "Company Premises" or "Nearby Field".

    Example Input: "Football at 6PM. Need 2 more players."
    Example Output:
    {"activity_type": "football", "start_time": "18:00", "required_players": 2, "title": "Football Game", "location": "Nearby Football Field"}
    """
    
    user_prompt = f"Extract details from this text: '{text}'"
    
    result_str = llm_client.run_agent(system_prompt, user_prompt, expected_format="json")
    
    # Strip markdown block if model accidentally included it
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
        # Ensure fallback defaults exist
        return {
            "activity_type": data.get("activity_type", "other"),
            "start_time": data.get("start_time", "18:00"),
            "required_players": int(data.get("required_players", 2)),
            "title": data.get("title", f"{data.get('activity_type', 'Activity').capitalize()} Session"),
            "location": data.get("location", "Company Premises")
        }
    except Exception as e:
        print(f"Error parsing JSON from Extraction Agent: {e}. Raw: {cleaned}")
        # Fallback to local regex-based logic if LLM output fails
        return {
            "activity_type": "football" if "foot" in text.lower() else "gym",
            "start_time": "18:00",
            "required_players": 2,
            "title": "Extracted Activity",
            "location": "Company Premises"
        }
