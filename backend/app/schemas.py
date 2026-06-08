from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    domain: str
    full_name: str
    title: str
    company: str
    org_group: str
    department: str
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

class ActivityResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    activity_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location: str
    participant_limit: int
    current_participants: int
    created_by: int
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
