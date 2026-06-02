from pydantic import BaseModel
from datetime import date
from typing import Optional

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
    category_id: int