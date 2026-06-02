from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from models import SessionLocal, Transaction, Category, User
from routers.auth import get_current_user

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
    summary_data = db.query(
        Category.name, 
        func.sum(Transaction.amount).label("total_spent")
    ).join(
        Transaction, Category.id == Transaction.category_id
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "Expense" 
    ).group_by(Category.name).all()

    result = []
    for row in summary_data:
        result.append({
            "category_name": row.name,
            "total_spent": row.total_spent
        })
    
    return result

@router.get("/rolling-average")
def get_rolling_average(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user) 
):
    today = datetime.utcnow().date()
    ninety_days_ago = today - timedelta(days=90)
    
    total_spent = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "Expense",
        Transaction.transaction_date >= ninety_days_ago
    ).scalar() 
    
    if total_spent is None:
        total_spent = 0.0
        
    monthly_average = total_spent / 3
    
    return {
        "timeframe": "Last 90 Days",
        "total_spent_in_window": total_spent,
        "monthly_average": round(monthly_average, 2)
    }