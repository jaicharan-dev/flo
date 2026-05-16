# needed imports

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import date, datetime, timedelta
from models import User, SessionLocal
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
import jwt

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "flo-super-secret-key-for-jwt"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# pydantic filters

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class TransactionCreate(BaseModel):
    amount: float
    type: str
    description: str
    transaction_date: date
    category_id: int

# helper functions

# key master
def get_db(): 
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# security guard
def get_current_user(  
        token: str = Depends(oauth2_scheme), 
        db: Session = Depends(get_db)
    ):
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Wristband expired, please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Fake wristband")

    user = db.query(User).filter(User.id == int(user_id)).first()
    return user

# endpoints
# new member sign up desk
@app.post("/register")
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = pwd_context.hash(user_data.password)
    new_user = User(email=user_data.email, password_hash=hashed_pwd)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully", "user_id": new_user.id}


# earning the VIP wristband
@app.post("/login")
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    
    # check email and password
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not pwd_context.verify(user_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # make a wristband
    expiration_time = datetime.utcnow() + timedelta(hours=2)
    
    payload = {
        "sub" : str(user.id),
        "exp" : expiration_time
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": token, 
        "token_type": "bearer",
        "message": "Login successful"
    }

@app.post("/transactions")
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

@app.get("/transactions")
def get_transactions(
        db: Session = Depends(get_db),                 
        current_user: User = Depends(get_current_user)
    ):
    
    user_transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()    
    return user_transactions

@app.put("/transactions/{transaction_id}")
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

@app.delete("/transactions/{transaction_id}")
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
