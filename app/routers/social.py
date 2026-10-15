from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Friendship, Story
from app.schemas import StoryCreateRequest, StoryResponse, FriendUserResponse
from app.security import get_current_user

router = APIRouter(prefix="/api/social", tags=["Friends & Stories"])

@router.get("/friends", response_model=List[FriendUserResponse])
def list_friends_and_suggestions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendships = db.query(Friendship).filter(
        ((Friendship.requester_id == current_user.id) | (Friendship.addressee_id == current_user.id))
        & (Friendship.status == "accepted")
    ).all()
    friend_ids = {
        f.addressee_id if f.requester_id == current_user.id else f.requester_id
        for f in friendships
    }

    users = db.query(User).filter(User.id != current_user.id).limit(20).all()
    return [
        FriendUserResponse(
            id=u.id,
            name=u.name,
            handle=u.handle,
            avatar_url=u.avatar_url,
            education_level=u.education_level,
            preferences=u.preferences or [],
            is_friend=u.id in friend_ids,
        )
        for u in users
    ]

@router.post("/friends/{target_user_id}/toggle")
def toggle_friend(
    target_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if target_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot add yourself.")

    existing = db.query(Friendship).filter(
        ((Friendship.requester_id == current_user.id) & (Friendship.addressee_id == target_user_id))
        | ((Friendship.requester_id == target_user_id) & (Friendship.addressee_id == current_user.id))
    ).first()

    if existing:
        db.delete(existing)
        is_friend = False
    else:
        db.add(Friendship(requester_id=current_user.id, addressee_id=target_user_id, status="accepted"))
        is_friend = True
    db.commit()
    return {"is_friend": is_friend}

@router.get("/stories", response_model=List[StoryResponse])
def get_stories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stories = db.query(Story).order_by(Story.created_at.desc()).limit(15).all()
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
                )
            )
    return result

@router.post("/stories", response_model=StoryResponse)
def create_story(
    payload: StoryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    story = Story(
        user_id=current_user.id,
        tag=payload.tag,
        title=payload.title,
        subject=payload.subject,
        bg_gradient=payload.bg_gradient,
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
    )
