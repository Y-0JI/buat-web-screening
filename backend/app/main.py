from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.research import router as research_router

app = FastAPI(title="BSJP AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)


@app.get("/")
async def root():
    return {"app": "BSJP AI", "version": "0.1.0"}
