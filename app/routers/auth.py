import re
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Friendship
from app.schemas import RegisterRequest, LoginRequest, PreferencesUpdateRequest, AuthResponse, UserResponse
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_csrf_token,
    get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

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
        onboarding_completed=False,
        streak_days=1,
        cards_learned_this_week=4,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Auto-connect with Sophie Chen so the new user sees a friend story right away
    sophie = db.query(User).filter(User.handle == "@sophie.studies").first()
    if sophie:
        db.add(Friendship(requester_id=sophie.id, addressee_id=user.id, status="accepted"))
        db.commit()

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
