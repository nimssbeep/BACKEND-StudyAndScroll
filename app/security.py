import re
import secrets
import bleach
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request, UploadFile
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

ALLOWED_MIME_TYPES = {"text/plain", "text/markdown", "application/pdf"}
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}

def sanitize_text(value: Optional[str], max_len: int = 2000) -> str:
    """Strips all HTML/XSS tags, null bytes, and control characters."""
    if not value:
        return ""
    cleaned = value.replace("\x00", "")
    # Strip all HTML tags completely
    cleaned = bleach.clean(cleaned, tags=[], attributes={}, strip=True)
    cleaned = re.sub(r"javascript\s*:", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()[:max_len]

def sanitize_filename(filename: str) -> str:
    """Prevents directory traversal and restricts filename characters."""
    name = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename.split("/")[-1].split("\\")[-1])
    return f"{secrets.token_hex(6)}_{name[:100]}"

async def validate_and_read_upload(file: UploadFile) -> bytes:
    """Enforces file extension, MIME type, magic bytes, and strict MB size limit."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed: .pdf, .txt, .md",
        )
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid MIME type '{file.content_type}'. Only educational PDF, TXT, or MD files are allowed.",
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    chunks = bytearray()
    while True:
        chunk = await file.read(65536)
        if not chunk:
            break
        chunks.extend(chunk)
        if len(chunks) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
            )

    raw_bytes = bytes(chunks)
    if ext == ".pdf" and not raw_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="File signature does not match a valid PDF document.")
    return raw_bytes

import bcrypt

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)

def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    jwt_token = token or request.cookies.get("skrulla_access_token")
    if not jwt_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(jwt_token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
