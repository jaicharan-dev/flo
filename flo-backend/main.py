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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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



@app.post("/login")
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not pwd_context.verify(user_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
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


