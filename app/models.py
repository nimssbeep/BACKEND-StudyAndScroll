from datetime import datetime, timedelta, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, ForeignKey, DateTime, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    handle = Column(String(60), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    avatar_url = Column(String(500), default="")
    bio = Column(String(300), default="")
    birthday = Column(String(50), default="")
    school = Column(String(160), default="")
    education_level = Column(String(50), default="University")  # "High School" | "University"
    preferences = Column(JSON, default=list)  # e.g., ["Mathematics", "Biology", "Computer Science"]
    certifications = Column(JSON, default=list)  # e.g., ["AWS Cloud Practitioner", "CompTIA Security+"]
    social_links = Column(JSON, default=dict)  # e.g., {"github": "...", "linkedin": "...", "twitter": "..."}
    onboarding_completed = Column(Boolean, default=False)
    streak_days = Column(Integer, default=1)
    cards_learned_this_week = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    materials = relationship("StudyMaterial", back_populates="owner", cascade="all, delete-orphan")
    posts = relationship("FeedPost", back_populates="author", cascade="all, delete-orphan")
    stories = relationship("Story", back_populates="author", cascade="all, delete-orphan")
    notifications = relationship(
        "Notification",
        foreign_keys="Notification.user_id",
        back_populates="recipient",
        cascade="all, delete-orphan",
    )


class StudyMaterial(Base):
    __tablename__ = "study_materials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # Nullable for default materials
    title = Column(String(200), nullable=False)
    subject = Column(String(80), nullable=False, index=True)
    education_level = Column(String(50), default="University")
    filename = Column(String(255), nullable=False)
    content_text = Column(Text, nullable=False)
    cards_count = Column(Integer, default=0)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    owner = relationship("User", back_populates="materials")
    posts = relationship("FeedPost", back_populates="material", cascade="all, delete-orphan")


class FeedPost(Base):
    __tablename__ = "feed_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(Integer, ForeignKey("study_materials.id", ondelete="CASCADE"), nullable=True)
    persona = Column(String(50), nullable=False)  # "Storyteller" | "Quizmaster" | "The Memer" | "Thread Architect"
    post_type = Column(String(30), default="concept")  # "concept" | "quiz"
    subject = Column(String(80), index=True, nullable=False)
    education_level = Column(String(50), default="University")
    hook = Column(String(300), nullable=False)
    series_tag = Column(String(100), default="THE EVERYDAY SCIENCE SERIES")
    headline = Column(String(250), nullable=False)
    body = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)
    tags = Column(JSON, default=list)

    # Quiz fields (if post_type == "quiz")
    quiz_question = Column(String(400), nullable=True)
    quiz_options = Column(JSON, nullable=True)  # List of strings
    quiz_correct_index = Column(Integer, nullable=True)
    quiz_explanation = Column(Text, nullable=True)

    # Hallucination Shield fields
    source_verified = Column(Boolean, default=True)
    grounding_score = Column(Float, default=0.98)
    source_excerpt = Column(Text, nullable=False)

    likes_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    author = relationship("User", back_populates="posts")
    material = relationship("StudyMaterial", back_populates="posts")
    comments = relationship("PostComment", back_populates="post", cascade="all, delete-orphan")


class PostLike(Base):
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("feed_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)


class SavedPost(Base):
    __tablename__ = "saved_posts"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("feed_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)


class PostComment(Base):
    __tablename__ = "post_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("feed_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    author_name = Column(String(100), nullable=False)
    author_handle = Column(String(60), nullable=False)
    content = Column(String(600), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    post = relationship("FeedPost", back_populates="comments")


class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    addressee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="accepted")  # "pending" | "accepted"
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String(80), default="IN MY STUDY ERA")
    title = Column(String(160), nullable=False)
    subject = Column(String(80), default="General")
    bg_gradient = Column(String(120), default="from-indigo-100 via-purple-100 to-pink-100")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    expires_at = Column(DateTime(timezone=True), default=lambda: utc_now() + timedelta(hours=24))
    is_archived = Column(Boolean, default=False, index=True)

    author = relationship("User", back_populates="stories")
 

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notification_type = Column(String(50), nullable=False)  # "like" | "comment" | "follow" | "quiz" | "material"
    title = Column(String(160), nullable=False)
    message = Column(String(400), nullable=False)
    link = Column(String(255), nullable=True)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    recipient = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    actor = relationship("User", foreign_keys=[actor_id])
