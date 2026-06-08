from typing import Optional
from backend.app.agents.llm import llm_client

def run_reflection_agent(user_query: str) -> Optional[str]:
    """
    Analyzes the user's chat message to see if it contains preference shifts,
    routines, or new constraints.
    Returns a memory string to be saved, or None if no persistent memory was detected.
    """
    # Simple keyword heuristic check to save LLM tokens/calls if mock or simple message
    lowered = user_query.lower()
    indicative_phrases = ["bored of", "bored with", "prefer", "usually", "want to meet", "hate", "love", "like to", "don't like"]
    
    has_indicator = any(phrase in lowered for phrase in indicative_phrases)
    if not has_indicator:
        return None

    system_prompt = """
    You are a Reflection Agent. Your goal is to analyze an employee's chat message and extract any persistent preferences, habits, routines, or feelings they express about after-work activities.
    
    If the user expresses a habit, preference, or emotional state about an activity (e.g., "I am bored of going to the gym every day", "I usually play football on Tuesdays", "I want to meet people from Product"), extract it into a first-person statement.
    If no new permanent preference or habit is expressed, respond with exactly "NONE".
    Do not output any introductory text or explanation, just the statement or "NONE".
    
    Examples:
    Input: "I am bored of going to the gym every day."
    Output: "I am bored of going to the gym every day."
    
    Input: "Do you have any football games?"
    Output: "NONE"
    """

    user_prompt = f"Analyze this user query: '{user_query}'"

    if llm_client.is_mock:
        # Custom mock parser
        if "bored" in lowered and "gym" in lowered:
            return "I am bored of going to the gym every day."
        elif "football" in lowered and "usually" in lowered:
            return "I usually play football on Tuesdays."
        elif "meet" in lowered and "product" in lowered:
            return "I want to meet more people from Product."
        return None

    response = llm_client.run_agent(system_prompt, user_prompt).strip()
    
    if response == "NONE" or not response or len(response) > 100:
        return None
        
    return response
