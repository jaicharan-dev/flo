from pydantic import BaseModel
from datetime import date
from typing import Optional, List

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class CategoryCreate(BaseModel):
    name: str
    keywords: Optional[str] = None
    monthly_limit: Optional[float] = None

class TransactionCreate(BaseModel):
    amount: float
    type: str
    description: str
    transaction_date: date
    category_id: Optional[int] = None

class ParseRequest(BaseModel):
    text: str

class CSVUploadResponse(BaseModel):
    imported_count: int
    skipped_count: int
    errors: List[str]
    message: str