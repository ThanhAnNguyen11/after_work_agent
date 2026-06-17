import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.app.models import PendingExtraction

EXTRACTION_TTL_HOURS = 24


def load_pending(user_id: int, db: Session):
    """Load PendingExtraction for user_id, or return None if none exists."""
    row = db.query(PendingExtraction).filter(
        PendingExtraction.user_id == user_id
    ).first()

    if row is None:
        return None

    if row.updated_at and (datetime.utcnow() - row.updated_at) > timedelta(hours=EXTRACTION_TTL_HOURS):
        clear_pending(user_id, db)
        return None

    return row


def save_pending(user_id: int, partial_data: dict, missing_fields: list, db: Session) -> None:
    row = db.query(PendingExtraction).filter(
        PendingExtraction.user_id == user_id
    ).first()

    if row is None:
        row = PendingExtraction(
            user_id=user_id,
            partial_data=json.dumps(partial_data),
            missing_fields=json.dumps(missing_fields),
        )
        db.add(row)
    else:
        row.partial_data = json.dumps(partial_data)
        row.missing_fields = json.dumps(missing_fields)
        row.updated_at = datetime.utcnow()

    db.commit()


def clear_pending(user_id: int, db: Session) -> None:
    db.query(PendingExtraction).filter(
        PendingExtraction.user_id == user_id
    ).delete()
    db.commit()


def get_partial_data(row) -> dict:
    try:
        return json.loads(row.partial_data) if row and row.partial_data else {}
    except Exception:
        return {}


def get_missing_fields(row) -> list:
    try:
        return json.loads(row.missing_fields) if row and row.missing_fields else []
    except Exception:
        return []
