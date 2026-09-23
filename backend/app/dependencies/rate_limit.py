"""Per-user rate limits, so one account can't run up the Gemini / Google Books bill or flood
Firestore.

Counters live in Firestore (`rate_limits/{uid}`) rather than in memory: on serverless hosts like
Vercel every request may hit a different short-lived instance, so an in-memory counter would
keep resetting and never see a user's full traffic.

Each rule is a fixed window (e.g. "6 per minute" counts requests in the current calendar minute).
All of a route's rules are checked and bumped in one transaction; a request that's refused
doesn't use up any allowance.
"""

import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status

from app.config import Settings, get_settings
from app.dependencies.auth import get_current_user
from app.services import firebase_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Limit:
    key: str  # field name in the user's rate_limits document
    max_requests: int  # 0 or less turns the rule off
    window_seconds: int
    message: str  # shown to the user; {max} and {wait} are filled in


def _chat_limits(s: Settings) -> list[Limit]:
    return [
        Limit("chat_minute", s.rate_limit_chat_per_minute, 60,
              "You're sending messages faster than the assistant can keep up. Try again in {wait}."),
        Limit("chat_day", s.rate_limit_chat_per_day, 86_400,
              "You've used today's {max} messages. You can send more in {wait}."),
    ]


def _new_session_limits(s: Settings) -> list[Limit]:
    return [
        Limit("sessions_hour", s.rate_limit_new_sessions_per_hour, 3_600,
              "You've started {max} conversations in the last hour. Try again in {wait}, "
              "or keep going in an existing one."),
    ]


def _book_search_limits(s: Settings) -> list[Limit]:
    return [
        Limit("books_minute", s.rate_limit_book_searches_per_minute, 60,
              "Too many book searches. Try again in {wait}."),
    ]


def check_limits(state: dict, limits: list[Limit], now: float) -> tuple[dict | None, tuple[Limit, int] | None]:
    """Pure decision step: given the stored counters, either returns the counter updates to write
    (request allowed) or the rule that blocks it plus the seconds until it resets."""
    updates = {}
    for limit in limits:
        window = int(now // limit.window_seconds)
        entry = state.get(limit.key) or {}
        count = entry.get("count", 0) if entry.get("window") == window else 0
        if count >= limit.max_requests:
            retry_after = max(1, math.ceil((window + 1) * limit.window_seconds - now))
            return None, (limit, retry_after)
        updates[limit.key] = {"window": window, "count": count + 1}
    return updates, None


def human_wait(seconds: int) -> str:
    def plural(n: int, unit: str) -> str:
        return f"{n} {unit}" if n == 1 else f"{n} {unit}s"

    if seconds < 60:
        return plural(seconds, "second")
    minutes = math.ceil(seconds / 60)
    if minutes < 60:
        return plural(minutes, "minute")
    return plural(math.ceil(seconds / 3_600), "hour")


def _rate_limited(limits_for: Callable[[Settings], list[Limit]]):
    async def dependency(user: dict = Depends(get_current_user)) -> dict:
        limits = [limit for limit in limits_for(get_settings()) if limit.max_requests > 0]
        if not limits:
            return user

        blocked = await firebase_service.update_rate_limit_state(
            user["uid"], lambda state: check_limits(state, limits, time.time())
        )
        if blocked:
            limit, retry_after = blocked
            logger.warning("Rate limit %s reached by uid=%s", limit.key, user["uid"])
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=limit.message.format(max=limit.max_requests, wait=human_wait(retry_after)),
                headers={"Retry-After": str(retry_after)},
            )
        return user

    return dependency


# Use in place of Depends(get_current_user) on routes that cost money or create data;
# each returns the signed-in user just like get_current_user.
limit_chat = _rate_limited(_chat_limits)
limit_new_sessions = _rate_limited(_new_session_limits)
limit_book_searches = _rate_limited(_book_search_limits)
