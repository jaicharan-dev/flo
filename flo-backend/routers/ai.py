import os
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from models import SessionLocal, User, Transaction, Category, get_db
from routers.auth import get_current_user
from google import genai
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix="/ai",
    tags=["AI Agent"]
)

class QueryRequest(BaseModel):
    query: str

@router.get("/test")
async def test_ai():
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return {"status": "disabled", "message": "GEMINI_API_KEY not configured."}
    try:
        client = genai.Client(api_key=gemini_key)
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say hello from Flo AI!"
        )
        return {"status": "success", "ai_response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini AI Error: {str(e)}")

@router.post("/query")
async def ai_query(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_query = request.query.strip().lower()

    txs = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    categories = db.query(Category).filter(Category.user_id == current_user.id).all()
    cat_map = {c.id: c.name for c in categories}

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            txs_recent = sorted(txs, key=lambda x: x.transaction_date, reverse=True)[:30]
            tx_summary = "\n".join(
                [f"- [{t.transaction_date}] {t.type}: ₹{t.amount:,.2f} | Category: {cat_map.get(t.category_id, 'Uncategorized')} | Description: '{t.description}'" for t in txs_recent]
            )
            context_str = (
                f"User Financial Context:\n"
                f"Total Transactions: {len(txs)}\n"
                f"Total Income: ₹{sum(t.amount for t in txs if t.type == 'Income'):,.2f}\n"
                f"Total Expenses: ₹{sum(t.amount for t in txs if t.type == 'Expense'):,.2f}\n"
                f"Recent Transactions:\n{tx_summary if tx_summary else 'None'}\n"
            )
            prompt = f"{context_str}\nUser Question: {request.query}\nProvide a concise, helpful answer as Flo financial assistant."
            response = await client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            if response.text:
                return {"response": response.text}
        except Exception:
            pass

    total_spent = sum(t.amount for t in txs if t.type == "Expense")
    total_income = sum(t.amount for t in txs if t.type == "Income")

    cat_totals = {}
    for t in txs:
        if t.type == "Expense":
            c_name = cat_map.get(t.category_id, "Uncategorized")
            cat_totals[c_name] = cat_totals.get(c_name, 0.0) + t.amount

    top_cat = max(cat_totals.items(), key=lambda x: x[1]) if cat_totals else ("None", 0.0)
    top_tx = max([t for t in txs if t.type == "Expense"], key=lambda x: x.amount, default=None)

    if "food" in user_query or "dining" in user_query or "eat" in user_query:
        food_spent = sum(t.amount for t in txs if t.type == "Expense" and cat_map.get(t.category_id, "").lower() in ["food", "dining", "restaurants", "groceries"])
        ans = f"You spent ₹{food_spent:,.2f} on Food & Dining."
    elif "most" in user_query or "biggest category" in user_query or "top category" in user_query:
        ans = f"Your highest spending category is **{top_cat[0]}** with total expenses of ₹{top_cat[1]:,.2f}."
    elif "increase" in user_query or "why" in user_query or "higher" in user_query:
        if top_tx:
            ans = f"Your spending increased primarily due to major expenses in **{cat_map.get(top_tx.category_id, 'Uncategorized')}**, such as ₹{top_tx.amount:,.2f} for '{top_tx.description}'."
        else:
            ans = f"Your spending total stands at ₹{total_spent:,.2f} across {len(txs)} transactions."
    elif "biggest" in user_query or "highest" in user_query or "largest" in user_query:
        if top_tx:
            ans = f"Your largest single expense was ₹{top_tx.amount:,.2f} for '{top_tx.description}' on {top_tx.transaction_date}."
        else:
            ans = "No large expenses recorded yet."
    else:
        ans = f"Based on your financial activity: Total Income is ₹{total_income:,.2f}, Total Expenses are ₹{total_spent:,.2f} across {len(txs)} transactions. Top category: {top_cat[0]} (₹{top_cat[1]:,.2f})."

    return {"response": ans}
