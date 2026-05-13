from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "postgresql://postgres:krishna@localhost:5432/flo_db" 

engine = create_engine(DATABASE_URL, echo = True)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(50))

Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

new_user = User(name = "Jaicharan")
session.add(new_user)
session.commit()

fetched_user = session.query(User).first()
print(f"Successfully fetched user from database: {fetched_user.name}")