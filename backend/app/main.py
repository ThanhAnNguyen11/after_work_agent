from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, date
from collections import Counter

from backend.app.database import get_db, init_db, seed_fixed_activities
from backend.app.models import User, Activity, FixedActivity, ActivityParticipant, Memory, RecommendationLog, UserExperience, UserBehavioralInterest, ParticipationJournal, Notification, RecommendationSession, PendingExtraction, FixedActivityParticipant
from backend.app.schemas import (
    UserCreate, UserResponse, ActivityCreate, ActivityResponse,
    FixedActivityResponse, MemoryResponse, ChatRequest, ChatResponse,
    JoinActivityRequest, JoinActivityResponse,
    RecommendationLogCreate, RecommendationLogResponse, RecommendationStatusUpdate,
    UserExperienceCreate, UserExperienceResponse,
    JournalOption, JournalPendingResponse, JournalResolveRequest, NotificationResponse,
    UserLoginRequest, UserLoginResponse, UserOnboardRequest,
    ConversationStarterResponse, RecommendationItem, BrowseActivityItem
)
from backend.app.agents.graph import run_agent_flow
from backend.app.agents.llm import llm_client
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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _current_week_start() -> "date":
    from datetime import date, timedelta
    today = date.today()
    return today - timedelta(days=today.weekday())  # Monday of current week


def _apply_schema_migrations():
    """Idempotent column migrations — run at startup after create_all."""
    from sqlalchemy import text as sa_text
    from backend.app.database import engine
    with engine.connect() as conn:
        is_pg = engine.dialect.name == "postgresql"
        migrations = [
            # pending_activity_json added 2026-06-14
            "ALTER TABLE recommendation_sessions ADD COLUMN IF NOT EXISTS pending_activity_json TEXT;"
            if is_pg else
            "ALTER TABLE recommendation_sessions ADD COLUMN pending_activity_json TEXT;",
            # fixed_activity_participants table (created via create_all, but ensure it exists)
            # create_all handles this; entry here is a no-op guard
        ]
        for sql in migrations:
            try:
                conn.execute(sa_text(sql))
                conn.commit()
            except Exception:
                conn.rollback()  # column already exists — safe to ignore


@app.on_event("startup")
def on_startup():
    init_db()
    _apply_schema_migrations()

@app.get("/health")
def health():
    return {"status": "ok"}

# --- CHAT / AGENT ENDPOINT ---

@app.post("/api/chat", response_model=ChatResponse)
def chat_with_agent(req: ChatRequest, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    try:
        response_text, activity_created, activity_type = run_agent_flow(
            user_id=req.user_id,
            message=req.message,
            conversation_history=req.conversation_history,
        )
        return ChatResponse(response=response_text, activity_created=activity_created, activity_type=activity_type)
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

def _enrich_activity(activity: Activity, db: Session) -> ActivityResponse:
    creator = db.query(User).filter(User.id == activity.created_by).first()
    data = ActivityResponse.model_validate(activity)
    data.host_name = creator.full_name if creator else None
    return data

@app.get("/api/activities", response_model=List[ActivityResponse])
def list_activities(db: Session = Depends(get_db)):
    activities = db.query(Activity).order_by(Activity.start_time.asc()).all()
    return [_enrich_activity(a, db) for a in activities]

@app.get("/api/activities/browse", response_model=List[BrowseActivityItem])
def browse_activities(user_id: int, db: Session = Depends(get_db)):
    joined_activity_ids = {
        p.activity_id for p in db.query(ActivityParticipant).filter(ActivityParticipant.user_id == user_id).all()
    }
    joined_gym_ids = {
        e.gym_class_id for e in db.query(UserExperience).filter(
            UserExperience.user_id == user_id,
            UserExperience.gym_class_id.isnot(None)
        ).all()
    }

    items: List[BrowseActivityItem] = []

    _WEEKDAYS_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    _DAY_ABBR = {"Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu", "Friday": "Fri", "Saturday": "Sat", "Sunday": "Sun"}

    def _fmt_weekday(weekday_str: str) -> str:
        days = [d.strip() for d in weekday_str.split(",")]
        if set(days) >= set(_WEEKDAYS_FULL):
            return "Weekdays"
        return ", ".join(_DAY_ABBR.get(d, d) for d in days)

    _WD_MAP = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}

    def _next_occurrence_ts(weekday_str: str, time_str: str) -> int:
        """Return Unix timestamp of the nearest upcoming occurrence of this recurring class."""
        try:
            h, m = map(int, time_str.split(":"))
            days = [_WD_MAP[d.strip()] for d in weekday_str.split(",") if d.strip() in _WD_MAP]
            today_wd = _now.weekday()
            best = None
            for wd in days:
                delta = (wd - today_wd) % 7
                candidate = _now.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=delta)
                if candidate <= _now:
                    candidate += timedelta(days=7)
                if best is None or candidate < best:
                    best = candidate
            return int(best.timestamp()) if best else 0
        except Exception:
            return 0

    # Platform fixed activities (always on_campus)
    for gc in db.query(FixedActivity).filter(FixedActivity.active == True).order_by(FixedActivity.weekday, FixedActivity.start_time).all():
        _day_label = _fmt_weekday(gc.weekday)
        _time_label = gc.start_time + (f"–{gc.end_time}" if gc.end_time else "")
        _is_free = gc.class_name.lower() in {"gym", "swimming", "running"}
        items.append(BrowseActivityItem(
            id=gc.id,
            source="platform",
            location_type="on_campus",
            title=gc.class_name,
            activity_type=gc.class_name.lower().split()[0],
            start_time=f"{_day_label} · {_time_label}",
            location=gc.location,
            spots_left=max(0, gc.capacity - 0),
            is_joined=gc.id in joined_gym_ids,
            host_name=gc.instructor,
            created_by=None,
            is_free_facility=_is_free,
            sort_ts=_next_occurrence_ts(gc.weekday, gc.start_time),
        ))

    # User-created activities — only upcoming or ongoing (15-min grace period after end)
    _now = get_current_time()
    _grace = _now - timedelta(minutes=15)
    _all_acts = (
        db.query(Activity)
        .filter(Activity.status == "active", Activity.start_time >= _grace)
        .order_by(Activity.start_time.asc())
        .all()
    )
    _all_acts = [a for a in _all_acts if (a.end_time or a.start_time + timedelta(hours=1)) >= _grace]
    for act in _all_acts:
        creator = db.query(User).filter(User.id == act.created_by).first()
        try:
            start_str = act.start_time.strftime("%a, %b %d · %H:%M")
        except Exception:
            start_str = str(act.start_time)
        try:
            end_str = act.end_time.strftime("%H:%M") if act.end_time else None
        except Exception:
            end_str = None
        items.append(BrowseActivityItem(
            id=act.id,
            source="user_created",
            location_type=act.location_type or "off_campus",
            title=act.title,
            activity_type=act.activity_type,
            start_time=start_str,
            end_time=end_str,
            location=act.location,
            spots_left=max(0, act.participant_limit - act.current_participants),
            is_joined=act.id in joined_activity_ids,
            host_name=creator.full_name if creator else None,
            created_by=act.created_by,
            difficulty=act.difficulty,
            sort_ts=int(act.start_time.timestamp()),
        ))

    return items

_SPORT_TYPES = {"gym", "yoga", "zumba", "boxing", "swimming", "football",
                "pickleball", "badminton", "running", "taekwondo"}
_ENT_TYPES   = {"board games", "movies", "dining", "esports", "coffee chat",
                "karaoke", "picnics", "concerts"}
_LEARN_TYPES = {"ai", "product", "english", "book club", "knowledge-sharing"}

def _generate_activity_description(activity: Activity, db: Session) -> str:
    system = (
        "You are a concise copywriter for a corporate after-work activity platform. "
        "Generate exactly one engaging sentence (max 15 words) describing the activity. "
        "Be specific to the activity type and title. No quotes or trailing punctuation."
    )
    prompt = f'Activity title: "{activity.title}"\nActivity type: {activity.activity_type}\n\nOne-sentence description:'
    try:
        generated = llm_client.run_agent(system, prompt).strip().strip('"').strip("'").rstrip(".")
        activity.description = generated
        db.add(activity)
        db.commit()
        return generated
    except Exception:
        return f"{activity.activity_type.replace('_', ' ').title()} — join the fun after work"


def _score_activity_for_user(activity: Activity, user: User, db: Session) -> RecommendationItem:
    user_interests = {i.strip().lower() for i in user.interests}
    act_type = activity.activity_type.lower()

    participant_ids = {p.user_id for p in activity.participants}
    is_joined = user.id in participant_ids
    spots_left = max(0, activity.participant_limit - activity.current_participants)

    score = 0

    # Interest match (0-50 pts)
    if act_type in user_interests:
        score += 50
    elif act_type in _SPORT_TYPES and user_interests & _SPORT_TYPES:
        score += 30
    elif act_type in _ENT_TYPES and user_interests & _ENT_TYPES:
        score += 30
    elif act_type in _LEARN_TYPES and user_interests & _LEARN_TYPES:
        score += 30

    # Participant interest overlap (0-30 pts)
    other_ids = participant_ids - {user.id}
    shared_interests: list[str] = []
    if other_ids:
        others = db.query(User).filter(User.id.in_(other_ids)).all()
        for p in others:
            common = user_interests & {i.strip().lower() for i in p.interests}
            shared_interests.extend(common)
    score += min(30, len(shared_interests) * 10)

    # Spots-available bonus (0-10 pts)
    score += 10 if spots_left > 3 else (5 if spots_left > 0 else 0)

    # Use activity description as the card insight; generate via LLM if missing
    if activity.description:
        ai_insight = activity.description
    else:
        ai_insight = _generate_activity_description(activity, db)

    return RecommendationItem(
        activity=_enrich_activity(activity, db),
        match_score=min(100, score),
        ai_insight=ai_insight,
        spots_left=spots_left,
        is_joined=is_joined,
    )


@app.get("/api/users/{user_id}/recommendations", response_model=List[RecommendationItem])
def get_recommendations(user_id: int, limit: int = 10, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _now = get_current_time()
    _grace = _now - timedelta(minutes=15)
    activities = (
        db.query(Activity)
        .filter(Activity.status == "active", Activity.start_time >= _grace)
        .order_by(Activity.start_time.asc())
        .all()
    )
    activities = [a for a in activities if (a.end_time or a.start_time + timedelta(hours=1)) >= _grace]

    results = [_score_activity_for_user(a, user, db) for a in activities]
    results = [r for r in results if not r.is_joined]
    results.sort(key=lambda x: x.match_score, reverse=True)
    return results[:limit]


@app.post("/api/activities", response_model=ActivityResponse)
def create_activity(act_in: ActivityCreate, creator_id: int, db: Session = Depends(get_db)):
    creator = db.query(User).filter(User.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator user not found")
        
    guidelines = act_in.guidelines or None
        
    activity = Activity(
        title=act_in.title,
        description=act_in.description,
        activity_type=act_in.activity_type,
        source="user_created",
        location_type=act_in.location_type,
        difficulty=act_in.difficulty,
        start_time=act_in.start_time,
        end_time=act_in.end_time or (act_in.start_time + timedelta(hours=1)),
        location=act_in.location,
        participant_limit=act_in.participant_limit,
        current_participants=1,  # Creator joins automatically
        created_by=creator_id,
        guidelines=guidelines,
        status="active"
    )
    db.add(activity)
    db.flush()
    
    # Add creator as a participant
    participant = ActivityParticipant(activity_id=activity.id, user_id=creator_id)
    db.add(participant)
    db.commit()
    db.refresh(activity)

    return _enrich_activity(activity, db)

@app.delete("/api/activities/{activity_id}")
def delete_activity(activity_id: int, user_id: int, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    if activity.created_by != user_id:
        raise HTTPException(status_code=403, detail="Only the activity host can delete this activity")
    db.query(ActivityParticipant).filter(ActivityParticipant.activity_id == activity_id).delete()
    db.query(RecommendationLog).filter(RecommendationLog.activity_id == activity_id).delete()
    db.delete(activity)
    db.commit()
    return {"success": True, "message": "Activity deleted."}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.query(Notification).filter(Notification.user_id == user_id).delete()
    db.query(UserBehavioralInterest).filter(UserBehavioralInterest.user_id == user_id).delete()
    db.query(UserExperience).filter(UserExperience.user_id == user_id).delete()
    db.query(ParticipationJournal).filter(ParticipationJournal.user_id == user_id).delete()
    db.query(PendingExtraction).filter(PendingExtraction.user_id == user_id).delete()
    db.query(RecommendationLog).filter(RecommendationLog.user_id == user_id).delete()
    db.query(RecommendationSession).filter(RecommendationSession.user_id == user_id).delete()
    db.query(FixedActivityParticipant).filter(FixedActivityParticipant.user_id == user_id).delete()
    db.query(ActivityParticipant).filter(ActivityParticipant.user_id == user_id).delete()
    db.query(Memory).filter(Memory.user_id == user_id).delete()
    db.query(Activity).filter(Activity.created_by == user_id).delete()
    db.delete(user)
    db.commit()
    return {"success": True, "message": f"User {user_id} deleted."}

@app.post("/api/activities/{activity_id}/join", response_model=JoinActivityResponse)
def join_activity(activity_id: int, req: JoinActivityRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
        
    # Check if activity status is inactive
    if activity.status == "inactive":
        return JoinActivityResponse(
            success=False,
            message="This activity is inactive or already full.",
            current_participants=activity.current_participants
        )
        
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
    
    # Notify host that the user joined (if host is not the joining user)
    if activity.created_by != req.user_id:
        join_notif = Notification(
            user_id=activity.created_by,
            message=f"{user.full_name} joined your activity: '{activity.title}'."
        )
        db.add(join_notif)
        
    # Mark status as inactive if limit is reached, and notify host
    if activity.current_participants >= activity.participant_limit:
        activity.status = "inactive"
        full_notif = Notification(
            user_id=activity.created_by,
            message=f"Your activity '{activity.title}' is now full."
        )
        db.add(full_notif)
    
    # Update recommendation log status to joined if it exists
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    rec_log = db.query(RecommendationLog).filter(
        RecommendationLog.user_id == req.user_id,
        RecommendationLog.activity_id == activity_id,
        RecommendationLog.recommended_at >= today_start
    ).first()
    if rec_log:
        rec_log.status = "joined"

    db.commit()
    db.refresh(activity)

    # Reset recommendation attempt state so user starts fresh next session
    rec_session = db.query(RecommendationSession).filter(
        RecommendationSession.user_id == req.user_id
    ).first()
    if rec_session:
        from backend.app.session_utils import reset_session
        reset_session(rec_session, db)

    # Clear any in-flight activity creation flow
    from backend.app.extraction_utils import clear_pending
    clear_pending(req.user_id, db)

    return JoinActivityResponse(
        success=True,
        message="Successfully joined the activity!",
        current_participants=activity.current_participants
    )

# --- GYM CLASSES ENDPOINTS ---

@app.get("/api/gym-classes", response_model=List[FixedActivityResponse])
def list_gym_classes(db: Session = Depends(get_db)):
    return db.query(FixedActivity).filter(FixedActivity.active == True).all()


@app.post("/api/gym-classes/{gym_class_id}/join")
def join_gym_class(gym_class_id: int, req: JoinActivityRequest, db: Session = Depends(get_db)):
    """Join a scheduled gym class for the current week. Resets automatically each Monday."""
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    gc = db.query(FixedActivity).filter(FixedActivity.id == gym_class_id, FixedActivity.active == True).first()
    if not gc:
        raise HTTPException(status_code=404, detail="Class not found")

    week_start = _current_week_start()
    existing = db.query(FixedActivityParticipant).filter(
        FixedActivityParticipant.user_id == req.user_id,
        FixedActivityParticipant.gym_class_id == gym_class_id,
        FixedActivityParticipant.week_start == week_start,
    ).first()
    if existing:
        participants = db.query(FixedActivityParticipant).filter(
            FixedActivityParticipant.gym_class_id == gym_class_id,
            FixedActivityParticipant.week_start == week_start,
        ).count()
        return {"success": False, "message": "Already joined this week.", "participants": participants}

    record = FixedActivityParticipant(
        user_id=req.user_id, gym_class_id=gym_class_id, week_start=week_start
    )
    db.add(record)
    db.commit()
    participants = db.query(FixedActivityParticipant).filter(
        FixedActivityParticipant.gym_class_id == gym_class_id,
        FixedActivityParticipant.week_start == week_start,
    ).count()
    return {"success": True, "message": f"Joined {gc.class_name}!", "participants": participants}

@app.get("/api/users/{user_id}/recent-shown-activities", response_model=List[BrowseActivityItem])
def get_recent_shown_activities(user_id: int, db: Session = Depends(get_db)):
    """Returns the activities most recently surfaced to the user by the recommendation agent (today)."""
    from datetime import timedelta
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    logs = (
        db.query(RecommendationLog)
        .filter(
            RecommendationLog.user_id == user_id,
            RecommendationLog.recommended_at >= today_start,
        )
        .order_by(RecommendationLog.recommended_at.desc())
        .limit(20)
        .all()
    )
    # Only keep the most recent recommendation batch.
    # Activities from the same recommendation are committed in one transaction
    # so their timestamps are within milliseconds of each other.
    # A 10-second window reliably isolates the latest batch from earlier ones.
    if logs:
        batch_cutoff = logs[0].recommended_at - timedelta(seconds=10)
        logs = [l for l in logs if l.recommended_at >= batch_cutoff]

    joined_activity_ids = {
        p.activity_id for p in db.query(ActivityParticipant)
        .filter(ActivityParticipant.user_id == user_id).all()
    }

    items = []
    seen_ids: set = set()
    for log in logs:
        if log.activity_id and log.activity_id not in seen_ids:
            act = db.query(Activity).filter(Activity.id == log.activity_id).first()
            if act:
                seen_ids.add(log.activity_id)
                creator = db.query(User).filter(User.id == act.created_by).first()
                try:
                    _end = act.end_time or (act.start_time + timedelta(hours=1))
                    start_str = act.start_time.strftime("%a, %b %d · %H:%M") + "–" + _end.strftime("%H:%M")
                except Exception:
                    start_str = str(act.start_time)
                items.append(BrowseActivityItem(
                    id=act.id,
                    source="user_created",
                    location_type=act.location_type or "off_campus",
                    title=act.title,
                    activity_type=act.activity_type,
                    start_time=start_str,
                    location=act.location,
                    spots_left=max(0, act.participant_limit - act.current_participants),
                    is_joined=act.id in joined_activity_ids,
                    host_name=creator.full_name if creator else None,
                    created_by=act.created_by,
                ))
        elif log.gym_class_id and log.gym_class_id not in seen_ids:
            gc = db.query(FixedActivity).filter(FixedActivity.id == log.gym_class_id).first()
            if gc:
                seen_ids.add(log.gym_class_id)
                _gc_time = gc.start_time + (f"–{gc.end_time}" if gc.end_time else "")
                items.append(BrowseActivityItem(
                    id=gc.id,
                    source="platform",
                    location_type="on_campus",
                    title=gc.class_name,
                    activity_type=gc.class_name.lower().split()[0],
                    start_time=_gc_time,
                    location=gc.location,
                    spots_left=max(0, gc.capacity),
                    is_joined=False,
                    host_name=gc.instructor,
                    created_by=None,
                ))
    return items

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
        elif "sports" in user_interests and target_type in ["football", "badminton", "running", "gym", "swimming"]:
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

# --- RECOMMENDATION LOG ENDPOINTS ---

@app.post("/api/recommendations/log", response_model=RecommendationLogResponse)
def log_recommendation(log_in: RecommendationLogCreate, db: Session = Depends(get_db)):
    # Avoid duplicate logs for the same user and activity/gym_class recommended today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    existing = db.query(RecommendationLog).filter(
        RecommendationLog.user_id == log_in.user_id,
        RecommendationLog.activity_id == log_in.activity_id,
        RecommendationLog.gym_class_id == log_in.gym_class_id,
        RecommendationLog.recommended_at >= today_start
    ).first()
    
    if existing:
        return existing
        
    log = RecommendationLog(
        user_id=log_in.user_id,
        activity_id=log_in.activity_id,
        gym_class_id=log_in.gym_class_id,
        status="shown"
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

@app.put("/api/recommendations/log/{log_id}/status", response_model=RecommendationLogResponse)
def update_recommendation_status(log_id: int, status_up: RecommendationStatusUpdate, db: Session = Depends(get_db)):
    log = db.query(RecommendationLog).filter(RecommendationLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Recommendation log not found")
    log.status = status_up.status
    db.commit()
    db.refresh(log)
    return log

@app.put("/api/recommendations/log/user/{user_id}/status", response_model=List[RecommendationLogResponse])
def update_recommendation_status_by_user(
    user_id: int,
    status_up: RecommendationStatusUpdate,
    activity_id: Optional[int] = None,
    gym_class_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(RecommendationLog).filter(
        RecommendationLog.user_id == user_id
    )
    if activity_id is not None:
        query = query.filter(RecommendationLog.activity_id == activity_id)
    if gym_class_id is not None:
        query = query.filter(RecommendationLog.gym_class_id == gym_class_id)
    
    logs = query.all()
    for log in logs:
        log.status = status_up.status
    db.commit()
    for log in logs:
        db.refresh(log)
    return logs

# --- USER EXPERIENCE ENDPOINTS ---

@app.post("/api/users/{user_id}/experiences", response_model=UserExperienceResponse)
def create_user_experience(user_id: int, exp_in: UserExperienceCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    exp = UserExperience(
        user_id=user_id,
        activity_id=exp_in.activity_id,
        gym_class_id=exp_in.gym_class_id,
        energy_rating=exp_in.energy_rating,
        connections_made=exp_in.connections_made,
        notes=exp_in.notes
    )
    exp.communities_enjoyed = exp_in.communities_enjoyed
    db.add(exp)
    db.commit()
    db.refresh(exp)
    
    # Trigger status update for recommendation log to 'joined'
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    rec_log = db.query(RecommendationLog).filter(
        RecommendationLog.user_id == user_id,
        RecommendationLog.activity_id == exp_in.activity_id,
        RecommendationLog.gym_class_id == exp_in.gym_class_id,
        RecommendationLog.recommended_at >= today_start
    ).first()
    if rec_log:
        rec_log.status = "joined"
        db.commit()
        
    return exp

@app.get("/api/users/{user_id}/experiences", response_model=List[UserExperienceResponse])
def get_user_experiences(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    experiences = db.query(UserExperience).filter(UserExperience.user_id == user_id).all()
    return experiences

# --- DAILY JOURNAL / FEEDBACK ENDPOINTS ---

def get_current_time() -> datetime:
    return datetime.now()

def map_custom_activity_type(custom_name: str) -> str:
    lowered = custom_name.lower()
    if "foot" in lowered:
        return "football"
    if "gym" in lowered:
        return "gym"
    if "yoga" in lowered:
        return "yoga"
    if "zumba" in lowered:
        return "zumba"
    if "combat" in lowered:
        return "body combat"
    if "run" in lowered:
        return "running"
    if "swim" in lowered or "pool" in lowered:
        return "swimming"
    if "board" in lowered or "game" in lowered or "catan" in lowered or "avalon" in lowered:
        return "board games"
    if "ai" in lowered or "study" in lowered or "sharing" in lowered:
        return "ai"
    if "badminton" in lowered:
        return "badminton"
    if "coffee" in lowered:
        return "coffee"
    return "other"

@app.get("/api/users/{user_id}/journal/pending", response_model=JournalPendingResponse)
def get_pending_journal_prompt(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    now = get_current_time()
    # 21:00 <= now.hour <= 23: target is today
    # 00:00 <= now.hour < 16: target is yesterday
    # Otherwise: no prompt
    if now.hour >= 21:
        target_date = now.date()
        prompt_active = True
    elif now.hour < 16:
        target_date = (now - timedelta(days=1)).date()
        prompt_active = True
    else:
        prompt_active = False
        
    if not prompt_active:
        return JournalPendingResponse(prompt=False)
        
    # Check if journal record already exists
    existing_journal = db.query(ParticipationJournal).filter(
        ParticipationJournal.user_id == user_id,
        ParticipationJournal.journal_date == target_date
    ).first()
    
    if existing_journal:
        return JournalPendingResponse(prompt=False)
        
    # Check if user has an activity they participated in on target_date (between 00:00 and 23:59)
    start_of_day = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
    end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
    
    participated = db.query(ActivityParticipant).join(Activity).filter(
        ActivityParticipant.user_id == user_id,
        Activity.start_time >= start_of_day,
        Activity.start_time <= end_of_day
    ).first()
    
    if participated:
        # Participation is already known. Auto-resolve it so we don't ask again.
        new_journal = ParticipationJournal(
            user_id=user_id,
            journal_date=target_date,
            status="resolved_activity",
            activity_id=participated.activity_id
        )
        db.add(new_journal)
        db.commit()
        return JournalPendingResponse(prompt=False)
        
    # Gather evening options (start_time >= 17:00) on the target_date
    weekday_name = target_date.strftime("%A")
    
    gym_classes = db.query(FixedActivity).filter(
        FixedActivity.active == True,
        FixedActivity.weekday.like(f"%{weekday_name}%")
    ).all()
    
    evening_classes = [gc for gc in gym_classes if gc.start_time >= "17:00"]
    
    start_evening = datetime(target_date.year, target_date.month, target_date.day, 17, 0, 0)
    end_evening = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
    
    evening_activities = db.query(Activity).filter(
        Activity.start_time >= start_evening,
        Activity.start_time <= end_evening
    ).all()
    
    options = []
    for act in evening_activities:
        options.append(JournalOption(
            activity_id=act.id,
            title=act.title,
            activity_type=act.activity_type,
            location=act.location
        ))
        
    for gc in evening_classes:
        options.append(JournalOption(
            gym_class_id=gc.id,
            title=f"Gym Class: {gc.class_name}",
            activity_type="gym",
            location=gc.location
        ))
        
    return JournalPendingResponse(
        prompt=True,
        target_date=target_date,
        options=options
    )

@app.post("/api/users/{user_id}/journal/resolve")
def resolve_journal_prompt(
    user_id: int, 
    req: JournalResolveRequest, 
    journal_date: Optional[date] = None, 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Determine the target date from current time if not provided
    if not journal_date:
        now = get_current_time()
        if now.hour >= 21:
            journal_date = now.date()
        elif now.hour < 16:
            journal_date = (now - timedelta(days=1)).date()
        else:
            raise HTTPException(
                status_code=400, 
                detail="No active daily journal window at the current time and no journal_date was provided."
            )
            
    # Check if a journal entry already exists for this date
    existing_journal = db.query(ParticipationJournal).filter(
        ParticipationJournal.user_id == user_id,
        ParticipationJournal.journal_date == journal_date
    ).first()
    
    if existing_journal and existing_journal.status != "asked":
        return {"success": True, "message": "Already resolved for this date."}
    if existing_journal and existing_journal.status == "asked":
        db.delete(existing_journal)
        db.flush()
        
    # Handle the resolution
    resolved_activity_type = None
    
    new_journal = ParticipationJournal(
        user_id=user_id,
        journal_date=journal_date,
        status=req.status,
        activity_id=req.activity_id,
        gym_class_id=req.gym_class_id,
        custom_activity=req.custom_activity
    )
    
    if req.status == "resolved_activity":
        # Resolve activity type and register/confirm attendance
        if req.activity_id:
            act = db.query(Activity).filter(Activity.id == req.activity_id).first()
            if not act:
                raise HTTPException(status_code=404, detail="Selected activity not found")
            resolved_activity_type = act.activity_type.lower()
            
            # Confirm/add participant record
            existing_participant = db.query(ActivityParticipant).filter(
                ActivityParticipant.activity_id == req.activity_id,
                ActivityParticipant.user_id == user_id
            ).first()
            if not existing_participant:
                p = ActivityParticipant(
                    activity_id=req.activity_id,
                    user_id=user_id,
                    source="self_reported"
                )
                db.add(p)
                act.current_participants += 1
                
        elif req.gym_class_id:
            gc = db.query(FixedActivity).filter(FixedActivity.id == req.gym_class_id).first()
            if not gc:
                raise HTTPException(status_code=404, detail="Selected gym class not found")
            resolved_activity_type = "gym"
            
        elif req.custom_activity:
            resolved_activity_type = map_custom_activity_type(req.custom_activity)
            
    # Save the journal record
    db.add(new_journal)
    
    # Update behavioral interest scores if an activity was resolved
    if resolved_activity_type:
        bi = db.query(UserBehavioralInterest).filter(
            UserBehavioralInterest.user_id == user_id,
            UserBehavioralInterest.activity_type == resolved_activity_type
        ).first()
        if not bi:
            bi = UserBehavioralInterest(
                user_id=user_id,
                activity_type=resolved_activity_type,
                score=0.0
            )
            db.add(bi)
            
        bi.score = min(1.0, bi.score + 0.3)
        bi.last_interacted = datetime.utcnow()
        
        # Decay other categories
        others = db.query(UserBehavioralInterest).filter(
            UserBehavioralInterest.user_id == user_id,
            UserBehavioralInterest.activity_type != resolved_activity_type
        ).all()
        for other_bi in others:
            other_bi.score = max(0.0, other_bi.score * 0.8)
            
    db.commit()
    return {"success": True, "message": "Journal response saved successfully."}

# --- HOST NOTIFICATION ENDPOINTS ---

@app.get("/api/users/{user_id}/notifications", response_model=List[NotificationResponse])
def list_user_notifications(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return db.query(Notification).filter(
        Notification.user_id == user_id
    ).order_by(Notification.created_at.desc()).all()

@app.put("/api/notifications/{notification_id}/read")
def mark_notification_as_read(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notification.read = True
    db.commit()
    return {"success": True, "message": "Notification marked as read."}

import secrets as _secrets

def _generate_token() -> str:
    return _secrets.token_urlsafe(32)

@app.post("/api/auth/register", response_model=UserLoginResponse)
def register_user(req: UserLoginRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.domain == req.domain).first()
    if existing:
        return UserLoginResponse(success=False, message="Domain already registered. Please log in instead.")
    token = _generate_token()
    new_user = User(
        domain=req.domain,
        password=req.password,
        is_onboarded=False,
        title="Employee",
        session_token=token,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserLoginResponse(
        success=True,
        message="Account created. Onboarding required.",
        user_id=new_user.id,
        is_onboarded=False,
        token=token,
    )

@app.post("/api/auth/login", response_model=UserLoginResponse)
def login_user(req: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.domain == req.domain).first()
    if not user:
        return UserLoginResponse(success=False, message="Domain not found. Please register first.")
    if user.password != req.password:
        return UserLoginResponse(success=False, message="Invalid password.")
    token = _generate_token()
    user.session_token = token
    db.commit()
    return UserLoginResponse(
        success=True,
        message="Login successful",
        user_id=user.id,
        is_onboarded=user.is_onboarded,
        token=token,
    )

@app.get("/api/auth/me", response_model=UserLoginResponse)
def get_me(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.session_token == token).first()
    if not user:
        return UserLoginResponse(success=False, message="Invalid or expired session.")
    return UserLoginResponse(
        success=True,
        message="Session valid",
        user_id=user.id,
        is_onboarded=user.is_onboarded,
        token=token,
    )

@app.post("/api/auth/logout")
def logout_user(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.session_token == token).first()
    if user:
        user.session_token = None
        db.commit()
    return {"success": True, "message": "Logged out."}

@app.get("/api/users/{user_id}/conversation-starter", response_model=ConversationStarterResponse)
def get_conversation_starter(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = get_current_time()
    first_name = user.full_name.split()[-1]

    # Priority 0: brand-new user — no participation history at all
    total_participated = db.query(ActivityParticipant).filter(
        ActivityParticipant.user_id == user_id
    ).count()
    if total_participated == 0:
        interests = user.interests or []
        interest_line = ""
        if interests:
            interest_line = f"\n\nTôi thấy bạn quan tâm đến **{interests[0]}**{(' và **' + interests[1] + '**') if len(interests) > 1 else ''} — sẽ ưu tiên gợi ý những hoạt động đó cho bạn."
        message = (
            f"Chào {first_name}! Tôi là ALP — trợ lý after-work của bạn tại VNG Campus.\n\n"
            f"Tôi có thể giúp bạn:\n"
            f"• **Tìm hoạt động** phù hợp với tâm trạng và lịch của bạn\n"
            f"• **Xem lịch** yoga, gym, bơi lội, cầu lông và các lớp tại campus\n"
            f"• **Tạo hoạt động** riêng và rủ đồng nghiệp cùng tham gia"
            f"{interest_line}\n\n"
            f"Thử hỏi tôi: \"Tối nay có gì không?\" hoặc \"Muốn gì đó nhẹ nhàng sau giờ làm\" là được rồi."
        )
        return ConversationStarterResponse(type="new_user_welcome", message=message)

    # Priority 1: unresolved participation exists
    if now.hour >= 21:
        target_date = now.date()
        prompt_active = True
    elif now.hour < 16:
        target_date = (now - timedelta(days=1)).date()
        prompt_active = True
    else:
        prompt_active = False

    if prompt_active:
        existing_journal = db.query(ParticipationJournal).filter(
            ParticipationJournal.user_id == user_id,
            ParticipationJournal.journal_date == target_date
        ).first()

        if not existing_journal:
            start_of_day = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
            end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
            participated = db.query(ActivityParticipant).join(Activity).filter(
                ActivityParticipant.user_id == user_id,
                Activity.start_time >= start_of_day,
                Activity.start_time <= end_of_day
            ).first()

            if not participated:
                # Mark as asked so this question doesn't repeat on the next app open.
                # The journal resolve endpoint will overwrite this when the user answers.
                db.add(ParticipationJournal(
                    user_id=user_id,
                    journal_date=target_date,
                    status="asked"
                ))
                db.commit()
                return ConversationStarterResponse(
                    type="participation_followup",
                    message="What did you do yesterday evening?"
                )

    # Priority 2: contextual welcome (LLM-generated)
    hour = now.hour
    interests = user.interests or []

    if hour < 12:
        time_context = "morning, before work starts"
    elif hour < 17:
        time_context = "afternoon, approaching the end of the work day"
    else:
        time_context = "evening, after work hours"

    system_prompt = """You are After Work Agent, a friendly workplace activity assistant.
Write ONE short, natural opening sentence to greet the employee and invite them to explore after-work activities.
Do not list activities. Do not use bullet points. Max 20 words. Be warm and specific to their interests if available."""

    user_prompt = f"""Employee name: {user.full_name.split()[-1]}
Time of day: {time_context}
Declared interests: {', '.join(interests) if interests else 'none yet'}"""

    try:
        message = llm_client.run_agent(system_prompt, user_prompt).strip()
        if not message:
            raise ValueError("empty response")
    except Exception:
        # Fallback to simple template if LLM is unavailable
        action_hint = "Planning something after work today?" if hour < 17 else "Looking for something to do tonight?"
        interest_hint = f" You're into {interests[0]} — want me to check what's on?" if interests else " Want me to show you what activities are available?"
        message = f"{action_hint}{interest_hint}"

    return ConversationStarterResponse(type="welcome", message=message)


@app.post("/api/dev/reset")
def dev_reset(db: Session = Depends(get_db)):
    """Wipes all user data for testing. Fixed activities are preserved."""
    db.query(Notification).delete()
    db.query(ParticipationJournal).delete()
    db.query(UserBehavioralInterest).delete()
    db.query(UserExperience).delete()
    db.query(RecommendationLog).delete()
    db.query(RecommendationSession).delete()
    db.query(PendingExtraction).delete()
    db.query(ActivityParticipant).delete()
    db.query(Memory).delete()
    db.query(Activity).delete()
    db.query(User).delete()
    db.commit()
    return {"success": True, "message": "All user data cleared."}

@app.post("/api/dev/seed-fixed-activities")
def dev_seed_fixed_activities(db: Session = Depends(get_db)):
    """Replaces all fixed activities with the authoritative dataset from database.py."""
    count = seed_fixed_activities(db)
    return {"success": True, "inserted": count}

@app.post("/api/users/{user_id}/onboard", response_model=UserResponse)
def onboard_user(user_id: int, req: UserOnboardRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.full_name = req.full_name
    user.company = req.company
    user.org_group = req.org_group
    user.department = req.department
    user.squad = req.squad
    user.interests = req.interests
    user.is_onboarded = True
    
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        domain=user.domain,
        full_name=user.full_name,
        title=user.title or "Employee",
        company=user.company,
        org_group=user.org_group,
        department=user.department,
        squad=user.squad,
        interests=user.interests,
        created_at=user.created_at
    )
