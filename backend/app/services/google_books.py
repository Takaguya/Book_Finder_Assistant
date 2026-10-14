import asyncio

import httpx

from app.config import get_settings
from app.models.schemas import BookResult, BookSearchResponse

BASE_URL = "https://www.googleapis.com/books/v1/volumes"
# Google Books occasionally answers 503 / 429 for a moment; a short retry usually succeeds.
RETRY_STATUSES = {429, 500, 502, 503, 504}
RETRY_DELAYS = (0.5, 1.5)


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


def _headers() -> dict:
    # The key goes in a header rather than the URL, so it never shows up in error messages or logs
    # (httpx includes the full URL when a request fails).
    key = get_settings().google_books_api_key
    return {"X-Goog-Api-Key": key} if key else {}


async def _get(client: httpx.AsyncClient, url: str, params: dict | None = None) -> httpx.Response:
    for delay in (*RETRY_DELAYS, None):
        try:
            response = await client.get(url, params=params, headers=_headers())
        except httpx.TransportError:
            if delay is None:
                raise
        else:
            if response.status_code not in RETRY_STATUSES or delay is None:
                return response
        await asyncio.sleep(delay)
    raise AssertionError("unreachable")


async def search_books(query: str, max_results: int = 8) -> BookSearchResponse:
    params = {"q": query, "maxResults": min(max(max_results, 1), 40)}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await _get(client, BASE_URL, params)
        response.raise_for_status()
        data = response.json()

    items = data.get("items", [])
    return BookSearchResponse(
        total_items=data.get("totalItems", 0),
        results=[_parse_volume(item) for item in items],
    )


async def get_book(volume_id: str) -> BookResult | None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await _get(client, f"{BASE_URL}/{volume_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return _parse_volume(response.json())
