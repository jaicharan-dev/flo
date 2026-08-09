from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models import SessionLocal, User
from routers.auth import get_current_user
from services.analytics_service import AnalyticsService

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/summary")
def get_category_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_category_summary(db, current_user.id)

@router.get("/rolling-average")
def get_rolling_average(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user) 
):
    return AnalyticsService.get_rolling_average(db, current_user.id)