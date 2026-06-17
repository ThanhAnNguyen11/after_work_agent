import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.app.models import RecommendationSession

SESSION_TTL_HOURS = 24


def load_session(user_id: int, db: Session) -> RecommendationSession:
    """Load or create a RecommendationSession for user_id. Auto-resets if older than TTL."""
    session = db.query(RecommendationSession).filter(
        RecommendationSession.user_id == user_id
    ).first()

    if session is None:
        session = RecommendationSession(user_id=user_id, attempt_number=1)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    if session.updated_at and (datetime.utcnow() - session.updated_at) > timedelta(hours=SESSION_TTL_HOURS):
        reset_session(session, db)

    return session


def reset_session(session: RecommendationSession, db: Session) -> None:
    """Reset all attempt state back to Attempt 1 defaults."""
    session.attempt_number = 1
    session.attempt1_shown_ids = "[]"
    session.attempt2_filters = "{}"
    session.attempt2_substate = None
    session.wellbeing_group = None
    session.pending_activity_json = None
    session.updated_at = datetime.utcnow()
    db.commit()


def advance_attempt(session: RecommendationSession, db: Session) -> None:
    """Advance to the next attempt number (max 3)."""
    session.attempt_number = min(session.attempt_number + 1, 3)
    session.updated_at = datetime.utcnow()
    db.commit()


def save_attempt1_shown(session: RecommendationSession, ids: list, db: Session) -> None:
    session.attempt1_shown_ids = json.dumps(ids)
    session.updated_at = datetime.utcnow()
    db.commit()


def get_attempt1_shown_ids(session: RecommendationSession) -> list:
    try:
        return json.loads(session.attempt1_shown_ids) if session.attempt1_shown_ids else []
    except Exception:
        return []


def save_attempt2_filters(session: RecommendationSession, filters: dict, db: Session) -> None:
    session.attempt2_filters = json.dumps(filters)
    session.attempt2_substate = "filters_applied"
    session.updated_at = datetime.utcnow()
    db.commit()


def get_attempt2_filters(session: RecommendationSession) -> dict:
    try:
        return json.loads(session.attempt2_filters) if session.attempt2_filters else {}
    except Exception:
        return {}


def set_attempt2_awaiting(session: RecommendationSession, db: Session) -> None:
    session.attempt2_substate = "awaiting_answers"
    session.updated_at = datetime.utcnow()
    db.commit()


def save_wellbeing_group(session: RecommendationSession, group: str, db: Session) -> None:
    session.wellbeing_group = group
    session.updated_at = datetime.utcnow()
    db.commit()


def save_pending_activity(session: RecommendationSession, activity: dict, db: Session) -> None:
    """Save the top recommended activity so the next turn can reference it."""
    session.pending_activity_json = json.dumps(activity)
    session.updated_at = datetime.utcnow()
    db.commit()


def get_pending_activity(session: RecommendationSession) -> dict:
    try:
        raw = getattr(session, "pending_activity_json", None)
        return json.loads(raw) if raw else {}
    except Exception:
        return {}
