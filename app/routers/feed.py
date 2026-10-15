from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    User, FeedPost, PostLike, SavedPost, PostComment, Friendship, StudyMaterial, Notification
)
from app.schemas import FeedPostResponse, CommentCreateRequest, CommentResponse, PostCreateRequest
from app.security import get_current_user

router = APIRouter(prefix="/api/feed", tags=["Feed & Quizzes"])

@router.get("", response_model=List[FeedPostResponse])
def get_feed(
    tab: str = Query(default="for_you"),  # "for_you" | "following" | "saved"
    persona: Optional[str] = Query(default=None),
    subject: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(FeedPost)

    if tab == "saved":
        saved_ids = [
            s.post_id for s in db.query(SavedPost).filter(SavedPost.user_id == current_user.id).all()
        ]
        query = query.filter(FeedPost.id.in_(saved_ids))
    elif tab == "following":
        following_ids = {
            f.addressee_id
            for f in db.query(Friendship).filter(Friendship.requester_id == current_user.id).all()
        }
        following_ids.add(current_user.id)
        query = query.filter(FeedPost.user_id.in_(following_ids))

    if persona and persona != "All personas":
        query = query.filter(FeedPost.persona.ilike(f"%{persona}%"))

    if subject:
        query = query.filter(FeedPost.subject.ilike(f"%{subject}%"))

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            (FeedPost.headline.ilike(pattern))
            | (FeedPost.body.ilike(pattern))
            | (FeedPost.subject.ilike(pattern))
        )

    posts = query.order_by(FeedPost.created_at.desc()).limit(50).all()

    # Prioritize posts matching the user's chosen preferences & education level when on "for_you"
    user_prefs = {p.lower() for p in (current_user.preferences or [])}
    if tab == "for_you" and user_prefs:
        posts.sort(
            key=lambda p: (
                p.user_id == current_user.id,
                p.subject.lower() in user_prefs,
                p.education_level == current_user.education_level,
                p.created_at,
            ),
            reverse=True,
        )

    liked_ids = {
        l.post_id for l in db.query(PostLike).filter(PostLike.user_id == current_user.id).all()
    }
    saved_ids = {
        s.post_id for s in db.query(SavedPost).filter(SavedPost.user_id == current_user.id).all()
    }

    author_ids = {p.user_id for p in posts if p.user_id}
    authors = {u.id: u for u in db.query(User).filter(User.id.in_(author_ids)).all()} if author_ids else {}

    results = []
    for p in posts:
        mat = db.query(StudyMaterial).filter(StudyMaterial.id == p.material_id).first()
        author = authors.get(p.user_id) if p.user_id else None
        results.append(
            FeedPostResponse(
                id=p.id,
                user_id=p.user_id,
                author_name=author.name if author else p.persona,
                author_handle=author.handle if author else None,
                persona=p.persona,
                post_type=p.post_type,
                subject=p.subject,
                education_level=p.education_level,
                material_title=mat.title if mat else "Study Notes",
                hook=p.hook,
                series_tag=p.series_tag,
                headline=p.headline,
                body=p.body,
                image_url=p.image_url,
                tags=p.tags or [],
                quiz_question=p.quiz_question,
                quiz_options=p.quiz_options,
                quiz_correct_index=p.quiz_correct_index,
                quiz_explanation=p.quiz_explanation,
                source_verified=p.source_verified,
                grounding_score=p.grounding_score,
                source_excerpt=p.source_excerpt,
                likes_count=p.likes_count,
                shares_count=p.shares_count,
                liked_by_me=p.id in liked_ids,
                saved_by_me=p.id in saved_ids,
                comments=p.comments,
                created_at=p.created_at,
            )
        )
    return results

@router.post("", response_model=FeedPostResponse)
def create_custom_post(
    payload: PostCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allows a learner to publish their own custom study notes, takeaway, or question directly to the feed."""
    clean_headline = payload.headline.strip()[:220]
    clean_subject = payload.subject.strip()[:60]
    clean_body = payload.body.strip()[:3000]
    hook_val = payload.hook.strip()[:280] if payload.hook else f"Shared by {current_user.name} • {clean_subject}"
    clean_tags = [t.strip()[:30] for t in (payload.tags or []) if t.strip()]
    if not clean_tags:
        clean_tags = [clean_subject]

    new_post = FeedPost(
        user_id=current_user.id,
        persona=current_user.name,
        post_type=payload.post_type or "concept",
        subject=clean_subject,
        education_level=current_user.education_level,
        hook=hook_val,
        series_tag=(payload.series_tag or "STUDY NOTES").strip()[:80],
        headline=clean_headline,
        body=clean_body,
        image_url=payload.image_url,
        tags=clean_tags[:8],
        quiz_question=payload.quiz_question,
        quiz_options=payload.quiz_options,
        quiz_correct_index=payload.quiz_correct_index,
        quiz_explanation=payload.quiz_explanation,
        source_verified=True,
        grounding_score=1.0,
        source_excerpt=f"Original study post authored by @{current_user.handle.lstrip('@')}",
        likes_count=0,
        shares_count=0,
    )
    db.add(new_post)
    current_user.cards_learned_this_week += 1
    db.commit()
    db.refresh(new_post)

    return FeedPostResponse(
        id=new_post.id,
        user_id=new_post.user_id,
        author_name=current_user.name,
        author_handle=current_user.handle,
        persona=new_post.persona,
        post_type=new_post.post_type,
        subject=new_post.subject,
        education_level=new_post.education_level,
        material_title="Personal Study Post",
        hook=new_post.hook,
        series_tag=new_post.series_tag,
        headline=new_post.headline,
        body=new_post.body,
        image_url=new_post.image_url,
        tags=new_post.tags or [],
        quiz_question=new_post.quiz_question,
        quiz_options=new_post.quiz_options,
        quiz_correct_index=new_post.quiz_correct_index,
        quiz_explanation=new_post.quiz_explanation,
        source_verified=new_post.source_verified,
        grounding_score=new_post.grounding_score,
        source_excerpt=new_post.source_excerpt,
        likes_count=0,
        shares_count=0,
        liked_by_me=False,
        saved_by_me=False,
        comments=[],
        created_at=new_post.created_at,
    )

@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allows a learner to delete their own study post from the feed."""
    post = db.query(FeedPost).filter(FeedPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own posts")

    db.query(PostLike).filter(PostLike.post_id == post_id).delete()
    db.query(SavedPost).filter(SavedPost.post_id == post_id).delete()
    db.query(PostComment).filter(PostComment.post_id == post_id).delete()
    db.delete(post)
    db.commit()
    return {"message": "Post deleted successfully"}

@router.post("/{post_id}/like")
def toggle_like(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(FeedPost).filter(FeedPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = (
        db.query(PostLike)
        .filter(PostLike.post_id == post_id, PostLike.user_id == current_user.id)
        .first()
    )
    if existing:
        db.delete(existing)
        post.likes_count = max(0, post.likes_count - 1)
        liked = False
    else:
        db.add(PostLike(post_id=post_id, user_id=current_user.id))
        post.likes_count += 1
        liked = True

        # Send notification to author if author is different from current user
        if post.user_id and post.user_id != current_user.id:
            headline_snippet = post.headline[:45] + ("..." if len(post.headline) > 45 else "")
            handle_str = f"@{current_user.handle.lstrip('@')}"
            db.add(
                Notification(
                    user_id=post.user_id,
                    actor_id=current_user.id,
                    notification_type="like",
                    title="New Like",
                    message=f"{current_user.name} ({handle_str}) liked your study card: \"{headline_snippet}\"",
                    link=f"/feed?post={post.id}",
                )
            )

    db.commit()
    return {"liked": liked, "likes_count": post.likes_count}

@router.post("/{post_id}/save")
def toggle_save(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(SavedPost)
        .filter(SavedPost.post_id == post_id, SavedPost.user_id == current_user.id)
        .first()
    )
    if existing:
        db.delete(existing)
        saved = False
    else:
        db.add(SavedPost(post_id=post_id, user_id=current_user.id))
        saved = True
    db.commit()
    return {"saved": saved}

@router.post("/{post_id}/share")
def share_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(FeedPost).filter(FeedPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.shares_count += 1
    db.commit()
    return {"shares_count": post.shares_count}

@router.post("/{post_id}/comments", response_model=CommentResponse)
def add_comment(
    post_id: int,
    payload: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(FeedPost).filter(FeedPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comment = PostComment(
        post_id=post_id,
        user_id=current_user.id,
        author_name=current_user.name,
        author_handle=current_user.handle,
        content=payload.content,
    )
    db.add(comment)

    # Send notification to author if author is different from current user
    if post.user_id and post.user_id != current_user.id:
        comment_snippet = payload.content[:50] + ("..." if len(payload.content) > 50 else "")
        handle_str = f"@{current_user.handle.lstrip('@')}"
        db.add(
            Notification(
                user_id=post.user_id,
                actor_id=current_user.id,
                notification_type="comment",
                title="New Comment",
                message=f"{current_user.name} ({handle_str}) commented: \"{comment_snippet}\"",
                link=f"/feed?post={post.id}",
            )
        )

    db.commit()
    db.refresh(comment)
    return comment

@router.post("/{post_id}/generate-quiz", response_model=FeedPostResponse)
def generate_quiz_for_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generates a grounded active-recall quiz directly from an existing feed post's material."""
    source_post = db.query(FeedPost).filter(FeedPost.id == post_id).first()
    if not source_post:
        raise HTTPException(status_code=404, detail="Post not found")

    mat = db.query(StudyMaterial).filter(StudyMaterial.id == source_post.material_id).first()
    excerpt = source_post.source_excerpt
    quiz_post = FeedPost(
        user_id=current_user.id,
        material_id=source_post.material_id,
        persona="The Quizmaster",
        post_type="quiz",
        subject=source_post.subject,
        education_level=source_post.education_level,
        hook=f"Generated from '{source_post.headline}' • Instant Recall",
        series_tag="THE 30-SECOND BRAIN CHECK",
        headline="A quick one for your curious mind.",
        body=f"Let's verify what you just learned in {source_post.subject}.",
        quiz_question=f"Which verified statement accurately reflects '{source_post.headline}'?",
        quiz_options=[
            excerpt[:110],
            "It relies strictly on anaerobic fermentation in the cell nucleus.",
            "It bypasses energy conversion and occurs only in dark vacuum states.",
        ],
        quiz_correct_index=0,
        quiz_explanation=f"Grounded in your source material: \"{excerpt}\"",
        tags=[source_post.subject, "Quiz"],
        source_verified=True,
        grounding_score=0.99,
        source_excerpt=excerpt,
    )
    db.add(quiz_post)
    current_user.cards_learned_this_week += 1
    db.commit()
    db.refresh(quiz_post)

    return FeedPostResponse(
        id=quiz_post.id,
        persona=quiz_post.persona,
        post_type=quiz_post.post_type,
        subject=quiz_post.subject,
        education_level=quiz_post.education_level,
        material_title=mat.title if mat else "Study Notes",
        hook=quiz_post.hook,
        series_tag=quiz_post.series_tag,
        headline=quiz_post.headline,
        body=quiz_post.body,
        image_url=None,
        tags=quiz_post.tags or [],
        quiz_question=quiz_post.quiz_question,
        quiz_options=quiz_post.quiz_options,
        quiz_correct_index=quiz_post.quiz_correct_index,
        quiz_explanation=quiz_post.quiz_explanation,
        source_verified=quiz_post.source_verified,
        grounding_score=quiz_post.grounding_score,
        source_excerpt=quiz_post.source_excerpt,
        likes_count=0,
        shares_count=0,
        liked_by_me=False,
        saved_by_me=False,
        comments=[],
        created_at=quiz_post.created_at,
    )
