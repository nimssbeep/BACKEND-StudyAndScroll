from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Friendship, Story, Notification, utc_now
from app.schemas import (
    StoryCreateRequest, StoryResponse, FriendUserResponse, NotificationResponse
)
from app.security import get_current_user

router = APIRouter(prefix="/api/social", tags=["Friends & Stories"])

@router.get("/friends", response_model=List[FriendUserResponse])
def list_friends_and_suggestions(
    search: Optional[str] = Query(default=None),
    filter_type: Optional[str] = Query(default="all"),  # "all" | "following" | "followers"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    following_ids = {
        f.addressee_id
        for f in db.query(Friendship).filter(Friendship.requester_id == current_user.id).all()
    }
    follower_ids = {
        f.requester_id
        for f in db.query(Friendship).filter(Friendship.addressee_id == current_user.id).all()
    }

    query = db.query(User).filter(User.id != current_user.id)

    if filter_type == "following":
        query = query.filter(User.id.in_(following_ids))
    elif filter_type == "followers":
        query = query.filter(User.id.in_(follower_ids))

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter((User.name.ilike(term)) | (User.handle.ilike(term)))

    users = query.order_by(User.name.asc()).limit(50).all()

    result = []
    for u in users:
        fol_cnt = db.query(Friendship).filter(Friendship.addressee_id == u.id).count()
        foll_cnt = db.query(Friendship).filter(Friendship.requester_id == u.id).count()
        result.append(
            FriendUserResponse(
                id=u.id,
                name=u.name,
                handle=u.handle,
                avatar_url=u.avatar_url,
                bio=u.bio or "",
                school=u.school or "",
                education_level=u.education_level,
                preferences=u.preferences or [],
                certifications=u.certifications or [],
                social_links=u.social_links or {},
                is_friend=(u.id in following_ids),
                followers_count=fol_cnt,
                following_count=foll_cnt,
            )
        )
    return result

@router.post("/friends/{target_user_id}/toggle")
def toggle_friend(
    target_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if target_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself.")

    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    existing = db.query(Friendship).filter(
        Friendship.requester_id == current_user.id,
        Friendship.addressee_id == target_user_id,
    ).first()

    if existing:
        db.delete(existing)
        is_friend = False
    else:
        db.add(Friendship(requester_id=current_user.id, addressee_id=target_user_id, status="accepted"))
        is_friend = True

        # Send follow notification to target user
        handle_str = f"@{current_user.handle.lstrip('@')}"
        notif = Notification(
            user_id=target_user_id,
            actor_id=current_user.id,
            notification_type="follow",
            title="New Follower",
            message=f"{current_user.name} ({handle_str}) started following your study journey!",
            link="/friends",
        )
        db.add(notif)

    db.commit()

    followers_count = db.query(Friendship).filter(Friendship.addressee_id == target_user_id).count()
    return {"is_friend": is_friend, "followers_count": followers_count}

@router.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    res = []
    for n in notifs:
        actor_name = None
        actor_handle = None
        actor_avatar = None
        if n.actor:
            actor_name = n.actor.name
            actor_handle = n.actor.handle
            actor_avatar = n.actor.avatar_url
        res.append(
            NotificationResponse(
                id=n.id,
                user_id=n.user_id,
                actor_id=n.actor_id,
                actor_name=actor_name,
                actor_handle=actor_handle,
                actor_avatar=actor_avatar,
                notification_type=n.notification_type,
                title=n.title,
                message=n.message,
                link=n.link,
                is_read=n.is_read,
                created_at=n.created_at,
            )
        )
    return res

@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"success": True}

@router.post("/notifications/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"success": True}

@router.get("/stories", response_model=List[StoryResponse])
def get_stories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = utc_now()
    # Auto-archive any stories that have passed their 24-hour window
    db.query(Story).filter(
        Story.is_archived == False,
        Story.expires_at <= now,
    ).update({"is_archived": True}, synchronize_session=False)
    db.commit()

    # Retrieve only active, non-archived stories
    stories = (
        db.query(Story)
        .filter(Story.is_archived == False, Story.expires_at > now)
        .order_by(Story.created_at.desc())
        .limit(25)
        .all()
    )
    result = []
    for s in stories:
        author = db.query(User).filter(User.id == s.user_id).first()
        if author:
            result.append(
                StoryResponse(
                    id=s.id,
                    user_id=author.id,
                    author_name=author.name,
                    author_handle=author.handle,
                    author_avatar=author.avatar_url,
                    tag=s.tag,
                    title=s.title,
                    subject=s.subject,
                    bg_gradient=s.bg_gradient,
                    created_at=s.created_at,
                    expires_at=s.expires_at,
                    is_archived=s.is_archived,
                )
            )
    return result

@router.get("/stories/archive", response_model=List[StoryResponse])
def get_story_archive(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = utc_now()
    # Ensure any expired stories are archived
    db.query(Story).filter(
        Story.is_archived == False,
        Story.expires_at <= now,
    ).update({"is_archived": True}, synchronize_session=False)
    db.commit()

    # Retrieve current user's archived stories
    archived = (
        db.query(Story)
        .filter(Story.user_id == current_user.id, Story.is_archived == True)
        .order_by(Story.created_at.desc())
        .all()
    )
    return [
        StoryResponse(
            id=s.id,
            user_id=current_user.id,
            author_name=current_user.name,
            author_handle=current_user.handle,
            author_avatar=current_user.avatar_url,
            tag=s.tag,
            title=s.title,
            subject=s.subject,
            bg_gradient=s.bg_gradient,
            created_at=s.created_at,
            expires_at=s.expires_at,
            is_archived=True,
        )
        for s in archived
    ]

@router.post("/stories", response_model=StoryResponse)
def create_story(
    payload: StoryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = utc_now()
    story = Story(
        user_id=current_user.id,
        tag=payload.tag,
        title=payload.title,
        subject=payload.subject,
        bg_gradient=payload.bg_gradient,
        created_at=now,
        expires_at=now + timedelta(hours=24),
        is_archived=False,
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return StoryResponse(
        id=story.id,
        user_id=current_user.id,
        author_name=current_user.name,
        author_handle=current_user.handle,
        author_avatar=current_user.avatar_url,
        tag=story.tag,
        title=story.title,
        subject=story.subject,
        bg_gradient=story.bg_gradient,
        created_at=story.created_at,
        expires_at=story.expires_at,
        is_archived=story.is_archived,
    )

@router.delete("/stories/{story_id}")
def delete_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")

    if story.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own stories.")

    db.delete(story)
    db.commit()
    return {"message": "Story deleted successfully", "id": story_id}

@router.post("/stories/{story_id}/archive")
def archive_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")

    if story.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only archive your own stories.")

    story.is_archived = True
    db.commit()
    return {"message": "Story moved to your archive", "id": story_id}
