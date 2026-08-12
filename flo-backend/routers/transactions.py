from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from models import SessionLocal, User, Category, get_db
from routers.auth import get_current_user
from schemas import TransactionCreate, CategoryCreate, ParseRequest, CSVUploadResponse
from services.transaction_service import TransactionService
from services.category_service import CategoryService
from services.transaction_parser import TransactionParser
from services.categorization_engine import CategorizationEngine
from services.csv_service import CSVService

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions & Categories"]
)

# --- 0. POST /transactions/upload-csv (Bulk CSV Statement Ingestion) ---
@router.post("/upload-csv", response_model=CSVUploadResponse)
def upload_csv_transactions(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return CSVService.process_csv_upload(db=db, user_id=current_user.id, file=file)

# --- 0. POST /transactions/parse (Natural Language Parser) ---
@router.post("/parse")
def parse_transaction_text(
    payload: ParseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    parsed = TransactionParser.parse(text=payload.text)
    user_categories = db.query(Category).filter(Category.user_id == current_user.id).all()
    
    suggested_category_id = None
    suggested_category_name = None
    if parsed.description:
        cat_result = CategorizationEngine.categorize(
            description=parsed.description,
            user_categories=user_categories,
            use_llm_fallback=True
        )
        if cat_result:
            suggested_category_id = cat_result.category_id
            suggested_category_name = cat_result.category_name or cat_result.proposed_category_name

    return {
        "parsed_transaction": parsed,
        "suggested_category_id": suggested_category_id,
        "suggested_category_name": suggested_category_name
    }

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