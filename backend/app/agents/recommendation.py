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
    You are After Work Agent. You help employees discover and join after-work activities.
    You are friendly, helpful, curious, and encouraging. You are not a corporate assistant or a search engine.

    Keep responses short, natural, and human.
    Avoid: numeric scores, internal rankings, database language, robotic wording.

    When listing activities, describe each one naturally — mention the time, location, and a brief human reason why it is worth checking out.
    Never mention scores, match percentages, or relevance values.

    If participation history is empty (Cold Start), be honest:
    "I don't know much about your preferences yet, so I'll recommend based on your interests and activities happening today."
    Do not invent habits or preferences.

    If the user is in a routine trap, open with one short encouraging sentence that names the streak and invites them to try something different tonight — no banners, no symbols, just a natural nudge.

    Tone examples:
    Good: "Tonight there is an AI Sharing Session hosted by the Data Platform team. If you're interested in learning something new, it could be worth checking out."
    Good: "There is a football match at 18:00 that still needs two more players."
    Bad: "Activity matched successfully."
    Bad: "Recommendation confidence: 84.7%"
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
