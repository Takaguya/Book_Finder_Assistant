import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

# A placeholder, set before the app loads its settings: nothing in these tests calls the real AI.
os.environ.setdefault("NVIDIA_API_KEY", "test-key")

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.dependencies.rate_limit import limit_chat  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import chat  # noqa: E402
from app.services import firebase_service  # noqa: E402

CHAT_REQUEST = {"session_id": "abc123", "message": "Any good space novels?"}


class ChatEndpointTest(unittest.TestCase):
    def setUp(self):
        # Signed in as a test user, with Firestore replaced by mocks. The client isn't used as a
        # context manager, so the app's startup (connecting to Firebase) never runs.
        app.dependency_overrides[limit_chat] = lambda: {"uid": "test-user"}
        self.addCleanup(app.dependency_overrides.clear)
        self.db = {}
        for name, result in [("session_exists", True), ("get_recent_messages", []),
                             ("get_preference_summary", ""), ("append_message", None)]:
            self.db[name] = patch.object(firebase_service, name, AsyncMock(return_value=result)).start()
        self.addCleanup(patch.stopall)
        self.client = TestClient(app)

    def test_reply_that_misses_the_deadline_is_refused_and_not_saved(self):
        async def slow_reply(*_args):
            await asyncio.sleep(5)

        with patch.object(chat, "REPLY_DEADLINE_SECONDS", 0.05), \
             patch.object(chat, "generate_reply", slow_reply), \
             self.assertLogs("app.routers.chat", level="WARNING"):
            res = self.client.post("/api/chat", json=CHAT_REQUEST)

        self.assertEqual(res.status_code, 504)
        self.assertIn("took too long", res.json()["detail"])
        self.db["append_message"].assert_not_awaited()

    def test_unexpected_error_is_json_the_browser_can_read(self):
        origin = get_settings().cors_origin_list[0]
        self.db["session_exists"].side_effect = RuntimeError("Firestore is unreachable")

        with self.assertLogs("app.main", level="ERROR"):
            res = self.client.post("/api/chat", json=CHAT_REQUEST, headers={"Origin": origin})

        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.headers.get("access-control-allow-origin"), origin)
        self.assertIsInstance(res.json()["detail"], str)


if __name__ == "__main__":
    unittest.main()
