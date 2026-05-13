from fastapi import FastAPI

app = FastAPI()

@app.get("/login")
def login_page():
    return {"message": "Please login here"}

@app.get("/search")
def search_items(item: str, limit: int = 10):
    return {
        "query": item,
        "message": f"Finding top {limit} results for {item}"
    }

