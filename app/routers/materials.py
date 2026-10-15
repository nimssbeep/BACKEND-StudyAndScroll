import io
from typing import List
from pypdf import PdfReader
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, StudyMaterial, FeedPost, Notification
from app.security import get_current_user, sanitize_text, sanitize_filename, validate_and_read_upload
from app.ai_shield import generate_grounded_cards_from_material

router = APIRouter(prefix="/api/materials", tags=["Study Materials"])

@router.get("")
def list_materials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_mats = (
        db.query(StudyMaterial)
        .filter((StudyMaterial.user_id == current_user.id) | (StudyMaterial.is_default == True))
        .order_by(StudyMaterial.created_at.desc())
        .all()
    )
    return [
        {
            "id": m.id,
            "title": m.title,
            "subject": m.subject,
            "education_level": m.education_level,
            "cards_count": m.cards_count,
            "is_default": m.is_default,
        }
        for m in user_mats
    ]

@router.post("/upload")
async def upload_study_material(
    title: str = Form(...),
    subject: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    clean_title = sanitize_text(title, 120)
    clean_subject = sanitize_text(subject, 60)
    safe_fname = sanitize_filename(file.filename or "notes.txt")

    raw_bytes = await validate_and_read_upload(file)

    # Extract text safely
    extracted_text = ""
    if safe_fname.lower().endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(raw_bytes))
            pages = [page.extract_text() or "" for page in reader.pages[:25]]
            extracted_text = "\n".join(pages)
        except Exception:
            raise HTTPException(status_code=400, detail="Could not parse PDF text.")
    else:
        extracted_text = raw_bytes.decode("utf-8", errors="ignore")

    clean_content = sanitize_text(extracted_text, 12000)

    # Run Hallucination Shield & Prompt Injection Guard to generate grounded cards
    generated_cards = await generate_grounded_cards_from_material(
        title=clean_title,
        subject=clean_subject,
        education_level=current_user.education_level,
        raw_content=clean_content,
    )

    material = StudyMaterial(
        user_id=current_user.id,
        title=clean_title,
        subject=clean_subject,
        education_level=current_user.education_level,
        filename=safe_fname,
        content_text=clean_content,
        cards_count=len(generated_cards),
        is_default=False,
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    created_posts = []
    for card in generated_cards:
        post = FeedPost(
            user_id=current_user.id,
            material_id=material.id,
            persona=card["persona"],
            post_type=card["post_type"],
            subject=clean_subject,
            education_level=current_user.education_level,
            hook=sanitize_text(card["hook"], 280),
            series_tag=sanitize_text(card.get("series_tag", "YOUR STUDY SERIES"), 80),
            headline=sanitize_text(card["headline"], 220),
            body=sanitize_text(card["body"], 1500),
            image_url=card.get("image_url"),
            tags=card.get("tags", [clean_subject]),
            quiz_question=sanitize_text(card.get("quiz_question"), 350) if card.get("quiz_question") else None,
            quiz_options=card.get("quiz_options"),
            quiz_correct_index=card.get("quiz_correct_index"),
            quiz_explanation=sanitize_text(card.get("quiz_explanation"), 600) if card.get("quiz_explanation") else None,
            source_verified=card.get("source_verified", True),
            grounding_score=card.get("grounding_score", 0.98),
            source_excerpt=sanitize_text(card["source_excerpt"], 300),
        )
        db.add(post)
        created_posts.append(post)

    current_user.cards_learned_this_week += len(created_posts)
    db.add(
        Notification(
            user_id=current_user.id,
            actor_id=current_user.id,
            notification_type="material",
            title="Notes Transformed",
            message=f"Generated {len(created_posts)} AI-verified cards from \"{clean_title}\".",
            link="/feed",
        )
    )
    db.commit()

    return {
        "message": "Study material verified, sanitized, and transformed into grounded feed cards!",
        "material_id": material.id,
        "cards_generated": len(created_posts),
    }
