from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.dependencies.rate_limit import limit_book_searches
from app.models.schemas import BookResult, BookSearchResponse
from app.services import google_books

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("/search", response_model=BookSearchResponse)
async def search(
    q: str = Query(min_length=1, max_length=200, description="Search query"),
    max_results: int = Query(default=10, ge=1, le=40),
    _user: dict = Depends(limit_book_searches),
) -> BookSearchResponse:
    return await google_books.search_books(q, max_results=max_results)


@router.get("/{volume_id}", response_model=BookResult)
async def get_book(
    # Google Books volume IDs are letters, digits, '-' and '_'. The ID is placed into the
    # Google Books URL, so anything else (like '?' or '#') is refused.
    volume_id: str = Path(pattern=r"^[A-Za-z0-9_-]{1,64}$"),
    _user: dict = Depends(limit_book_searches),
) -> BookResult:
    book = await google_books.get_book(volume_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book
