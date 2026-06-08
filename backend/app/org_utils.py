from typing import List, Dict, Any
from backend.app.models import User, Activity, GymClass

def organization_distance(user_a: User, user_b: User) -> float:
    """
    Calculate organizational distance/closeness between two users.
    Scoring:
    - Same Squad: 1.0
    - Same Department: 0.8
    - Same Group: 0.5
    - Cross Group (Same Company): 0.2
    - Cross Company: 0.0
    """
    if not user_a or not user_b:
        return 0.0
        
    # Same Squad (squad is nullable, so ensure both are not None/empty before matching)
    if (user_a.squad and user_b.squad and 
            user_a.squad.strip().lower() == user_b.squad.strip().lower()):
        return 1.0
        
    # Same Department
    if (user_a.department and user_b.department and 
            user_a.department.strip().lower() == user_b.department.strip().lower()):
        return 0.8
        
    # Same Group
    if (user_a.org_group and user_b.org_group and 
            user_a.org_group.strip().lower() == user_b.org_group.strip().lower()):
        return 0.5
        
    # Same Company (Cross Group)
    if (user_a.company and user_b.company and 
            user_a.company.strip().lower() == user_b.company.strip().lower()):
        return 0.2
        
    return 0.0

def calculate_recommendation_score(
    user: User, 
    activity_or_class: Any, 
    user_history: List[Activity], 
    participants: List[User] = None,
    creator: User = None,
    user_query: str = ""
) -> Dict[str, Any]:
    """
    Calculate the recommendation score based on the formula:
    score = 0.4 * interest_match + 0.3 * activity_relevance + 0.2 * social_connection + 0.1 * discovery_score
    
    Returns a dictionary with the final score and sub-scores for transparency.
    """
    is_gym_class = isinstance(activity_or_class, GymClass)
    
    # Detect if user is in a routine trap (3+ activities, 70%+ of one type)
    in_routine_trap = False
    dominant_type = None
    if user_history and len(user_history) >= 3:
        types = [act.activity_type.lower() for act in user_history]
        from collections import Counter
        counts = Counter(types)
        most_common = counts.most_common(1)[0]
        dominant_ratio = most_common[1] / len(user_history)
        if dominant_ratio >= 0.7:
            in_routine_trap = True
            dominant_type = most_common[0]
            
    # 1. Interest Match
    # Clean user interests
    user_interests = [i.strip().lower() for i in user.interests]
    
    if is_gym_class:
        class_name = activity_or_class.class_name.lower()
        # Direct match: class name in user interests (e.g. "yoga")
        if class_name in user_interests:
            interest_match = 1.0
        # If user is interested in "gym" in general, but this is a gym class
        elif "gym" in user_interests:
            interest_match = 0.8
        else:
            interest_match = 0.0
    else:
        act_type = activity_or_class.activity_type.lower()
        if act_type in user_interests:
            interest_match = 1.0
        # Check if the title has any interest words
        elif any(interest in activity_or_class.title.lower() for interest in user_interests):
            interest_match = 0.8
        # If it's a sports activity (e.g., football) and user likes "sports"
        elif act_type == "football" and "sports" in user_interests:
            interest_match = 0.9
        else:
            interest_match = 0.0

    # 2. Activity Relevance (History)
    # Calculate what fraction of user's past activities match this type
    if not user_history:
        # If no history, default to neutral score
        activity_relevance = 0.3
    else:
        target_type = activity_or_class.class_name.lower() if is_gym_class else activity_or_class.activity_type.lower()
        
        # Count matches in history
        match_count = 0
        for past_act in user_history:
            past_type = past_act.activity_type.lower()
            
            def is_gym(t):
                return t in ["yoga", "body combat", "zumba", "gym"]
                
            if target_type == past_type or (is_gym(target_type) and is_gym(past_type)):
                match_count += 1
                
        # Relevance is the ratio (capped at 1.0)
        activity_relevance = min(match_count / len(user_history), 1.0)
        # Give a small boost if they have no participation in this but it matches interest
        if activity_relevance == 0.0 and interest_match > 0:
            activity_relevance = 0.2

    # 3. Social Connection
    # Measures the average organizational closeness of other participants
    if participants:
        # Exclude the current user from the peer list if they are in there
        other_peers = [p for p in participants if p.id != user.id]
        if other_peers:
            distances = [organization_distance(user, peer) for peer in other_peers]
            social_connection = sum(distances) / len(distances)
        else:
            # Only the user has joined, or no other participants
            if creator and creator.id != user.id:
                social_connection = organization_distance(user, creator)
            else:
                social_connection = 0.0
    else:
        # No participants yet
        if not is_gym_class and creator and creator.id != user.id:
            social_connection = organization_distance(user, creator)
        else:
            social_connection = 0.0

    # 4. Discovery Score (Routine Breaking)
    # Discovery is high when the user does NOT regularly join this activity type
    if not user_history:
        discovery_score = 0.8  # New users get high discovery potential
    else:
        discovery_score = 1.0 - activity_relevance
        
    # Calculate weighted total score
    final_score = (
        0.4 * interest_match +
        0.3 * activity_relevance +
        0.2 * social_connection +
        0.1 * discovery_score
    )
    
    # Routine Interrupter (The "Uncomfort Zone" Pass)
    if in_routine_trap:
        candidate_type = "gym" if is_gym_class else activity_or_class.activity_type.lower()
        
        # Check if the query specifically mentions this activity type or class name
        is_explicitly_asking = False
        if user_query:
            q_clean = user_query.lower()
            name_to_check = activity_or_class.class_name.lower() if is_gym_class else activity_or_class.activity_type.lower()
            if name_to_check in q_clean or (name_to_check == "gym" and is_gym_class and activity_or_class.class_name.lower() in q_clean):
                is_explicitly_asking = True
                
        if is_explicitly_asking:
            # Do not penalize if the user explicitly asked about it
            pass
        elif candidate_type == dominant_type:
            # Zero out relevance and penalize dominant category to force variety
            activity_relevance = 0.0
            final_score = 0.4 * interest_match + 0.2 * social_connection + 0.1 * discovery_score - 0.2
        else:
            # Apply dynamic Uncomfort Zone breaking bonus to novelty options
            final_score += 0.35

    final_score = max(0.0, min(1.0, final_score))

    return {
        "final_score": round(final_score, 3),
        "interest_match": round(interest_match, 3),
        "activity_relevance": round(activity_relevance, 3),
        "social_connection": round(social_connection, 3),
        "discovery_score": round(discovery_score, 3),
        "in_routine_trap": in_routine_trap,
        "dominant_type": dominant_type
    }
