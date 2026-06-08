from datetime import datetime
import json
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    org_group = Column(String, nullable=False)
    department = Column(String, nullable=False)
    squad = Column(String, nullable=True)
    interests_raw = Column("interests", Text, default="[]")  # Stored as JSON string
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

class GymClass(Base):
    __tablename__ = "gym_classes"

    id = Column(Integer, primary_key=True, index=True)
    class_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    weekday = Column(String, nullable=False)  # e.g., "Monday, Wednesday, Friday" or "Monday"
    start_time = Column(String, nullable=False)  # e.g., "18:00"
    end_time = Column(String, nullable=True)  # e.g., "19:00"
    location = Column(String, nullable=False)
    capacity = Column(Integer, default=20)
    instructor = Column(String, nullable=True)
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
