from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import jwt

from models import SessionLocal, User
from schemas import UserCreate

SECRET_KEY = "YOUR_SECRET_KEY" 
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
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

@router.post("/login")
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.password_hash):
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