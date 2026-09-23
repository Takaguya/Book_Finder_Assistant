import httpx

from app.config import get_settings
from app.models.schemas import BookResult, BookSearchResponse

BASE_URL = "https://www.googleapis.com/books/v1/volumes"


def _parse_volume(item: dict) -> BookResult:
    info = item.get("volumeInfo", {})
    image_links = info.get("imageLinks", {})
    return BookResult(
        id=item.get("id", ""),
        title=info.get("title", "Untitled"),
        authors=info.get("authors", []),
        description=info.get("description"),
        thumbnail=image_links.get("thumbnail") or image_links.get("smallThumbnail"),
        published_date=info.get("publishedDate"),
        categories=info.get("categories", []),
        average_rating=info.get("averageRating"),
        preview_link=info.get("previewLink"),
    )


async def search_books(query: str, max_results: int = 8) -> BookSearchResponse:
    settings = get_settings()
    params = {
        "q": query,
        "maxResults": min(max(max_results, 1), 40),
    }
    if settings.google_books_api_key:
        params["key"] = settings.google_books_api_key

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

    items = data.get("items", [])
    return BookSearchResponse(
        total_items=data.get("totalItems", 0),
        results=[_parse_volume(item) for item in items],
    )


async def get_book(volume_id: str) -> BookResult | None:
    settings = get_settings()
    params = {}
    if settings.google_books_api_key:
        params["key"] = settings.google_books_api_key

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{BASE_URL}/{volume_id}", params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return _parse_volume(response.json())
