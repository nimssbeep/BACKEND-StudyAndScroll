import os
import re
import secrets
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import RegisterRequest, LoginRequest, PreferencesUpdateRequest, AuthResponse, UserResponse
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_csrf_token,
    get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB

def _set_auth_cookies(response: Response, access_token: str, csrf_token: str):
    response.set_cookie(
        key="skrulla_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True behind HTTPS in production
        max_age=86400,
    )
    response.set_cookie(
        key="skrulla_csrf_token",
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=False,
        max_age=86400,
    )

@router.post("/register", response_model=AuthResponse)
def register_user(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    base_handle = "@" + re.sub(r"[^a-z0-9]", "", payload.name.lower())[:16] + ".curious"
    handle = base_handle
    counter = 1
    while db.query(User).filter(User.handle == handle).first():
        handle = f"{base_handle}{counter}"
        counter += 1

    user = User(
        name=payload.name,
        handle=handle,
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        avatar_url="",  # User starts clean with dynamic initials or uploads their own
        onboarding_completed=False,
        streak_days=1,
        cards_learned_this_week=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token({"sub": str(user.id)})
    csrf_token = generate_csrf_token()
    _set_auth_cookies(response, access_token, csrf_token)

    return AuthResponse(access_token=access_token, csrf_token=csrf_token, user=user)

@router.post("/login", response_model=AuthResponse)
def login_user(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    access_token = create_access_token({"sub": str(user.id)})
    csrf_token = generate_csrf_token()
    _set_auth_cookies(response, access_token, csrf_token)

    return AuthResponse(access_token=access_token, csrf_token=csrf_token, user=user)

@router.post("/logout")
def logout_user(response: Response):
    response.delete_cookie("skrulla_access_token")
    response.delete_cookie("skrulla_csrf_token")
    return {"message": "Logged out safely."}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/preferences", response_model=UserResponse)
def update_preferences(
    payload: PreferencesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.skip:
        current_user.education_level = payload.education_level
        current_user.preferences = payload.preferences
    current_user.onboarding_completed = True
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allows user to upload their own custom profile picture."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file.")

    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format '{ext}'. Allowed: .jpg, .jpeg, .png, .webp, .gif",
        )

    # Read and enforce file size
    contents = await file.read()
    if len(contents) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=413, detail="Profile picture must be under 5 MB.")

    # Validate image magic bytes
    is_valid_image = (
        contents.startswith(b"\xff\xd8\xff")  # JPEG
        or contents.startswith(b"\x89PNG\r\n\x1a\n")  # PNG
        or contents.startswith(b"GIF87a") or contents.startswith(b"GIF89a")  # GIF
        or (contents.startswith(b"RIFF") and b"WEBP" in contents[:16])  # WEBP
    )
    if not is_valid_image:
        raise HTTPException(status_code=400, detail="File signature does not match a valid image.")

    # Remove previous avatar file if exists locally
    if current_user.avatar_url and current_user.avatar_url.startswith("/uploads/avatars/"):
        old_path = current_user.avatar_url.lstrip("/")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    # Save new avatar with unique filename
    os.makedirs("uploads/avatars", exist_ok=True)
    new_filename = f"user_{current_user.id}_{secrets.token_hex(6)}{ext}"
    dest_path = os.path.join("uploads", "avatars", new_filename)
    with open(dest_path, "wb") as f:
        f.write(contents)

    current_user.avatar_url = f"/uploads/avatars/{new_filename}"
    db.commit()
    db.refresh(current_user)
    return current_user

@router.delete("/avatar", response_model=UserResponse)
def remove_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Removes custom profile picture and resets to dynamic initials."""
    if current_user.avatar_url and current_user.avatar_url.startswith("/uploads/avatars/"):
        old_path = current_user.avatar_url.lstrip("/")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    current_user.avatar_url = ""
    db.commit()
    db.refresh(current_user)
    return current_user
