from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from models import Transaction, Category


class AnalyticsService:
    @staticmethod
    def get_category_summary(db: Session, user_id: int) -> List[Dict[str, Any]]:
        summary_data = db.query(
            Category.name, 
            func.sum(Transaction.amount).label("total_spent")
        ).join(
            Transaction, Category.id == Transaction.category_id
        ).filter(
            Transaction.user_id == user_id,
            Transaction.type == "Expense" 
        ).group_by(Category.name).all()

        result = []
        for row in summary_data:
            result.append({
                "category_name": row.name,
                "total_spent": row.total_spent
            })
        
        return result

    @staticmethod
    def get_rolling_average(db: Session, user_id: int) -> Dict[str, Any]:
        today = datetime.utcnow().date()
        ninety_days_ago = today - timedelta(days=90)
        
        total_spent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
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
