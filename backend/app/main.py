from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from backend.app.database import get_db, init_db
from backend.app.models import User, Activity, GymClass, ActivityParticipant, Memory
from backend.app.schemas import (
    UserCreate, UserResponse, ActivityCreate, ActivityResponse, 
    GymClassResponse, MemoryResponse, ChatRequest, ChatResponse,
    JoinActivityRequest, JoinActivityResponse
)
from backend.app.agents.graph import run_agent_flow
from backend.app.org_utils import organization_distance

app = FastAPI(
    title="After Work Agent API",
    description="Backend API for the After Work Discovery Agent hackathon project",
    version="1.0.0"
)

# Enable CORS for Streamlit frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

# --- CHAT / AGENT ENDPOINT ---

@app.post("/api/chat", response_model=ChatResponse)
def chat_with_agent(req: ChatRequest, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    try:
        response_text = run_agent_flow(user_id=req.user_id, message=req.message)
        return ChatResponse(response=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent workflow error: {str(e)}")

# --- USER ENDPOINTS ---

@app.get("/api/users", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    # Populate the virtual interests list from raw DB property
    result = []
    for u in users:
        result.append(UserResponse(
            id=u.id,
            domain=u.domain,
            full_name=u.full_name,
            title=u.title,
            company=u.company,
            org_group=u.org_group,
            department=u.department,
            squad=u.squad,
            interests=u.interests,
            created_at=u.created_at
        ))
    return result

@app.post("/api/users", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if domain exists
    existing = db.query(User).filter(User.domain == user_in.domain).first()
    if existing:
        raise HTTPException(status_code=400, detail="User domain already exists")
        
    user = User(
        domain=user_in.domain,
        full_name=user_in.full_name,
        title=user_in.title,
        company=user_in.company,
        org_group=user_in.org_group,
        department=user_in.department,
        squad=user_in.squad
    )
    user.interests = user_in.interests
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        domain=user.domain,
        full_name=user.full_name,
        title=user.title,
        company=user.company,
        org_group=user.org_group,
        department=user.department,
        squad=user.squad,
        interests=user.interests,
        created_at=user.created_at
    )

@app.get("/api/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=u.id,
        domain=u.domain,
        full_name=u.full_name,
        title=u.title,
        company=u.company,
        org_group=u.org_group,
        department=u.department,
        squad=u.squad,
        interests=u.interests,
        created_at=u.created_at
    )

@app.put("/api/users/{user_id}/interests", response_model=UserResponse)
def update_user_interests(user_id: int, interests: List[str], db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.interests = interests
    db.commit()
    db.refresh(u)
    return UserResponse(
        id=u.id,
        domain=u.domain,
        full_name=u.full_name,
        title=u.title,
        company=u.company,
        org_group=u.org_group,
        department=u.department,
        squad=u.squad,
        interests=u.interests,
        created_at=u.created_at
    )

@app.get("/api/users/{user_id}/memories", response_model=List[MemoryResponse])
def get_user_memories(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return db.query(Memory).filter(Memory.user_id == user_id).all()

@app.get("/api/users/{user_id}/history", response_model=List[ActivityResponse])
def get_user_history(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    participants = db.query(ActivityParticipant).filter(ActivityParticipant.user_id == user_id).all()
    act_ids = [p.activity_id for p in participants]
    
    # Return all activities user joined
    if not act_ids:
        return []
    return db.query(Activity).filter(Activity.id.in_(act_ids)).order_by(Activity.start_time.desc()).all()

# --- ACTIVITY ENDPOINTS ---

@app.get("/api/activities", response_model=List[ActivityResponse])
def list_activities(db: Session = Depends(get_db)):
    # Order upcoming activities
    return db.query(Activity).order_by(Activity.start_time.asc()).all()

@app.post("/api/activities", response_model=ActivityResponse)
def create_activity(act_in: ActivityCreate, creator_id: int, db: Session = Depends(get_db)):
    creator = db.query(User).filter(User.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator user not found")
        
    activity = Activity(
        title=act_in.title,
        description=act_in.description,
        activity_type=act_in.activity_type,
        start_time=act_in.start_time,
        end_time=act_in.end_time or (act_in.start_time + timedelta(hours=1)),
        location=act_in.location,
        participant_limit=act_in.participant_limit,
        current_participants=1,  # Creator joins automatically
        created_by=creator_id
    )
    db.add(activity)
    db.flush()
    
    # Add creator as a participant
    participant = ActivityParticipant(activity_id=activity.id, user_id=creator_id)
    db.add(participant)
    db.commit()
    db.refresh(activity)
    
    return activity

@app.post("/api/activities/{activity_id}/join", response_model=JoinActivityResponse)
def join_activity(activity_id: int, req: JoinActivityRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
        
    # Check if already joined
    existing = db.query(ActivityParticipant).filter(
        ActivityParticipant.activity_id == activity_id,
        ActivityParticipant.user_id == req.user_id
    ).first()
    
    if existing:
        return JoinActivityResponse(
            success=False,
            message="You are already participating in this activity.",
            current_participants=activity.current_participants
        )
        
    # Check participant limit
    if activity.current_participants >= activity.participant_limit:
        return JoinActivityResponse(
            success=False,
            message="This activity is already full.",
            current_participants=activity.current_participants
        )
        
    # Add participant
    p = ActivityParticipant(activity_id=activity_id, user_id=req.user_id)
    db.add(p)
    
    # Increment current_participants
    activity.current_participants += 1
    db.commit()
    db.refresh(activity)
    
    return JoinActivityResponse(
        success=True,
        message="Successfully joined the activity!",
        current_participants=activity.current_participants
    )

# --- GYM CLASSES ENDPOINTS ---

@app.get("/api/gym-classes", response_model=List[GymClassResponse])
def list_gym_classes(db: Session = Depends(get_db)):
    return db.query(GymClass).filter(GymClass.active == True).all()

# --- SCENARIO 5: MISSING PLAYERS CANDIDATE SELECTOR ---

@app.get("/api/activities/{activity_id}/candidates")
def get_activity_candidates(activity_id: int, db: Session = Depends(get_db)):
    """
    Finds and recommends suitable candidates for an activity that needs players.
    Matches users based on:
    - Interests (interest match)
    - Past history (participated in this activity type before)
    - Excludes users already joined.
    """
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
        
    # Find users already participating
    existing_participant_ids = db.query(ActivityParticipant.user_id).filter(
        ActivityParticipant.activity_id == activity_id
    ).all()
    joined_ids = [p[0] for p in existing_participant_ids]
    
    all_users = db.query(User).all()
    candidates = []
    
    # Target criteria
    target_type = activity.activity_type.lower()
    
    for u in all_users:
        if u.id in joined_ids:
            continue
            
        score = 0.0
        reasons = []
        
        # 1. Interests Match
        user_interests = [i.strip().lower() for i in u.interests]
        if target_type in user_interests:
            score += 0.6
            reasons.append(f"Interested in {target_type}")
        elif "sports" in user_interests and target_type in ["football", "badminton", "running", "gym"]:
            score += 0.4
            reasons.append("Interested in sports")
            
        # 2. History Match
        # Find if user has participated in this activity type before
        p_records = db.query(ActivityParticipant).filter(ActivityParticipant.user_id == u.id).all()
        hist_ids = [p.activity_id for p in p_records]
        
        history_match_count = 0
        if hist_ids:
            history_match_count = db.query(Activity).filter(
                Activity.id.in_(hist_ids),
                Activity.activity_type == target_type
            ).count()
            
        if history_match_count > 0:
            score += 0.4
            reasons.append(f"Participated in {target_type} {history_match_count} times before")
            
        # 3. Add to candidate list if they match any criteria
        if score > 0:
            # Calculate organizational closeness to host/creator
            creator = db.query(User).filter(User.id == activity.created_by).first()
            org_dist = organization_distance(u, creator) if creator else 0.0
            
            candidates.append({
                "id": u.id,
                "domain": u.domain,
                "full_name": u.full_name,
                "title": u.title,
                "department": u.department,
                "squad": u.squad,
                "org_closeness": org_dist,
                "reasons": reasons,
                "fit_score": round(score + 0.1 * org_dist, 2)
            })
            
    # Sort candidates by fit score descending
    candidates.sort(key=lambda x: x["fit_score"], reverse=True)
    return candidates
