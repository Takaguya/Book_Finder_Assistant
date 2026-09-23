# Book Finder Assistant

A chatbot that recommends and finds real books. A FastAPI backend runs a Gemini agent that
searches the Google Books API through `search_books` function calling. A React frontend signs
people in with Google (Firebase Auth) and lets them chat with the agent.

- Multiple conversations in a sidebar: start new ones, switch between them, delete old ones.
- Recommendations appear as book covers on a shelf, each linking to Google Books.
- Light, dark, or follow-the-system theme.
- Long-term personalization: after every turn, a short natural-language "preference summary"
  of the user's taste is rebuilt and shared across all of their conversations, so the agent
  remembers more than the current chat.

## Architecture

```
frontend (React + Vite + TS)
  -> Firebase Auth (Google sign-in) -> gets Firebase ID token
  -> calls backend with "Authorization: Bearer <id token>"
  -> sidebar lists conversations; "New conversation" starts one, each can be deleted

backend (FastAPI)
  -> verifies ID token with Firebase Admin SDK
  -> GET    /api/books/search                  -> Google Books API
  -> GET    /api/chat/sessions                 -> Firestore (list this user's sessions)
  -> POST   /api/chat/sessions                 -> Firestore (create a new session)
  -> DELETE /api/chat/sessions/{id}            -> Firestore (delete a session and its messages)
  -> GET    /api/chat/sessions/{id}/messages   -> Firestore (that session's history)
  -> POST   /api/chat                          -> Gemini agent
       - loads that session's recent history + the user's (cross-session) preference summary
       - Gemini calls the search_books tool -> Google Books API
       - reply + book results returned to frontend; first turn also names the session
       - both messages appended to Firestore under that session
       - preference summary re-generated as a background task after the response is sent
```

Firestore layout: `users/{uid}` holds the cross-session `preference_summary`; each conversation
lives under `users/{uid}/sessions/{sessionId}` (with a `title`) and its own
`users/{uid}/sessions/{sessionId}/messages` subcollection.

## 1. Prerequisites

1. **Google Books API key**: Google Cloud Console → enable "Books API" → create an API key
   (restrict it to the Books API). Used server-side only.
2. **Gemini API key**: https://aistudio.google.com/apikey
3. **Firebase project**: https://console.firebase.google.com
   - Enable **Authentication → Sign-in method → Google**.
   - Enable **Firestore Database**. The browser never reads Firestore directly (only the
     backend does), so the security rules can deny all client access.
   - Under **Project settings → General → Your apps**, add a **Web app** and copy the config
     values into `frontend/.env`.
   - Under **Project settings → Service accounts**, click **Generate new private key** and save
     the JSON as `backend/serviceAccountKey.json` (never commit this file).

## 2. Backend setup

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env            # fill in GEMINI_API_KEY, GOOGLE_BOOKS_API_KEY, FIREBASE_PROJECT_ID
# place serviceAccountKey.json in backend/ (path configured via FIREBASE_SERVICE_ACCOUNT_PATH)
uvicorn app.main:app --reload --port 8000
```

API docs at http://localhost:8000/docs once running.

## 3. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env   # fill in Firebase web config + VITE_API_BASE_URL
npm run dev
```

Open http://localhost:5173, sign in with Google, and start chatting.

## 4. Running with Docker

Each service has its own `Dockerfile` (`backend/Dockerfile`, `frontend/Dockerfile`), and
`docker-compose.yml` at the repo root wires them together: backend on `:8000`, frontend
(built and served by nginx) on `:8080`.

```bash
cp .env.example .env                   # VITE_* web config + CORS_ORIGINS, used at frontend build time
cp backend/.env.example backend/.env   # GEMINI_API_KEY, GOOGLE_BOOKS_API_KEY, etc.
# place your Firebase service account key at backend/serviceAccountKey.json

docker compose up --build
```

Frontend at http://localhost:8080, backend at http://localhost:8000. Because Vite bakes
`VITE_*` values into the built JS bundle, changing anything in the root `.env` requires
`docker compose build frontend` again (not just a restart).

Each Dockerfile also works on its own, without compose:

```bash
docker build -t book-finder-backend backend/
docker run -p 8000:8000 --env-file backend/.env \
  -v $(pwd)/backend/serviceAccountKey.json:/app/serviceAccountKey.json:ro \
  book-finder-backend

docker build -t book-finder-frontend frontend/ \
  --build-arg VITE_API_BASE_URL=http://localhost:8000 \
  --build-arg VITE_FIREBASE_API_KEY=... # ...and the other VITE_FIREBASE_* args
docker run -p 8080:80 book-finder-frontend
```

Both containers listen on `$PORT` when it's set (backend defaults to `8000`, frontend to `80`),
so the same images also run on container platforms that assign their own port.

## Notes

- The agent (`backend/app/services/gemini_agent.py`) is instructed to always ground
  recommendations in a real `search_books` tool call rather than inventing titles.
- Long-term personalization: after every chat turn, `summarize_preferences()` asks Gemini to fold
  the new exchange into a short running summary stored on the user's Firestore doc
  (`users/{uid}.preference_summary`). That summary, plus the last `CHAT_HISTORY_LIMIT` messages,
  is injected into the system instruction on the next turn.
- CORS origins for the backend are controlled via `CORS_ORIGINS` in `backend/.env`.
- The backend uses `serviceAccountKey.json` when the file exists. Without it, it falls back to
  Google Application Default Credentials (for example, a Cloud Run service's own identity).
