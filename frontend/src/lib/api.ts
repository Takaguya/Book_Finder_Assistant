import { auth } from "./firebase";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface BookResult {
  id: string;
  title: string;
  authors: string[];
  description: string | null;
  thumbnail: string | null;
  published_date: string | null;
  categories: string[];
  average_rating: number | null;
  preview_link: string | null;
}

export interface ChatMessageOut {
  reply: string;
  books: BookResult[];
  session_title: string | null;
}

export interface ChatHistoryItem {
  role: "user" | "model";
  text: string;
  created_at: string | null;
  books?: BookResult[];
}

export interface ChatSession {
  id: string;
  title: string;
  updated_at: string | null;
}

async function authHeaders(): Promise<HeadersInit> {
  const user = auth.currentUser;
  if (!user) {
    throw new Error("Not signed in.");
  }
  const token = await user.getIdToken();
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

async function ensureOk(res: Response): Promise<void> {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Request failed (${res.status}): ${body || res.statusText}`);
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  await ensureOk(res);
  return res.json() as Promise<T>;
}

// Gemini calls (plus retry/backoff on the backend) can legitimately take a while, but a
// request should never hang forever with no feedback — surface a clear timeout error instead.
async function fetchWithTimeout(url: string, options: RequestInit, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("The request took too long and timed out. Please try again.");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export async function sendChatMessage(sessionId: string, message: string): Promise<ChatMessageOut> {
  const res = await fetchWithTimeout(
    `${API_BASE_URL}/api/chat`,
    {
      method: "POST",
      headers: await authHeaders(),
      body: JSON.stringify({ session_id: sessionId, message }),
    },
    90_000,
  );
  return handleResponse<ChatMessageOut>(res);
}

export async function listChatSessions(): Promise<ChatSession[]> {
  const res = await fetchWithTimeout(
    `${API_BASE_URL}/api/chat/sessions`,
    { headers: await authHeaders() },
    15_000,
  );
  const data = await handleResponse<{ sessions: ChatSession[] }>(res);
  return data.sessions;
}

export async function createChatSession(): Promise<ChatSession> {
  const res = await fetchWithTimeout(
    `${API_BASE_URL}/api/chat/sessions`,
    { method: "POST", headers: await authHeaders() },
    15_000,
  );
  return handleResponse<ChatSession>(res);
}

export async function deleteChatSession(sessionId: string): Promise<void> {
  const res = await fetchWithTimeout(
    `${API_BASE_URL}/api/chat/sessions/${encodeURIComponent(sessionId)}`,
    { method: "DELETE", headers: await authHeaders() },
    15_000,
  );
  await ensureOk(res);
}

export async function fetchSessionMessages(sessionId: string): Promise<ChatHistoryItem[]> {
  const res = await fetchWithTimeout(
    `${API_BASE_URL}/api/chat/sessions/${encodeURIComponent(sessionId)}/messages`,
    { headers: await authHeaders() },
    15_000,
  );
  const data = await handleResponse<{ messages: ChatHistoryItem[] }>(res);
  return data.messages;
}
