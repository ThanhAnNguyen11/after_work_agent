from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date

class UserBase(BaseModel):
    domain: str
    full_name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    org_group: Optional[str] = None
    department: Optional[str] = None
    squad: Optional[str] = None
    interests: List[str] = []

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class GymClassResponse(BaseModel):
    id: int
    class_name: str
    description: Optional[str] = None
    weekday: str
    start_time: str
    end_time: Optional[str] = None
    location: str
    capacity: int
    instructor: Optional[str] = None
    active: bool

    class Config:
        from_attributes = True

class ActivityCreate(BaseModel):
    title: str
    description: Optional[str] = None
    activity_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location: str
    participant_limit: int = 10
    guidelines: Optional[str] = None

class ActivityResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    activity_type: str
    source: str = "user_created"
    start_time: datetime
    end_time: Optional[datetime] = None
    location: str
    participant_limit: int
    current_participants: int
    created_by: int
    host_name: Optional[str] = None
    guidelines: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class MemoryResponse(BaseModel):
    id: int
    user_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    user_id: int
    message: str

class ChatResponse(BaseModel):
    response: str

class JoinActivityRequest(BaseModel):
    user_id: int

class JoinActivityResponse(BaseModel):
    success: bool
    message: str
    current_participants: int

class RecommendationLogCreate(BaseModel):
    user_id: int
    activity_id: Optional[int] = None
    gym_class_id: Optional[int] = None

class RecommendationLogResponse(BaseModel):
    id: int
    user_id: int
    activity_id: Optional[int] = None
    gym_class_id: Optional[int] = None
    recommended_at: datetime
    status: str

    class Config:
        from_attributes = True

class RecommendationStatusUpdate(BaseModel):
    status: str  # 'shown', 'clicked', 'joined', 'dismissed'

class UserExperienceCreate(BaseModel):
    user_id: int
    activity_id: Optional[int] = None
    gym_class_id: Optional[int] = None
    energy_rating: Optional[int] = None  # -2 to +2
    connections_made: Optional[int] = 0
    notes: Optional[str] = None
    communities_enjoyed: Optional[List[str]] = []

class UserExperienceResponse(BaseModel):
    id: int
    user_id: int
    activity_id: Optional[int] = None
    gym_class_id: Optional[int] = None
    experience_date: datetime
    energy_rating: Optional[int] = None
    connections_made: int
    notes: Optional[str] = None
    communities_enjoyed: List[str]

    class Config:
        from_attributes = True

class UserBehavioralInterestResponse(BaseModel):
    id: int
    user_id: int
    activity_type: str
    score: float
    last_interacted: datetime

    class Config:
        from_attributes = True

class JournalOption(BaseModel):
    activity_id: Optional[int] = None
    gym_class_id: Optional[int] = None
    title: str
    activity_type: str
    location: str

class JournalPendingResponse(BaseModel):
    prompt: bool
    target_date: Optional[date] = None
    options: List[JournalOption] = []

class JournalResolveRequest(BaseModel):
    status: str  # 'skipped', 'resolved_no_activity', 'resolved_activity'
    activity_id: Optional[int] = None
    gym_class_id: Optional[int] = None
    custom_activity: Optional[str] = None

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    message: str
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserLoginRequest(BaseModel):
    domain: str
    password: str

class UserLoginResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[int] = None
    is_onboarded: Optional[bool] = None
    token: Optional[str] = None

class UserOnboardRequest(BaseModel):
    full_name: str
    company: str
    org_group: str
    department: str
    squad: Optional[str] = None
    interests: List[str] = []

class ConversationStarterResponse(BaseModel):
    type: str  # "participation_followup" | "welcome"
    message: str
