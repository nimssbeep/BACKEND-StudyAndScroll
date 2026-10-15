from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Skrulla API"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite:///./skrulla.db"
    JWT_SECRET_KEY: str = "super-secret-jwt-key-change-in-production-987654321"
    CSRF_SECRET_KEY: str = "super-secret-csrf-key-change-in-production-123456789"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    MAX_UPLOAD_SIZE_MB: int = 10
    GEMINI_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
