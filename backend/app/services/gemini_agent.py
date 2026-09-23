from google import genai
from google.genai import types

from app.config import get_settings
from app.models.schemas import BookResult
from app.services import google_books

MAX_TOOL_ROUNDS = 4

SYSTEM_INSTRUCTION = """You are "Bookish", a warm, knowledgeable book recommendation assistant.

Your job:
- Help the user discover books to read: recommendations, comparisons, "books like X", genre/mood based picks, author deep-dives, etc.
- ALWAYS call the `search_books` tool to look up real books via the Google Books API before recommending specific titles.
  Never invent a title, author, or description from memory — ground every recommendation in a search result.
- You may call `search_books` more than once (e.g. to try a different query) if the first results are not a good fit.
- When you reply, write a short, friendly explanation of WHY each book fits what the user asked for. Keep it concise.
- Do not repeat long raw descriptions verbatim; summarize in your own words.
- If the user is chit-chatting or asking something unrelated to books, respond naturally without forcing a search.

You are also given a running summary of this specific user's reading preferences (genres, authors, tone, past likes/dislikes)
built up from earlier conversations. Use it to personalize recommendations, but don't mention the summary mechanism itself."""

SEARCH_BOOKS_DECLARATION = types.FunctionDeclaration(
    name="search_books",
    description="Search the Google Books catalog for real books matching a query (title, author, genre, topic, or mood).",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "query": types.Schema(
                type=types.Type.STRING,
                description="Search terms, e.g. 'cozy fantasy books like Howl's Moving Castle' or 'Brandon Sanderson'.",
            ),
            "max_results": types.Schema(
                type=types.Type.INTEGER,
                description="How many results to fetch (1-10). Defaults to 5.",
            ),
        },
        required=["query"],
    ),
)

BOOKS_TOOL = types.Tool(function_declarations=[SEARCH_BOOKS_DECLARATION])


# The SDK does not retry by default (1 attempt, no backoff) unless retry_options
# is set explicitly — without this, a single transient 503 from Gemini crashes the request.
_RETRY_OPTIONS = types.HttpRetryOptions(attempts=4, initial_delay=1.0, max_delay=8.0, exp_base=2.0)


def _get_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(retry_options=_RETRY_OPTIONS),
    )


def _history_to_contents(history: list[dict]) -> list[types.Content]:
    contents = []
    for item in history:
        role = "model" if item.get("role") == "model" else "user"
        text = item.get("text", "")
        if not text:
            continue
        contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
    return contents


def _extract_function_calls(response: types.GenerateContentResponse) -> list[types.FunctionCall]:
    candidate = response.candidates[0]
    return [
        part.function_call
        for part in candidate.content.parts
        if getattr(part, "function_call", None) is not None
    ]


def _book_to_tool_payload(book: BookResult) -> dict:
    return {
        "id": book.id,
        "title": book.title,
        "authors": book.authors,
        "published_date": book.published_date,
        "categories": book.categories,
        "average_rating": book.average_rating,
        "description": (book.description or "")[:600],
    }


async def generate_reply(
    user_message: str,
    history: list[dict],
    preference_summary: str,
) -> tuple[str, list[BookResult]]:
    """Runs the book-recommendation agent for one turn.

    Uses the async Chat API (client.aio.chats) rather than calling
    Models.generate_content directly — Google recommends Chat.send_message for
    multi-turn conversations, and since our search_books tool is declared
    declaratively (not as a Python callable) the SDK's automatic function
    calling never applies to it anyway, so we drive the tool-call loop by hand.
    """
    settings = get_settings()
    client = _get_client()

    system_instruction = SYSTEM_INSTRUCTION
    if preference_summary:
        system_instruction += f"\n\nKnown user preference summary:\n{preference_summary}"

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[BOOKS_TOOL],
        temperature=0.7,
    )

    chat = client.aio.chats.create(
        model=settings.gemini_model,
        config=config,
        history=_history_to_contents(history),
    )

    found_books: dict[str, BookResult] = {}
    message: str | list[types.Part] = user_message

    for _ in range(MAX_TOOL_ROUNDS):
        response = await chat.send_message(message)
        function_calls = _extract_function_calls(response)

        if not function_calls:
            final_text = response.text or "I couldn't come up with a response — could you rephrase that?"
            return final_text, list(found_books.values())

        function_response_parts = []
        for call in function_calls:
            args = dict(call.args or {})
            query = args.get("query", "")
            max_results = int(args.get("max_results") or 5)

            search_result = await google_books.search_books(query, max_results=max_results)
            for book in search_result.results:
                found_books[book.id] = book

            payload = {
                "total_items": search_result.total_items,
                "results": [_book_to_tool_payload(b) for b in search_result.results],
            }
            function_response_parts.append(
                types.Part.from_function_response(name=call.name, response={"result": payload})
            )

        message = function_response_parts

    # Ran out of tool-call rounds; send the last pending tool result with tools
    # disabled so the model is forced to produce a plain-text final answer.
    # No tools on this call, so also explicitly disable AFC (see summarize_preferences).
    response = await chat.send_message(
        message,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )
    return response.text or "Here's what I found so far.", list(found_books.values())


async def summarize_preferences(
    previous_summary: str,
    user_message: str,
    assistant_reply: str,
) -> str:
    """Updates a running natural-language summary of the user's reading preferences."""
    settings = get_settings()
    client = _get_client()

    prompt = f"""Existing summary of this user's book preferences (may be empty):
---
{previous_summary or "(none yet)"}
---

New exchange:
User: {user_message}
Assistant: {assistant_reply}

Update the summary to fold in anything new about this user's reading preferences: favorite genres, authors,
themes, moods, formats, things they disliked, etc. Keep it under 120 words, third person, plain text,
no bullet points, no preamble. If nothing new was revealed, return the existing summary unchanged."""

    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
        # No tools are used here, so explicitly disable automatic function calling —
        # otherwise it's "enabled" by default on every AsyncModels.generate_content
        # call and the SDK logs its "use AsyncChat.send_message instead" warning.
        config=types.GenerateContentConfig(
            temperature=0.2,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )
    return (response.text or previous_summary).strip()
