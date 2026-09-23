from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies.auth import get_current_user
from app.models.schemas import BookResult, BookSearchResponse
from app.services import google_books

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("/search", response_model=BookSearchResponse)
async def search(
    q: str = Query(min_length=1, description="Search query"),
    max_results: int = Query(default=10, ge=1, le=40),
    _user: dict = Depends(get_current_user),
) -> BookSearchResponse:
    return await google_books.search_books(q, max_results=max_results)


@router.get("/{volume_id}", response_model=BookResult)
async def get_book(volume_id: str, _user: dict = Depends(get_current_user)) -> BookResult:
    book = await google_books.get_book(volume_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book
