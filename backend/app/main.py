import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import chat
from app.services.firebase_service import init_firebase

logger = logging.getLogger(__name__)


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


# Registered before CORSMiddleware so it runs inside it. FastAPI's own 500 response for an
# unhandled error is built outside every middleware, so it has no CORS headers and the browser
# reports a CORS failure instead of the error. This turns the error into a normal JSON response.
@app.middleware("http")
async def unexpected_errors_as_json(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong on our side. Please try again."},
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

app.include_router(chat.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
