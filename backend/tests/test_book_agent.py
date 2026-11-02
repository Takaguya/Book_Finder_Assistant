import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from openai.types.chat import ChatCompletion

from app.models.schemas import BookResult, BookSearchResponse
from app.services import book_agent
from app.services.book_agent import _books_for_reply, _normalize_title, _visible_text

MARTIAN = BookResult(id="m1", title="The Martian")
HAIL_MARY = BookResult(id="h1", title="Project Hail Mary: A Novel")


def _found(*books: BookResult) -> dict[str, BookResult]:
    return {book.id: book for book in books}


class NormalizeTitleTest(unittest.TestCase):
    def test_drops_subtitles_markdown_and_typographic_punctuation(self):
        self.assertEqual(_normalize_title("Project Hail Mary: A Novel"), "project hail mary")
        self.assertEqual(_normalize_title("Dune (Movie Tie-In)"), "dune")
        self.assertEqual(_normalize_title("**Starseeker’s Deep‑Space Log**"), "starseekers deep-space log")
        self.assertEqual(_normalize_title("Pride & Prejudice"), "pride and prejudice")


class VisibleTextTest(unittest.TestCase):
    def test_removes_hidden_reasoning(self):
        self.assertEqual(_visible_text("<think>let me see\n...</think>\nHello!"), "Hello!")
        self.assertEqual(_visible_text(None), "")


class BooksForReplyTest(unittest.TestCase):
    def test_shelf_follows_the_order_of_bold_titles(self):
        reply = "Try **Project Hail Mary**, then **The Martian**."
        books = _books_for_reply(reply, _found(MARTIAN, HAIL_MARY), "a space novel")
        self.assertEqual([b.id for b in books], ["h1", "m1"])

    def test_books_the_user_named_are_left_out(self):
        reply = "If you liked **The Martian**, read **Project Hail Mary**."
        books = _books_for_reply(reply, _found(MARTIAN, HAIL_MARY), "books like The Martian")
        self.assertEqual([b.id for b in books], ["h1"])

    def test_duplicate_editions_merge_into_the_one_with_a_cover(self):
        plain = BookResult(id="d1", title="Dune")
        with_cover = BookResult(id="d2", title="Dune (Movie Tie-In)", thumbnail="https://example.com/dune.jpg")
        books = _books_for_reply("Read **Dune**.", _found(plain, with_cover), "classic sci-fi")
        self.assertEqual([b.id for b in books], ["d2"])

    def test_without_bold_titles_only_whole_words_match(self):
        rain = BookResult(id="r1", title="Rain")
        self.assertEqual(_books_for_reply("Perfect for a rainy day.", _found(rain), "cozy"), [])
        books = _books_for_reply("Try The Martian by Andy Weir.", _found(MARTIAN, rain), "space")
        self.assertEqual([b.id for b in books], ["m1"])

    def test_reply_naming_no_found_book_gets_an_empty_shelf(self):
        self.assertEqual(_books_for_reply("Happy reading!", _found(MARTIAN), "hi"), [])


def _completion(content: str | None = None, tool_calls: list[dict] | None = None) -> ChatCompletion:
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return ChatCompletion.model_validate({
        "id": "test", "object": "chat.completion", "created": 0, "model": "test",
        "choices": [{"index": 0, "finish_reason": "tool_calls" if tool_calls else "stop", "message": message}],
    })


def _search_call(n: int) -> dict:
    return {
        "id": f"call-{n}", "type": "function",
        "function": {"name": "search_books", "arguments": json.dumps({"query": f"query {n}"})},
    }


class FakeClient:
    """Stands in for AsyncOpenAI: hands out the given responses in order and records each request."""

    def __init__(self, responses: list[ChatCompletion]):
        self._responses = list(responses)
        self.requests: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs) -> ChatCompletion:
        self.requests.append(kwargs)
        return self._responses.pop(0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return None


class SearchCapTest(unittest.IsolatedAsyncioTestCase):
    async def test_searches_past_the_per_round_cap_are_refused(self):
        client = FakeClient([
            _completion(tool_calls=[_search_call(n) for n in range(5)]),
            _completion(content="Read **The Martian**."),
        ])
        search = AsyncMock(return_value=BookSearchResponse(total_items=1, results=[MARTIAN]))
        with patch.object(book_agent, "_client", return_value=client), \
             patch.object(book_agent, "get_settings", return_value=SimpleNamespace(nvidia_model="test")), \
             patch.object(book_agent.google_books, "search_books", search):
            reply, books = await book_agent.generate_reply("a space novel", [], "")

        self.assertEqual(search.await_count, book_agent.MAX_SEARCHES_PER_ROUND)
        # Every tool call still gets an answer; the extra ones get the refusal.
        tool_messages = [m for m in client.requests[-1]["messages"] if m["role"] == "tool"]
        self.assertEqual(len(tool_messages), 5)
        refused = [m for m in tool_messages if "Too many searches" in m["content"]]
        self.assertEqual(len(refused), 5 - book_agent.MAX_SEARCHES_PER_ROUND)
        self.assertEqual(reply, "Read **The Martian**.")
        self.assertEqual([b.id for b in books], ["m1"])


if __name__ == "__main__":
    unittest.main()
