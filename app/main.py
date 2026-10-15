import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import Base, engine, SessionLocal
from app.seed import seed_initial_data
from app.routers import auth, feed, materials, social

# Ensure uploads directory for user-uploaded avatars
os.makedirs("uploads/avatars", exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()
    yield

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# Allow all localhost / 127.0.0.1 / [::1] origins across any port for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://[::1]:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://[::1]:5173",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.middleware("http")
async def security_and_csrf_middleware(request: Request, call_next):
    # Pass through OPTIONS requests directly for CORS preflight
    if request.method == "OPTIONS":
        return await call_next(request)

    # Enforce CSRF validation on state-mutating requests when cookie auth is present
    if request.method in {"POST", "PUT", "DELETE", "PATCH"}:
        if (
            not request.url.path.startswith("/api/auth/login")
            and not request.url.path.startswith("/api/auth/register")
            and not request.url.path.startswith("/api/auth/avatar")
        ):
            csrf_cookie = request.cookies.get("skrulla_csrf_token")
            csrf_header = request.headers.get("X-CSRF-Token")
            if csrf_cookie and csrf_header and csrf_cookie != csrf_header:
                return JSONResponse(status_code=403, content={"detail": "CSRF token mismatch."})

    response = await call_next(request)
    # Hardened HTTP Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Mount user-uploaded files static directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(feed.router)
app.include_router(materials.router)
app.include_router(social.router)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Skrulla Backend API"}
