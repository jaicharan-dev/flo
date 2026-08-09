from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models import SessionLocal, User
from routers.auth import get_current_user
from schemas import TransactionCreate, CategoryCreate
from services.transaction_service import TransactionService
from services.category_service import CategoryService

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
    TransactionService.create_transaction(db, current_user.id, transaction_data)
    return {"message": "Transaction saved successfully!"}

# --- 2. GET /transactions ---
@router.get("/")
def get_transactions(
    db: Session = Depends(get_db),                 
    current_user: User = Depends(get_current_user),
    category_id: Optional[int] = None,
    limit: int = 5
):
    return TransactionService.get_user_transactions(db, current_user.id, category_id=category_id, limit=limit)

# --- 3. PUT /transactions/{transaction_id} ---
@router.put("/{transaction_id}")
def update_transaction(
    transaction_id: int,                           
    transaction_data: TransactionCreate,           
    db: Session = Depends(get_db),                 
    current_user: User = Depends(get_current_user) 
):
    TransactionService.update_transaction(db, current_user.id, transaction_id, transaction_data)
    return {"message": "Transaction updated successfully!"}

# --- 4. DELETE /transactions/{transaction_id} ---
@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    TransactionService.delete_transaction(db, current_user.id, transaction_id)
    return {"message": "Transaction deleted successfully!"}

# --- 5. POST /categories ---
@router.post("/categories")
def create_category(
    category_data: CategoryCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_category = CategoryService.create_category(db, current_user.id, category_data)
    return {"message": "Category created!", "category_id": new_category.id}

# --- 6. GET /categories ---
@router.get("/categories")
def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return CategoryService.get_user_categories(db, current_user.id)

# --- 7. PUT /categories/{category_id} (Edit) ---
@router.put("/categories/{category_id}")
def update_category(
    category_id: int, 
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    CategoryService.update_category(db, current_user.id, category_id, category_data)
    return {"message": "Category updated successfully!"}

# --- 8. DELETE /categories/{category_id} ---
@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    CategoryService.delete_category(db, current_user.id, category_id)
    return {"message": "Category deleted. Transactions preserved as Uncategorized."}