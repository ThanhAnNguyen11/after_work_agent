from typing import List
from backend.app.models import Activity
from backend.app.agents.llm import llm_client

def run_discovery_agent(user_name: str, interests: List[str], history: List[Activity]) -> str:
    """
    Analyzes the user's activity history and interests.
    Determines if they are stuck in a routine (e.g., gym-only) and suggests exploratory directions.
    """
    if not history:
        return "New employee: Encourage general exploration across different department socials and technical groups."

    # Programmatic detection of routine traps
    types = [act.activity_type.lower() for act in history]
    from collections import Counter
    counts = Counter(types)
    
    total = len(history)
    dominant_type = None
    dominant_ratio = 0.0
    
    if total > 0:
        most_common = counts.most_common(1)[0]
        dominant_type = most_common[0]
        dominant_ratio = most_common[1] / total

    # If user does the same activity type more than 70% of the time, they are in a routine
    in_routine = total >= 3 and dominant_ratio >= 0.7

    system_prompt = """
    You are a Discovery Agent for after-work events. Your goal is to help employees break repetitive patterns and try new things.
    Review the user's history, dominant activity habits, and interests, and write a single short routine-breaking recommendation paragraph.
    Explain why they should explore a new category (e.g., if they only go to the gym, suggest a social activity like board games or a study group).
    """

    user_prompt = f"""
    User: {user_name}
    Interests: {interests}
    Total activities attended: {total}
    Participation breakdown: {dict(counts)}
    Is in a routine trap: {in_routine} (Dominant activity: '{dominant_type}' at {dominant_ratio:.1%})
    
    Write a 1-2 sentence recommendation advising them to try a different category, pointing out their consistent routine.
    """

    # If in mock mode or API is off, we can run a quick fallback
    if llm_client.is_mock:
        if in_routine and dominant_type == "gym":
            return "You have attended gym activities consistently. I recommend trying a social activity like Board Game Night or a study group to meet new colleagues and balance your fitness routine."
        else:
            return "You've been active in your core areas. Trying a dynamic coffee talk or running session is a great way to branch out."

    return llm_client.run_agent(system_prompt, user_prompt)
