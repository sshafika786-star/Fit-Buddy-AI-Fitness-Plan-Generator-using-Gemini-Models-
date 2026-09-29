from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="FitBuddy – AI Fitness Plan Generator",
    description="FastAPI + SQLite + Gemini AI fitness-plan application.",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(router)
