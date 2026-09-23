import logging

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path
from google.genai import errors as genai_errors

from app.config import get_settings
from app.dependencies.auth import get_current_user
from app.dependencies.rate_limit import limit_chat, limit_new_sessions
from app.models.schemas import (
    SESSION_ID_PATTERN,
    ChatHistoryResponse,
    ChatMessageIn,
    ChatMessageOut,
    ChatSession,
    ChatSessionListResponse,
)
from app.services import firebase_service
from app.services.gemini_agent import generate_reply, summarize_preferences

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

MAX_TITLE_LENGTH = 48

SessionId = Annotated[str, Path(pattern=SESSION_ID_PATTERN)]


@router.get("/sessions", response_model=ChatSessionListResponse)
async def get_sessions(user: dict = Depends(get_current_user)) -> ChatSessionListResponse:
    sessions = await firebase_service.list_sessions(user["uid"])
    return ChatSessionListResponse(sessions=sessions)


@router.post("/sessions", response_model=ChatSession, status_code=201)
async def create_session(user: dict = Depends(limit_new_sessions)) -> ChatSession:
    session = await firebase_service.create_session(user["uid"])
    return ChatSession(**session)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: SessionId, user: dict = Depends(get_current_user)) -> None:
    # Idempotent: deleting a session that's already gone still succeeds, since the outcome
    # the client wants (the session no longer exists) holds either way.
    await firebase_service.delete_session(user["uid"], session_id)


@router.get("/sessions/{session_id}/messages", response_model=ChatHistoryResponse)
async def get_session_messages(
    session_id: SessionId, user: dict = Depends(get_current_user)
) -> ChatHistoryResponse:
    uid = user["uid"]
    if not await firebase_service.session_exists(uid, session_id):
        raise HTTPException(status_code=404, detail="Chat session not found.")
    settings = get_settings()
    messages = await firebase_service.get_recent_messages(uid, session_id, settings.chat_history_limit)
    return ChatHistoryResponse(messages=messages)


@router.post("", response_model=ChatMessageOut)
async def chat(
    payload: ChatMessageIn,
    background_tasks: BackgroundTasks,
    user: dict = Depends(limit_chat),
) -> ChatMessageOut:
    settings = get_settings()
    uid = user["uid"]
    session_id = payload.session_id

    if not await firebase_service.session_exists(uid, session_id):
        raise HTTPException(status_code=404, detail="Chat session not found.")

    history, preference_summary = await _load_context(uid, session_id, settings.chat_history_limit)
    is_first_message = len(history) == 0

    try:
        reply_text, books = await generate_reply(payload.message, history, preference_summary)
    except genai_errors.ServerError as exc:
        logger.warning("Gemini server error during chat: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="The book assistant is temporarily unavailable (upstream AI service is overloaded). Please try again shortly.",
        ) from exc
    except genai_errors.ClientError as exc:
        logger.error("Gemini client error during chat: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="The book assistant couldn't process that request. Please try again.",
        ) from exc

    # The user may have deleted this conversation while the reply was generating. Saving now
    # would recreate it as an untitled session holding these two messages.
    if not await firebase_service.session_exists(uid, session_id):
        raise HTTPException(status_code=404, detail="This conversation was deleted.")

    await firebase_service.append_message(uid, session_id, "user", payload.message)
    await firebase_service.append_message(
        uid, session_id, "model", reply_text,
        books=[b.model_dump() for b in books],
    )

    session_title = None
    if is_first_message:
        session_title = _derive_title(payload.message)
        await firebase_service.rename_session(uid, session_id, session_title)

    # Preference-summary learning is a second full Gemini call that the user never sees the
    # result of directly — run it after the response is sent instead of making the user wait
    # through two sequential Gemini round-trips (this was doubling response time / timeouts).
    background_tasks.add_task(
        _update_preference_summary, uid, preference_summary, payload.message, reply_text
    )

    return ChatMessageOut(reply=reply_text, books=books, session_title=session_title)


def _derive_title(message: str) -> str:
    title = " ".join(message.split())  # collapse whitespace/newlines
    if len(title) > MAX_TITLE_LENGTH:
        title = title[: MAX_TITLE_LENGTH - 1].rstrip() + "…"
    return title or firebase_service.DEFAULT_SESSION_TITLE


async def _load_context(uid: str, session_id: str, limit: int) -> tuple[list[dict], str]:
    history = await firebase_service.get_recent_messages(uid, session_id, limit)
    preference_summary = await firebase_service.get_preference_summary(uid)
    return history, preference_summary


async def _update_preference_summary(
    uid: str, previous_summary: str, user_message: str, assistant_reply: str
) -> None:
    try:
        updated_summary = await summarize_preferences(previous_summary, user_message, assistant_reply)
        if updated_summary and updated_summary != previous_summary:
            await firebase_service.update_preference_summary(uid, updated_summary)
    except genai_errors.APIError as exc:
        logger.warning("Skipping preference-summary update after Gemini error: %s", exc)
