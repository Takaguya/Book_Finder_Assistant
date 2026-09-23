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


settings = get_settings()

app = FastAPI(
    title="Book Finder Assistant API",
    lifespan=lifespan,
    docs_url="/docs" if settings.api_docs_enabled else None,
    redoc_url="/redoc" if settings.api_docs_enabled else None,
    openapi_url="/openapi.json" if settings.api_docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # The frontend authenticates with a bearer token, never cookies, so credentials stay off,
    # and only the methods and headers it actually sends are allowed.
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(books.router)
app.include_router(chat.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
