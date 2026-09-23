import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
from typing import TypeVar

import firebase_admin
from fastapi.concurrency import run_in_threadpool
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials, firestore

from app.config import get_settings

_app: firebase_admin.App | None = None
_db = None

DEFAULT_SESSION_TITLE = "New chat"

T = TypeVar("T")


def _load_credentials(settings) -> credentials.Base:
    # 1. The key's JSON in an env var: hosts like Vercel, where a key file can't be shipped safely.
    if settings.firebase_service_account_json:
        try:
            key_info = json.loads(settings.firebase_service_account_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "FIREBASE_SERVICE_ACCOUNT_JSON is set but isn't valid JSON. "
                "Paste the entire contents of the service-account key file."
            ) from exc
        return credentials.Certificate(key_info)
    # 2. The downloaded key file: local development, or Docker with the key mounted.
    if os.path.exists(settings.firebase_service_account_path):
        return credentials.Certificate(settings.firebase_service_account_path)
    # 3. The host's own Google identity (Application Default Credentials): on Cloud Run no key
    #    has to exist anywhere.
    return credentials.ApplicationDefault()


def init_firebase() -> None:
    global _app, _db
    if _app is not None:
        return
    settings = get_settings()
    cred = _load_credentials(settings)
    _app = firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None)
    _db = firestore.client()


def _client():
    if _db is None:
        raise RuntimeError("Firebase has not been initialized. Call init_firebase() on startup.")
    return _db


async def verify_id_token(id_token: str) -> dict:
    """Verifies a Firebase Auth ID token (obtained from Google sign-in on the frontend)."""
    decoded = await run_in_threadpool(firebase_auth.verify_id_token, id_token)
    return decoded


def _user_doc(uid: str):
    return _client().collection("users").document(uid)


def _sessions_collection(uid: str):
    return _user_doc(uid).collection("sessions")


def _session_doc(uid: str, session_id: str):
    return _sessions_collection(uid).document(session_id)


def _messages_collection(uid: str, session_id: str):
    return _session_doc(uid, session_id).collection("messages")


def _fmt_timestamp(value) -> str | None:
    return value.isoformat() if value else None


async def create_session(uid: str, title: str = DEFAULT_SESSION_TITLE) -> dict:
    def _write():
        now = datetime.now(timezone.utc)
        doc_ref = _sessions_collection(uid).document()
        doc_ref.set({"title": title, "created_at": now, "updated_at": now})
        return {"id": doc_ref.id, "title": title, "updated_at": _fmt_timestamp(now)}

    return await run_in_threadpool(_write)


async def list_sessions(uid: str, limit: int = 50) -> list[dict]:
    def _read():
        query = (
            _sessions_collection(uid)
            .order_by("updated_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        results = []
        for doc in query.stream():
            data = doc.to_dict()
            results.append(
                {
                    "id": doc.id,
                    "title": data.get("title") or DEFAULT_SESSION_TITLE,
                    "updated_at": _fmt_timestamp(data.get("updated_at")),
                }
            )
        return results

    return await run_in_threadpool(_read)


async def session_exists(uid: str, session_id: str) -> bool:
    def _read():
        return _session_doc(uid, session_id).get().exists

    return await run_in_threadpool(_read)


async def rename_session(uid: str, session_id: str, title: str) -> None:
    def _write():
        _session_doc(uid, session_id).set({"title": title}, merge=True)

    await run_in_threadpool(_write)


async def delete_session(uid: str, session_id: str) -> None:
    def _delete():
        # recursive_delete also removes the messages subcollection; deleting only the session
        # document would leave its messages orphaned in Firestore.
        _client().recursive_delete(_session_doc(uid, session_id))

    await run_in_threadpool(_delete)


async def append_message(
    uid: str, session_id: str, role: str, text: str, books: list[dict] | None = None
) -> None:
    def _write():
        now = datetime.now(timezone.utc)
        doc_data: dict = {"role": role, "text": text, "created_at": now}
        if books:
            doc_data["books"] = books
        _messages_collection(uid, session_id).add(doc_data)
        _session_doc(uid, session_id).set({"updated_at": now}, merge=True)

    await run_in_threadpool(_write)


async def get_recent_messages(uid: str, session_id: str, limit: int) -> list[dict]:
    def _read():
        query = (
            _messages_collection(uid, session_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        docs = list(query.stream())
        docs.reverse()  # chronological order, oldest first
        return [
            {
                "role": d.get("role"),
                "text": d.get("text"),
                "created_at": _fmt_timestamp(d.get("created_at")),
                "books": d.get("books") or [],
            }
            for d in (doc.to_dict() for doc in docs)
        ]

    return await run_in_threadpool(_read)


async def update_rate_limit_state(uid: str, decide: Callable[[dict], tuple[dict | None, T]]) -> T:
    """Atomically reads this user's rate-limit counters, lets `decide` compute the new ones, and
    writes them back. `decide` returns (updates or None, result) and may run more than once if
    two requests from the same user collide, so it must not have side effects."""

    def _run():
        doc_ref = _client().collection("rate_limits").document(uid)

        @firestore.transactional
        def _in_transaction(transaction):
            snap = doc_ref.get(transaction=transaction)
            updates, result = decide(snap.to_dict() or {})
            if updates:
                transaction.set(doc_ref, updates, merge=True)
            return result

        return _in_transaction(_client().transaction())

    return await run_in_threadpool(_run)


async def get_preference_summary(uid: str) -> str:
    def _read():
        snap = _user_doc(uid).get()
        if not snap.exists:
            return ""
        return snap.to_dict().get("preference_summary", "") or ""

    return await run_in_threadpool(_read)


async def update_preference_summary(uid: str, summary: str) -> None:
    def _write():
        _user_doc(uid).set(
            {
                "preference_summary": summary,
                "preference_updated_at": datetime.now(timezone.utc),
            },
            merge=True,
        )

    await run_in_threadpool(_write)
