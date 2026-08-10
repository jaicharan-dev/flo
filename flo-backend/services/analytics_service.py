import math
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date

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
                "total_spent": float(row.total_spent or 0.0)
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
            "total_spent_in_window": float(total_spent),
            "monthly_average": round(float(monthly_average), 2)
        }

    @staticmethod
    def get_kpis(db: Session, user_id: int) -> Dict[str, Any]:
        income_sum = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == "Income"
        ).scalar() or 0.0

        expense_sum = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == "Expense"
        ).scalar() or 0.0

        total_tx = db.query(func.count(Transaction.id)).filter(
            Transaction.user_id == user_id
        ).scalar() or 0

        expense_tx_count = db.query(func.count(Transaction.id)).filter(
            Transaction.user_id == user_id,
            Transaction.type == "Expense"
        ).scalar() or 0

        avg_tx_val = round(expense_sum / expense_tx_count, 2) if expense_tx_count > 0 else 0.0

        today = datetime.utcnow().date()
        ninety_days_ago = today - timedelta(days=90)
        last_90_spent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == "Expense",
            Transaction.transaction_date >= ninety_days_ago
        ).scalar() or 0.0
        monthly_avg_spending = round(last_90_spent / 3, 2) if last_90_spent > 0 else round(expense_sum, 2)

        return {
            "total_income": round(float(income_sum), 2),
            "total_expense": round(float(expense_sum), 2),
            "net_balance": round(float(income_sum - expense_sum), 2),
            "total_transactions": total_tx,
            "expense_transactions_count": expense_tx_count,
            "avg_transaction_value": avg_tx_val,
            "monthly_avg_spending": monthly_avg_spending
        }

    @staticmethod
    def get_budget_vs_actual(db: Session, user_id: int) -> Dict[str, Any]:
        today = datetime.utcnow().date()
        first_day_of_month = date(today.year, today.month, 1)

        categories = db.query(Category).filter(Category.user_id == user_id).all()
        
        category_budgets = []
        tot_budget = 0.0
        tot_actual = 0.0

        for cat in categories:
            budget = float(cat.monthly_limit or 0.0)
            actual_spent = db.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == cat.id,
                Transaction.type == "Expense",
                Transaction.transaction_date >= first_day_of_month
            ).scalar() or 0.0

            actual_spent = float(actual_spent)
            remaining = round(budget - actual_spent, 2) if budget > 0 else 0.0
            utilization = round((actual_spent / budget) * 100, 1) if budget > 0 else 0.0
            is_over = actual_spent > budget if budget > 0 else False

            if budget > 0:
                tot_budget += budget
                tot_actual += actual_spent

            category_budgets.append({
                "category_id": cat.id,
                "category_name": cat.name,
                "budget": budget,
                "actual": round(actual_spent, 2),
                "remaining": remaining,
                "utilization_pct": utilization,
                "is_over_budget": is_over
            })

        tot_remaining = round(tot_budget - tot_actual, 2)
        overall_utilization = round((tot_actual / tot_budget) * 100, 1) if tot_budget > 0 else 0.0

        return {
            "categories": category_budgets,
            "totals": {
                "total_budget": round(tot_budget, 2),
                "total_actual": round(tot_actual, 2),
                "total_remaining": tot_remaining,
                "overall_utilization_pct": overall_utilization
            }
        }

    @staticmethod
    def get_trends(db: Session, user_id: int) -> Dict[str, Any]:
        today = datetime.utcnow().date()
        first_day_current = date(today.year, today.month, 1)
        
        if today.month == 1:
            first_day_prev = date(today.year - 1, 12, 1)
        else:
            first_day_prev = date(today.year, today.month - 1, 1)

        daily_rows = db.query(
            Transaction.transaction_date,
            func.sum(Transaction.amount).label("daily_amount")
        ).filter(
            Transaction.user_id == user_id,
            Transaction.type == "Expense"
        ).group_by(Transaction.transaction_date).order_by(Transaction.transaction_date.asc()).all()

        daily_trends = [
            {"date": row.transaction_date.isoformat(), "amount": float(row.daily_amount)}
            for row in daily_rows
        ]

        curr_spent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == "Expense",
            Transaction.transaction_date >= first_day_current
        ).scalar() or 0.0

        prev_spent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == "Expense",
            Transaction.transaction_date >= first_day_prev,
            Transaction.transaction_date < first_day_current
        ).scalar() or 0.0

        curr_spent = float(curr_spent)
        prev_spent = float(prev_spent)
        mom_change_amt = round(curr_spent - prev_spent, 2)

        if prev_spent > 0:
            mom_change_pct = round(((curr_spent - prev_spent) / prev_spent) * 100, 1)
        elif curr_spent > 0:
            mom_change_pct = 100.0
        else:
            mom_change_pct = 0.0

        return {
            "daily_trends": daily_trends,
            "current_month_spending": round(curr_spent, 2),
            "previous_month_spending": round(prev_spent, 2),
            "mom_change_amount": mom_change_amt,
            "mom_change_pct": mom_change_pct
        }

    @staticmethod
    def get_stats_and_outliers(db: Session, user_id: int) -> Dict[str, Any]:
        txs = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.type == "Expense"
        ).order_by(Transaction.amount.asc()).all()

        if not txs:
            return {
                "count": 0,
                "mean": 0.0,
                "median": 0.0,
                "std_dev": 0.0,
                "min": 0.0,
                "max": 0.0,
                "q1": 0.0,
                "q3": 0.0,
                "iqr": 0.0,
                "iqr_threshold": 0.0,
                "outliers": []
            }

        amounts = [t.amount for t in txs]
        n = len(amounts)
        mean_val = sum(amounts) / n
        variance = sum((x - mean_val) ** 2 for x in amounts) / n
        std_dev = math.sqrt(variance)

        def percentile(p):
            idx = (n - 1) * p
            lower = math.floor(idx)
            upper = math.ceil(idx)
            if lower == upper:
                return amounts[int(idx)]
            return amounts[lower] + (amounts[upper] - amounts[lower]) * (idx - lower)

        median_val = percentile(0.5)
        q1_val = percentile(0.25)
        q3_val = percentile(0.75)
        iqr_val = q3_val - q1_val
        iqr_threshold = q3_val + (1.5 * iqr_val)

        cat_map = {}
        cats = db.query(Category).filter(Category.user_id == user_id).all()
        for c in cats:
            cat_map[c.id] = c.name

        outliers = []
        for t in txs:
            if t.amount > iqr_threshold and iqr_threshold > 0:
                outliers.append({
                    "id": t.id,
                    "amount": t.amount,
                    "description": t.description,
                    "transaction_date": t.transaction_date.isoformat(),
                    "category_name": cat_map.get(t.category_id, "Uncategorized")
                })

        return {
            "count": n,
            "mean": round(mean_val, 2),
            "median": round(median_val, 2),
            "std_dev": round(std_dev, 2),
            "min": round(min(amounts), 2),
            "max": round(max(amounts), 2),
            "q1": round(q1_val, 2),
            "q3": round(q3_val, 2),
            "iqr": round(iqr_val, 2),
            "iqr_threshold": round(iqr_threshold, 2),
            "outliers": outliers
        }

