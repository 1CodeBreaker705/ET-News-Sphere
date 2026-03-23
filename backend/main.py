from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from security import get_current_user
import models
from routes import router
from vector_store import get_qdrant_client, close_qdrant
import os

# In a real app, initialize DB connection here:
# engine = create_engine(DATABASE_URL)
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ET News-Sphere API")

# Configure CORS for React frontend (Vite usually runs on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect all routes
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    print("Initializing ET News-Sphere API...")
    get_qdrant_client()

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down ET News-Sphere API...")
    close_qdrant()

@app.get("/")
def read_root():
    return {"message": "Welcome to ET News-Sphere API"}

@app.get("/api/profile")
def get_profile(user: dict = Depends(get_current_user)):
    """
    Protected endpoint returning user data extracted from the JWT token.
    """
    return {
        "user_id": user.get("sub"),
        "email": user.get("email"),
        "role": user.get("role"),
        "app_metadata": user.get("app_metadata"),
        "user_metadata": user.get("user_metadata")
    }
