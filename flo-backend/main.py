import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import engine, Base

from routers import auth, transactions, analytics

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Flo Personal Finance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(analytics.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Flo API! Visit /docs for the interactive manual."}
