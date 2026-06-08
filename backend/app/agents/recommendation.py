from typing import List, Dict, Any
from backend.app.models import User
from backend.app.agents.llm import llm_client

def generate_recommendation_response(
    user: User,
    scored_recommendations: List[Dict[str, Any]],
    discovery_note: str,
    memories: List[str],
    user_query: str = "",
    in_routine_trap: bool = False,
    dominant_type: str = None
) -> str:
    """
    Formulates the final recommendation chat message.
    Lists all activities ranked by score without natural language justifications.
    """
    if not scored_recommendations:
        return "I couldn't find any activities happening on this day. Try creating a new activity!"

    system_prompt = """
    You are a Thoughtful Companion helping employees discover after-work experiences, communities, and networking opportunities.
    You are NOT a corporate assistant or search engine. Keep responses concise, friendly, encouraging, and natural. Avoid corporate jargon and sounding robotic.
    
    CRITICAL FORMAT RULES:
    1. Do NOT output any raw numeric scores (e.g., "Match Score: 0.72" or "Score = 0.82" are strictly FORBIDDEN).
    2. Do NOT say robotic terms like "similarity score is high" or "activity matched successfully."
    3. List the recommended activities in a clean, numbered format in descending order of their suitability.
    4. For each activity, describe its start and end times and location naturally, followed by a concise (1-2 sentences) natural explanation of why it is an interesting opportunity (e.g., connecting with people from specific sibling departments, trying something new to break a routine, or finding a familiar match).
    
    Example output format:
    Tonight, there are two interesting opportunities worth exploring:
    
    1. **Chess Gathering** from 18:00 to 19:30 (Location: Pantry Area). This has participants from BIZ and PCT, which is a great chance to meet people outside your squad.
    2. **Yoga** from 19:00 to 20:00 (Location: Gym Room A). If you're looking for something familiar to stay active, this is a perfect choice.
    
    CRITICAL RULE (The "Uncomfort Zone" Pass):
    If the user is in a routine trap (flagged in user prompt), you MUST prepend the response with this exact banner on a new line:
    ⚡ **UNCOMFORT ZONE PASS ACTIVATED** ⚡
    followed by a brief, encouraging 1-sentence note calling out their dominant habit and challenging them to break their streak by trying one of the alternative recommended communities tonight.
    """

    # Format user history summary and scored activities for the prompt
    recommendations_str = ""
    for idx, item in enumerate(scored_recommendations, 1):
        info = item["info"]
        social_note = item.get("social_note", "")
        day_str = f" on {info['day_info']}" if 'day_info' in info else ""
        
        recommendations_str += f"""
        {idx}. {info['title']} (Type: {info['type']}, Start: {info['start_time']}, End: {info['end_time']}{day_str}, Location: {info['location']})
           - Social/Networking opportunity context: {social_note}
        """

    user_prompt = f"""
    User Query: {user_query}
    User: {user.full_name} ({user.title}, Department: {user.department}, Squad: {user.squad})
    User Discovery Habit Insight: {discovery_note}
    Routine Trap Status: In Routine Trap = {in_routine_trap} (Dominant Habit: {dominant_type})
    
    Ranked Candidate Activities:
    {recommendations_str}
    
    Formulate the final response. Follow all personality and style guidelines. Do NOT include raw scores.
    """
    
    if llm_client.is_mock:
        # Default mock response fallback
        return llm_client.run_agent("", user_prompt)

    return llm_client.run_agent(system_prompt, user_prompt)
