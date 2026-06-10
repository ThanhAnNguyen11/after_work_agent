from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models import User, Activity, FixedActivity, ActivityParticipant, Memory, RecommendationLog
from backend.app.org_utils import calculate_recommendation_score, organization_distance
from backend.app.agents.extraction import extract_activity_from_text
from backend.app.agents.discovery import run_discovery_agent
from backend.app.agents.social_opp import run_social_opportunity_agent
from backend.app.agents.recommendation import generate_recommendation_response
from backend.app.agents.reflection import run_reflection_agent
from backend.app.agents.llm import llm_client

# Define the state shape
class AgentState(TypedDict):
    user_id: int
    message: str
    intent: str       # "extract" or "recommend"
    user_intent: str  # "exercise" | "learning" | "networking" | "relaxation" | "exploration"
    response: str

    # Internal variables passed between nodes
    user_data: Optional[Dict[str, Any]]
    available_activities: List[Dict[str, Any]]
    discovery_note: str
    social_notes: Dict[int, str]  # activity_id -> note
    scored_recommendations: List[Dict[str, Any]]
    memories: List[str]

# --- NODES ---

def intent_detector(state: AgentState) -> Dict[str, Any]:
    """
    Classifies the user input into routing intent (extract/recommend) and
    semantic user intent (exercise/learning/networking/relaxation/exploration).
    """
    message = state["message"].lower()

    # --- Heuristic: detect activity-creation signals ---
    creation_signals = [
        "at 6pm", "at 6 pm", "at 7pm", "at 5pm", "at 18:00", "at 19:00",
        "need 2 more", "need 3 more", "need more players", "need players",
        "anyone want to play", "football at", "badminton at", "board games at",
        "swimming at", "pool at", "swim at"
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

    # --- LLM classification (overrides heuristics when API is available) ---
    if not llm_client.is_mock:
        system_prompt = """You are an Intent Classifier for an after-work activity assistant.

Classify the user message into exactly ONE of these labels:
- EXTRACT: user is announcing/posting an activity to register (e.g. "Football at 6PM, need 2 more players")
- EXERCISE: user wants physical activity (gym, football, yoga, running, swimming, badminton...)
- LEARNING: user wants educational or skill-building events (AI talk, study group, workshop...)
- NETWORKING: user wants to meet new people or connect cross-department
- RELAXATION: user wants to unwind (coffee chat, board games, casual hangout...)
- EXPLORATION: user has no specific preference or is just browsing what's available

Respond with exactly one word from the list above. No explanation."""

        llm_response = llm_client.run_agent(system_prompt, f"Message: '{state['message']}'").strip().upper()

        if "EXTRACT" in llm_response:
            is_extraction = True
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

    intent = "extract" if is_extraction else "recommend"
    return {"intent": intent, "user_intent": user_intent}

def extraction_node(state: AgentState) -> Dict[str, Any]:
    """
    Extracts the activity details from the post, saves it to the database,
    and returns a success response.
    """
    db = SessionLocal()
    try:
        user_id = state["user_id"]
        message = state["message"]
        
        # Run Extraction Agent
        extracted = extract_activity_from_text(message)
        
        # Calculate start time date (default to tonight)
        now = datetime.now()
        hour, minute = map(int, extracted["start_time"].split(":"))
        start_time = datetime(now.year, now.month, now.day, hour, minute)
        
        # If the start time has already passed today, set it to tomorrow
        if start_time < now:
            start_time += timedelta(days=1)
            
        # Determine participant limit (creator joins automatically)
        participant_limit = extracted.get("required_players", 2) + 1
        
        # Create Activity record
        activity = Activity(
            title=extracted["title"],
            description=f"Auto-extracted from chat: '{message}'",
            activity_type=extracted["activity_type"],
            start_time=start_time,
            end_time=start_time + timedelta(hours=1),
            location=extracted["location"],
            participant_limit=participant_limit,
            current_participants=1,
            created_by=user_id
        )
        
        db.add(activity)
        db.flush()  # Get activity.id
        
        # Automatically join the creator as participant
        join_record = ActivityParticipant(
            activity_id=activity.id,
            user_id=user_id
        )
        db.add(join_record)
        db.commit()
        
        response = (
            f"🎉 **Activity Created successfully!**\n\n"
            f"I have registered your activity:\n"
            f"- **Title**: {activity.title}\n"
            f"- **Type**: {activity.activity_type.capitalize()}\n"
            f"- **Time**: {activity.start_time.strftime('%Y-%m-%d %H:%M')}\n"
            f"- **Location**: {activity.location}\n"
            f"- **Spots**: 1 joined (Host), looking for {extracted['required_players']} more players."
        )
        return {"response": response}
    except Exception as e:
        db.rollback()
        return {"response": f"Sorry, I encountered an error creating the activity: {e}"}
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
            
        # Get user history (participated activities)
        participated_records = db.query(ActivityParticipant).filter(ActivityParticipant.user_id == user_id).all()
        history_ids = [p.activity_id for p in participated_records]
        
        history = db.query(Activity).filter(Activity.id.in_(history_ids)).all() if history_ids else []
        
        # Get memories
        user_memories = db.query(Memory).filter(Memory.user_id == user_id).all()
        memories_list = [m.content for m in user_memories]
        
        # Determine target date from query keywords (tomorrow or specific weekdays)
        now = datetime.now()
        target_date = now
        has_specific_day = False
        
        message_clean = message.lower()
        if "tomorrow" in message_clean:
            target_date = now + timedelta(days=1)
            has_specific_day = True
        else:
            weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            for i, w in enumerate(weekdays):
                if w in message_clean:
                    current_weekday = now.weekday()  # Monday is 0, Sunday is 6
                    target_weekday_idx = i  # Monday is 0, Sunday is 6
                    days_ahead = target_weekday_idx - current_weekday
                    if days_ahead <= 0:  # target day is earlier this week or today, shift to next week
                        days_ahead += 7
                    target_date = now + timedelta(days=days_ahead)
                    has_specific_day = True
                    break
            
        if has_specific_day:
            target_weekday = target_date.strftime("%A")  # e.g., "Monday"
            target_date_only = target_date.date()
            
            # Load upcoming dynamic activities happening on the target date
            upcoming_activities = db.query(Activity).filter(
                Activity.start_time >= datetime(target_date_only.year, target_date_only.month, target_date_only.day, 0, 0),
                Activity.start_time <= datetime(target_date_only.year, target_date_only.month, target_date_only.day, 23, 59)
            ).all()
            
            # Load active gym classes scheduled for the target weekday
            gym_classes = db.query(FixedActivity).filter(FixedActivity.active == True).all()
            filtered_gym_classes = [gc for gc in gym_classes if target_weekday in gc.weekday]
        else:
            # General query with no specific day: load activities for next 7 days and all gym classes
            upcoming_activities = db.query(Activity).filter(
                Activity.start_time >= datetime(now.year, now.month, now.day, 0, 0),
                Activity.start_time <= datetime(now.year, now.month, now.day, 23, 59) + timedelta(days=7)
            ).all()
            
            filtered_gym_classes = db.query(FixedActivity).filter(FixedActivity.active == True).all()
            
        # Format activities & classes into clean contexts for scoring
        candidate_activities = []
        
        for act in upcoming_activities:
            # Get other participants in this activity
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
            
        for gc in filtered_gym_classes:
            candidate_activities.append({
                "type": "gym_class",
                "obj": gc,
                "peers": [],
                "creator": None,
                "title": f"Gym Class: {gc.class_name}",
                "activity_type": "gym",
                "start_time": gc.start_time,
                "end_time": gc.end_time if gc.end_time else "13:00",
                "location": gc.location,
                "id": gc.id,
                "day_info": gc.weekday
            })
            
        # Save user fields to state (convert models to serializable dicts where needed)
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
        
        return {
            "user_data": user_dict,
            "available_activities": candidate_activities,
            "memories": memories_list
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
        
        # Fetch history models
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
                # Get the actual database peers loaded
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
    """
    db = SessionLocal()
    try:
        user_id = state["user_id"]
        user = db.query(User).filter(User.id == user_id).first()
        available = state["available_activities"]
        discovery_note = state["discovery_note"]
        social_notes = state.get("social_notes", {})
        memories = state["memories"]
        
        # Load user history models for score calculation
        p_records = db.query(ActivityParticipant).filter(ActivityParticipant.user_id == user_id).all()
        history_ids = [p.activity_id for p in p_records]
        history = db.query(Activity).filter(Activity.id.in_(history_ids)).all() if history_ids else []
        
        scored_list = []
        for item in available:
            obj = None
            if item["type"] == "dynamic":
                obj = db.query(Activity).filter(Activity.id == item["id"]).first()
                # Get peers
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
            
            # Format info dict
            info = {
                "title": item["title"],
                "type": item["activity_type"],
                "start_time": item["start_time"],
                "end_time": item.get("end_time", ""),
                "location": item["location"],
                "class_type": item["type"],
                "id": item["id"]
            }
            
            scored_list.append({
                "info": info,
                "scores": scores,
                "social_note": social_notes.get(item["id"], "") if item["type"] == "dynamic" else ""
            })
            
        # Sort by final score descending
        scored_list.sort(key=lambda x: x["scores"]["final_score"], reverse=True)
        
        in_routine_trap = False
        dominant_type = None
        if scored_list:
            in_routine_trap = scored_list[0]["scores"].get("in_routine_trap", False)
            dominant_type = scored_list[0]["scores"].get("dominant_type", None)
            
            # If the user query specifically mentions an activity type or class name, disable the routine trap banner
            message = state.get("message", "")
            if message:
                msg_clean = message.lower()
                for item in scored_list:
                    act_name = item["info"]["title"].lower()
                    act_type = item["info"]["type"].lower()
                    if act_type in msg_clean or act_name in msg_clean or (act_type == "gym" and "yoga" in msg_clean) or "swim" in msg_clean or "pool" in msg_clean:
                        in_routine_trap = False
                        break

        # Run Recommendation LLM
        response = generate_recommendation_response(
            user=user,
            scored_recommendations=scored_list,
            discovery_note=discovery_note,
            memories=memories,
            user_query=state.get("message", ""),
            in_routine_trap=in_routine_trap,
            dominant_type=dominant_type,
            user_intent=state.get("user_intent", "")
        )
        
        # Log presented recommendations
        for item in scored_list[:3]:
            info = item["info"]
            act_id = info["id"] if info["class_type"] == "dynamic" else None
            gym_id = info["id"] if info["class_type"] == "gym_class" else None
            
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            existing = db.query(RecommendationLog).filter(
                RecommendationLog.user_id == user_id,
                RecommendationLog.activity_id == act_id,
                RecommendationLog.gym_class_id == gym_id,
                RecommendationLog.recommended_at >= today_start
            ).first()
            
            if not existing:
                log = RecommendationLog(
                    user_id=user_id,
                    activity_id=act_id,
                    gym_class_id=gym_id,
                    status="shown"
                )
                db.add(log)
        db.commit()

        return {
            "scored_recommendations": scored_list,
            "response": response
        }
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
            # Check if this memory already exists for the user
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

# --- DEFINE GRAPH ---

builder = StateGraph(AgentState)

# Add Nodes
builder.add_node("intent_detector", intent_detector)
builder.add_node("extraction_node", extraction_node)
builder.add_node("load_user_context", load_user_context)
builder.add_node("discovery_node", discovery_node)
builder.add_node("social_opp_node", social_opp_node)
builder.add_node("recommendation_node", recommendation_node)
builder.add_node("reflection_node", reflection_node)

# Add Edges
builder.set_entry_point("intent_detector")

# Define conditional route from intent
def route_intent(state: AgentState) -> str:
    if state["intent"] == "extract":
        return "extraction_node"
    else:
        return "load_user_context"

builder.add_conditional_edges(
    "intent_detector",
    route_intent,
    {
        "extraction_node": "extraction_node",
        "load_user_context": "load_user_context"
    }
)

# Standard sequential edges
builder.add_edge("extraction_node", END)

builder.add_edge("load_user_context", "discovery_node")
builder.add_edge("discovery_node", "social_opp_node")
builder.add_edge("social_opp_node", "recommendation_node")

builder.add_edge("recommendation_node", "reflection_node")
builder.add_edge("reflection_node", END)

# Compile
compiled_graph = builder.compile()

def run_agent_flow(user_id: int, message: str) -> str:
    """
    Main entry point to execute the LangGraph workflow.
    """
    initial_state = {
        "user_id": user_id,
        "message": message,
        "intent": "",
        "user_intent": "",
        "response": "",
        "user_data": None,
        "available_activities": [],
        "discovery_note": "",
        "social_notes": {},
        "scored_recommendations": [],
        "memories": []
    }
    
    final_state = compiled_graph.invoke(initial_state)
    return final_state["response"]
