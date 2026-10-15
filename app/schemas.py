from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.security import sanitize_text

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return sanitize_text(v, 80)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PreferencesUpdateRequest(BaseModel):
    education_level: str = Field(default="University")
    preferences: List[str] = Field(default_factory=list)
    skip: bool = False

    @field_validator("education_level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        clean = sanitize_text(v, 40)
        return clean if clean in {"High School", "University"} else "University"

    @field_validator("preferences")
    @classmethod
    def clean_prefs(cls, v: List[str]) -> List[str]:
        return [sanitize_text(item, 40) for item in v[:10] if item.strip()]

class UserResponse(BaseModel):
    id: int
    name: str
    handle: str
    email: EmailStr
    avatar_url: str
    education_level: str
    preferences: List[str]
    onboarding_completed: bool
    streak_days: int
    cards_learned_this_week: int

    class Config:
        from_attributes = True

class AuthResponse(BaseModel):
    access_token: str
    csrf_token: str
    user: UserResponse

class CommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)

    @field_validator("content")
    @classmethod
    def clean_content(cls, v: str) -> str:
        return sanitize_text(v, 500)

class CommentResponse(BaseModel):
    id: int
    author_name: str
    author_handle: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class FeedPostResponse(BaseModel):
    id: int
    persona: str
    post_type: str
    subject: str
    education_level: str
    material_title: str
    hook: str
    series_tag: str
    headline: str
    body: str
    image_url: Optional[str] = None
    tags: List[str]
    quiz_question: Optional[str] = None
    quiz_options: Optional[List[str]] = None
    quiz_correct_index: Optional[int] = None
    quiz_explanation: Optional[str] = None
    source_verified: bool
    grounding_score: float
    source_excerpt: str
    likes_count: int
    shares_count: int
    liked_by_me: bool = False
    saved_by_me: bool = False
    comments: List[CommentResponse] = []
    created_at: datetime

class StoryCreateRequest(BaseModel):
    tag: str = Field(default="IN MY STUDY ERA", max_length=60)
    title: str = Field(..., min_length=3, max_length=140)
    subject: str = Field(default="Biology", max_length=60)
    bg_gradient: str = Field(default="from-indigo-100 via-purple-100 to-pink-100", max_length=120)

    @field_validator("tag", "title", "subject")
    @classmethod
    def sanitize_fields(cls, v: str) -> str:
        return sanitize_text(v, 140)

class StoryResponse(BaseModel):
    id: int
    user_id: int
    author_name: str
    author_handle: str
    author_avatar: str
    tag: str
    title: str
    subject: str
    bg_gradient: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_archived: bool = False

class FriendUserResponse(BaseModel):
    id: int
    name: str
    handle: str
    avatar_url: str
    education_level: str
    preferences: List[str]
    is_friend: bool
    followers_count: int = 0
    following_count: int = 0

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    actor_handle: Optional[str] = None
    actor_avatar: Optional[str] = None
    notification_type: str
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
