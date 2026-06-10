from datetime import datetime
import json
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Date, Float, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, default="abc", nullable=False)
    is_onboarded = Column(Boolean, default=True, nullable=False)
    full_name = Column(String, nullable=True)
    title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    org_group = Column(String, nullable=True)
    department = Column(String, nullable=True)
    squad = Column(String, nullable=True)
    interests_raw = Column("interests", Text, default="[]")  # Stored as JSON string
    session_token = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    created_activities = relationship("Activity", back_populates="creator")
    participants = relationship("ActivityParticipant", back_populates="user")
    memories = relationship("Memory", back_populates="user")

    @property
    def interests(self):
        try:
            return json.loads(self.interests_raw) if self.interests_raw else []
        except Exception:
            return []

    @interests.setter
    def interests(self, value):
        if isinstance(value, list):
            self.interests_raw = json.dumps(value)
        else:
            self.interests_raw = json.dumps([])

class FixedActivity(Base):
    __tablename__ = "fixed_activities"

    id = Column(Integer, primary_key=True, index=True)
    class_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    weekday = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=True)
    location = Column(String, nullable=False)
    capacity = Column(Integer, default=20)
    instructor = Column(String, nullable=True)
    guidelines = Column(Text, nullable=True)
    active = Column(Boolean, default=True)

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    activity_type = Column(String, nullable=False)  # e.g., "football", "board games"
    start_time = Column(DateTime, nullable=False)  # Actual date/time of execution
    end_time = Column(DateTime, nullable=True)  # Actual end date/time of execution
    location = Column(String, nullable=False)
    participant_limit = Column(Integer, default=10)
    current_participants = Column(Integer, default=1)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    source = Column(String, default="user_created")  # "user_created" | "fixed"
    guidelines = Column(Text, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    creator = relationship("User", back_populates="created_activities")
    participants = relationship("ActivityParticipant", back_populates="activity", cascade="all, delete-orphan")

class ActivityParticipant(Base):
    __tablename__ = "activity_participants"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String, default="join")  # "join" | "self_reported"

    # Relationships
    activity = relationship("Activity", back_populates="participants")
    user = relationship("User", back_populates="participants")

class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="memories")

class RecommendationLog(Base):
    __tablename__ = "recommendation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=True)
    gym_class_id = Column(Integer, ForeignKey("fixed_activities.id"), nullable=True)
    recommended_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="shown")  # 'shown', 'clicked', 'joined', 'dismissed'

    # Relationships
    user = relationship("User")
    activity = relationship("Activity")
    gym_class = relationship("FixedActivity")

class UserExperience(Base):
    __tablename__ = "user_experiences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=True)
    gym_class_id = Column(Integer, ForeignKey("fixed_activities.id"), nullable=True)
    experience_date = Column(DateTime, default=datetime.utcnow)
    energy_rating = Column(Integer, nullable=True)  # -2 to +2
    connections_made = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    communities_enjoyed_raw = Column("communities_enjoyed", Text, default="[]")  # stored as JSON string

    # Relationships
    user = relationship("User")
    activity = relationship("Activity")
    gym_class = relationship("FixedActivity")

    @property
    def communities_enjoyed(self):
        try:
            return json.loads(self.communities_enjoyed_raw) if self.communities_enjoyed_raw else []
        except Exception:
            return []

    @communities_enjoyed.setter
    def communities_enjoyed(self, value):
        if isinstance(value, list):
            self.communities_enjoyed_raw = json.dumps(value)
        else:
            self.communities_enjoyed_raw = json.dumps([])

class UserBehavioralInterest(Base):
    __tablename__ = "user_behavioral_interests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_type = Column(String, nullable=False)
    score = Column(Float, default=0.0)
    last_interacted = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")

class ParticipationJournal(Base):
    __tablename__ = "participation_journal"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    journal_date = Column(Date, nullable=False)
    status = Column(String, nullable=False)  # 'asked', 'skipped', 'resolved_no_activity', 'resolved_activity'
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=True)
    gym_class_id = Column(Integer, ForeignKey("fixed_activities.id"), nullable=True)
    custom_activity = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    activity = relationship("Activity")
    gym_class = relationship("FixedActivity")

    __table_args__ = (UniqueConstraint('user_id', 'journal_date', name='_user_journal_date_uc'),)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
