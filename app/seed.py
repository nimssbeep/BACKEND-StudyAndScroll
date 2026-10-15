from sqlalchemy.orm import Session

def seed_initial_data(db: Session):
    """
    Production / User-Driven mode:
    No hardcoded mock users, peer accounts, or hardcoded profile pictures.
    Users register and upload their own content and profile pictures.
    """
    pass
