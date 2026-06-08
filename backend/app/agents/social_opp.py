from typing import List, Dict, Any
from backend.app.models import User
from backend.app.agents.llm import llm_client

def run_social_opportunity_agent(
    user: User, 
    activity_title: str, 
    participants: List[User]
) -> str:
    """
    Analyzes participants in a prospective activity.
    If participants belong to other squads/departments, generates a networking/social pitch.
    """
    if not participants:
        return "This is a new activity. You can be the first to join and invite colleagues from your department!"

    # Identify departments/squads of participants
    other_orgs = []
    cross_dept_count = 0
    
    for p in participants:
        if p.id == user.id:
            continue
        # Get their squad/department label
        label = p.squad if p.squad else p.department
        if label:
            other_orgs.append(label)
        
        # Check if cross department
        if p.department != user.department:
            cross_dept_count += 1

    unique_orgs = list(set(other_orgs))
    
    if not unique_orgs:
        return ""
        
    system_prompt = """
    You are a Social Opportunity Agent. Your goal is to help employees network across organizational silos.
    Review the current user's squad/department and the list of departments participating in a specific activity.
    Generate a 1-sentence highlight explaining why this activity is a great social networking opportunity (e.g. "Meet colleagues from Product and BIZ to expand your network beyond Consumer Solutions").
    """

    user_prompt = f"""
    Current User Department/Squad: {user.squad if user.squad else user.department}
    Activity: {activity_title}
    Participants' squads/departments: {unique_orgs}
    Number of cross-department colleagues: {cross_dept_count}
    
    Write a single sentence focusing on networking and breaking team boundaries. Keep it brief.
    """

    if llm_client.is_mock:
        if cross_dept_count > 0:
            orgs_str = ", ".join(unique_orgs)
            return f"This activity expands your network beyond {user.squad if user.squad else user.department} as members from {orgs_str} are participating."
        else:
            return "Perfect chance to hang out with members from your own division."

    return llm_client.run_agent(system_prompt, user_prompt)
