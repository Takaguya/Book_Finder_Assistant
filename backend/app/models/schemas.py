from typing import Literal

from pydantic import BaseModel, Field


class BookResult(BaseModel):
    id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    description: str | None = None
    thumbnail: str | None = None
    published_date: str | None = None
    categories: list[str] = Field(default_factory=list)
    average_rating: float | None = None
    preview_link: str | None = None


class BookSearchResponse(BaseModel):
    total_items: int
    results: list[BookResult]


class ChatMessageIn(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=4000)


class ChatMessageOut(BaseModel):
    reply: str
    books: list[BookResult] = Field(default_factory=list)
    session_title: str | None = None  # set only when this turn renamed the session


class ChatHistoryItem(BaseModel):
    role: Literal["user", "model"]
    text: str
    created_at: str | None = None
    books: list[BookResult] = Field(default_factory=list)


class ChatHistoryResponse(BaseModel):
    messages: list[ChatHistoryItem]


class ChatSession(BaseModel):
    id: str
    title: str
    updated_at: str | None = None


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSession]
