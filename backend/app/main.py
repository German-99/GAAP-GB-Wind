"""API entry point. Run with: uvicorn app.main:app --reload"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from app.api.routes import router
from app.config import CORS_ORIGINS
 
app = FastAPI(
    title="Wind Forecast Accuracy API",
    description="Wind forecast in effect at the time of day-ahead decision-making, and its accuracy (Elexon).",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["GET"], allow_headers=["*"]
)
app.include_router(router)
 
 
@app.get("/health")
def health():
    return {"status": "ok"}