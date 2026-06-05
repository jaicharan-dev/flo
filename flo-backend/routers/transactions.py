from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import SessionLocal, Transaction, Category, User
from routers.auth import get_current_user

from schemas import TransactionCreate, CategoryCreate

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions & Categories"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 1. POST /transactions ---
@router.post("/")
def add_transaction(
    transaction_data: TransactionCreate, 
    db: Session = Depends(get_db),       
    current_user: User = Depends(get_current_user) 
):
    new_transaction = Transaction(
        amount=transaction_data.amount,
        type=transaction_data.type,
        description=transaction_data.description,
        transaction_date=transaction_data.transaction_date,
        category_id=transaction_data.category_id,
        user_id=current_user.id 
    )
    db.add(new_transaction)
    db.commit()
    return {"message": "Transaction saved successfully!"}

# --- 2. GET /transactions ---
@router.get("/")
def get_transactions(
        db: Session = Depends(get_db),                 
        current_user: User = Depends(get_current_user),
        category_id: Optional[int] = None,
        limit: int = 5
    ):
    
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)    
    
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    
    user_transactions = query.order_by(Transaction.id.desc()).limit(limit).all()
    return user_transactions

# --- 3. PUT /transactions/{transaction_id} ---
@router.put("/{transaction_id}")
def update_transaction(
        transaction_id: int,                           
        transaction_data: TransactionCreate,           
        db: Session = Depends(get_db),                 
        current_user: User = Depends(get_current_user) 
    ):
    
    transaction_to_update = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    if not transaction_to_update:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    if transaction_to_update.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own transactions")
        
    transaction_to_update.amount = transaction_data.amount
    transaction_to_update.type = transaction_data.type
    transaction_to_update.description = transaction_data.description
    transaction_to_update.transaction_date = transaction_data.transaction_date
    transaction_to_update.category_id = transaction_data.category_id
    
    db.commit()
    return {"message": "Transaction updated successfully!"}

# --- 4. DELETE /transactions/{transaction_id} ---
@router.delete("/transactions/{transaction_id}")
def delete_transaction(
        transaction_id: int, 
        db: Session = Depends(get_db), 
        current_user: User = Depends(get_current_user)
    ):
    
    transaction_to_delete = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    if not transaction_to_delete:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    if transaction_to_delete.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own transactions")
        
    db.delete(transaction_to_delete)
    db.commit()
    return {"message": "Transaction deleted successfully!"}

# --- 5. POST /categories ---
@router.post("/categories")
def create_category(
    category_data: CategoryCreate, 
    db: Session = Depends(get_db)
):
    new_category = Category(
        name=category_data.name,
        keywords=category_data.keywords,
        monthly_limit=category_data.monthly_limit
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return {"message": "Category created!", "category_id": new_category.id}

# --- 6. GET /categories ---
@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    # Fetch all categories from the database
    categories = db.query(Category).all()
    return categories