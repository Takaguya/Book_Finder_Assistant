from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import books, chat
from app.services.firebase_service import init_firebase


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_firebase()
    yield


app = FastAPI(title="Book Finder Assistant API", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books.router)
app.include_router(chat.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
