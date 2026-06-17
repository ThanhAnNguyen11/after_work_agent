from typing import List, Dict, Any, Optional
from backend.app.models import User, Activity, FixedActivity

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

INTENT_WEIGHTS = {
    "exercise":    {"interest": 0.45, "relevance": 0.40, "social": 0.10, "discovery": 0.05},
    "learning":    {"interest": 0.40, "relevance": 0.30, "social": 0.15, "discovery": 0.15},
    "networking":  {"interest": 0.25, "relevance": 0.20, "social": 0.45, "discovery": 0.10},
    "relaxation":  {"interest": 0.35, "relevance": 0.35, "social": 0.20, "discovery": 0.10},
    "exploration": {"interest": 0.30, "relevance": 0.15, "social": 0.15, "discovery": 0.40},
}
_DEFAULT_WEIGHTS = {"interest": 0.40, "relevance": 0.30, "social": 0.20, "discovery": 0.10}

def calculate_recommendation_score(
    user: User,
    activity_or_class: Any,
    user_history: List[Activity],
    participants: List[User] = None,
    creator: User = None,
    user_query: str = "",
    user_intent: str = "",
    db: Any = None
) -> Dict[str, Any]:
    """
    Calculate the recommendation score based on the formula:
    score = w_interest * interest_match + w_relevance * activity_relevance
            + w_social * social_connection + w_discovery * discovery_score

    Weights are adjusted by user_intent (exercise/learning/networking/relaxation/exploration).
    Returns a dictionary with the final score and sub-scores for transparency.
    """
    is_gym_class = isinstance(activity_or_class, FixedActivity)
    
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
    
    act_type = activity_or_class.class_name.lower() if is_gym_class else activity_or_class.activity_type.lower()

    # Category buckets for facility classes — each class maps to the broader interest(s) it satisfies
    _FACILITY_SPORTS = {"swimming", "gym", "boxing", "obstacles", "new obstacles", "abs", "body fit", "new body fit"}
    _FACILITY_DANCE  = {"fitness dance", "zumba"}
    _FACILITY_YOGA   = {"yoga"}

    # Static declared match
    declared_match = 0.0
    if is_gym_class:
        if act_type in user_interests:
            declared_match = 1.0
        elif act_type in _FACILITY_SPORTS and ("sports" in user_interests or "fitness" in user_interests or (act_type == "gym" and "gym" in user_interests)):
            declared_match = 0.8
        elif act_type in _FACILITY_DANCE and ("dance" in user_interests or "fitness" in user_interests or "zumba" in user_interests):
            declared_match = 0.8
        elif act_type in _FACILITY_YOGA and ("wellness" in user_interests or "fitness" in user_interests or "meditation" in user_interests):
            declared_match = 0.8
    else:
        if act_type in user_interests:
            declared_match = 1.0
        elif any(interest in activity_or_class.title.lower() for interest in user_interests):
            declared_match = 0.8
        elif act_type in ["football", "swimming", "badminton", "running", "gym"] and "sports" in user_interests:
            declared_match = 0.9

    # Behavioral match score
    behavioral_score = 0.0
    if db is not None:
        from backend.app.models import UserBehavioralInterest
        beh_interest = db.query(UserBehavioralInterest).filter(
            UserBehavioralInterest.user_id == user.id,
            UserBehavioralInterest.activity_type == act_type
        ).first()
        if beh_interest:
            behavioral_score = beh_interest.score

    # Determine dynamic weights based on actual participation history size
    history_count = len(user_history) if user_history else 0
    if history_count >= 3:
        # Behavioral matches gradually outweigh profile settings (declared interests)
        w_behavioral = min(0.8, history_count * 0.1)
        w_declared = 1.0 - w_behavioral
    else:
        # Cold start: rely entirely on declared static preferences
        w_behavioral = 0.0
        w_declared = 1.0

    interest_match = w_declared * declared_match + w_behavioral * behavioral_score

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
            
            def _same_category(a, b):
                # Group fitness facility classes that are interchangeable in terms of user preference
                _fitness = {"gym", "obstacles", "new obstacles", "abs", "body fit", "new body fit", "boxing"}
                _dance   = {"fitness dance", "zumba"}
                _yoga    = {"yoga"}
                for bucket in (_fitness, _dance, _yoga):
                    if a in bucket and b in bucket:
                        return True
                return False

            if target_type == past_type or _same_category(target_type, past_type):
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
        elif is_gym_class:
            social_connection = 0.3  # gym classes have real participants not tracked in DB; neutral baseline
        else:
            social_connection = 0.0

    # 4. Discovery Score (Routine Breaking)
    # Discovery is high when the user does NOT regularly join this activity type
    if not user_history:
        discovery_score = 0.8  # New users get high discovery potential
    else:
        discovery_score = 1.0 - activity_relevance
        
    # Calculate weighted total score (weights shift based on user intent)
    w = INTENT_WEIGHTS.get(user_intent.lower(), _DEFAULT_WEIGHTS)
    final_score = (
        w["interest"]   * interest_match +
        w["relevance"]  * activity_relevance +
        w["social"]     * social_connection +
        w["discovery"]  * discovery_score
    )
    
    # Routine Interrupter (The "Uncomfort Zone" Pass)
    if in_routine_trap:
        candidate_type = act_type  # already set to class_name.lower() for FixedActivity

        # Check if the query specifically mentions this activity type or class name
        is_explicitly_asking = False
        if user_query:
            q_clean = user_query.lower()
            name_to_check = act_type
            if name_to_check in q_clean:
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

    # 5. Location Type Preference (inferred from participation history)
    activity_location_type = "on_campus" if is_gym_class else getattr(activity_or_class, "location_type", "off_campus")
    location_boost = 0.0
    if user_history:
        on_campus_count = sum(1 for a in user_history if getattr(a, "location_type", "off_campus") == "on_campus")
        off_campus_count = len(user_history) - on_campus_count
        if on_campus_count > off_campus_count and activity_location_type == "on_campus":
            location_boost = 0.1
        elif off_campus_count > on_campus_count and activity_location_type == "off_campus":
            location_boost = 0.1

    final_score = max(0.0, min(1.0, final_score + location_boost))

    # Weekend boost: +0.15 for off-campus activities on Saturday/Sunday
    from datetime import date as _date
    weekend_boost = 0.15 if _date.today().weekday() in (5, 6) and activity_location_type == "off_campus" else 0.0
    final_score = max(0.0, min(1.0, final_score + weekend_boost))

    # 6. Query Keyword Boost — when user explicitly names an activity type, prioritise it
    _QUERY_KEYWORD_BOOSTS = {
        "yoga": ["yoga"],
        "swim": ["swimming"], "bơi": ["swimming"], "bơi lội": ["swimming"],
        "badminton": ["badminton"], "cầu lông": ["badminton"],
        "football": ["football"], "bóng đá": ["football"],
        "running": ["running"], "chạy": ["running"], "chạy bộ": ["running"],
        "gym": ["gym"], "thể dục": ["gym"],
        "body": ["body combat", "body fit"],
        "zumba": ["zumba"],
        "board game": ["board games"], "cờ": ["board games"],
        "coffee": ["coffee chat"], "cà phê": ["coffee chat"],
    }
    query_keyword_boost = 0.0
    if user_query:
        q_clean = user_query.lower()
        target_type = activity_or_class.class_name.lower() if is_gym_class else activity_or_class.activity_type.lower()
        for keyword, types in _QUERY_KEYWORD_BOOSTS.items():
            if keyword in q_clean and any(t in target_type for t in types):
                query_keyword_boost = 0.4
                break
    final_score = max(0.0, min(1.0, final_score + query_keyword_boost))

    return {
        "final_score": round(final_score, 3),
        "interest_match": round(interest_match, 3),
        "activity_relevance": round(activity_relevance, 3),
        "social_connection": round(social_connection, 3),
        "discovery_score": round(discovery_score, 3),
        "location_boost": round(location_boost, 3),
        "weekend_boost": round(weekend_boost, 3),
        "query_keyword_boost": round(query_keyword_boost, 3),
        "in_routine_trap": in_routine_trap,
        "dominant_type": dominant_type
    }


def apply_attempt2_filters(
    scored_list: List[Dict],
    filters: Dict[str, str],
    attempt1_shown_ids: List[int]
) -> List[Dict]:
    """
    Post-scoring filter pass for Attempt 2.
    Hard-excludes activity IDs from Attempt 1, then applies soft boosts
    based on the user's energy/social/environment/time answers.
    Re-sorts by boosted score. Returns a new list.
    """
    LOW_ENERGY_TYPES = {"yoga", "swimming", "board games", "coffee", "coffee chat", "walking"}
    HIGH_ENERGY_TYPES = {"football", "running", "badminton", "body combat", "zumba", "gym", "taekwondo"}
    INDOOR_KEYWORDS = {"studio", "room", "pantry", "indoor", "gym", "office", "meeting"}
    OUTDOOR_KEYWORDS = {"field", "court", "pool", "park", "outdoor", "lobby", "rooftop"}

    # Hard-exclude attempt 1 IDs
    candidates = [item for item in scored_list if item["info"]["id"] not in attempt1_shown_ids]
    if not candidates:
        candidates = list(scored_list)

    def filter_boost(item: Dict) -> float:
        boost = 1.0
        act_type = item["info"].get("type", "").lower()
        location = item["info"].get("location", "").lower()
        class_type = item["info"].get("class_type", "")

        if filters.get("energy") == "low" and act_type in LOW_ENERGY_TYPES:
            boost += 0.3
        elif filters.get("energy") == "high" and act_type in HIGH_ENERGY_TYPES:
            boost += 0.3

        if filters.get("social") == "solo" and class_type == "gym_class":
            boost += 0.2
        elif filters.get("social") == "group" and class_type == "dynamic":
            boost += 0.2

        env = filters.get("environment", "either")
        if env == "indoor" and any(k in location for k in INDOOR_KEYWORDS):
            boost += 0.2
        elif env == "outdoor" and any(k in location for k in OUTDOOR_KEYWORDS):
            boost += 0.2

        return boost

    boosted = []
    for item in candidates:
        boost = filter_boost(item)
        adjusted = min(1.0, item["scores"]["final_score"] * boost)
        boosted.append({**item, "scores": {**item["scores"], "final_score": adjusted}})

    boosted.sort(key=lambda x: x["scores"]["final_score"], reverse=True)
    return boosted
