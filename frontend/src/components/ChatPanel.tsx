import { useEffect, useRef, useState } from "react";
import { fetchSessionMessages, sendChatMessage, type ChatHistoryItem } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { signOutUser } from "../lib/firebase";
import { MessageBubble, type DisplayMessage } from "./MessageBubble";

// Keep in sync with ChatMessageIn.message max_length in backend/app/models/schemas.py
const MAX_MESSAGE_LENGTH = 4000;

const SUGGESTIONS = [
  "A cozy fantasy for a rainy weekend",
  "Books like Project Hail Mary",
  "Short literary fiction I can finish in a day",
];

interface ChatPanelProps {
  sessionId: string;
  title: string;
  onSessionRenamed: (title: string) => void;
  onToggleSidebar: () => void;
}

export function ChatPanel({ sessionId, title, onSessionRenamed, onToggleSidebar }: ChatPanelProps) {
  const { user } = useAuth();
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadingHistory(true);
    (async () => {
      try {
        const history = await fetchSessionMessages(sessionId);
        if (!cancelled) {
          setMessages(history.map((m) => ({ role: m.role, text: m.text, books: m.books })));
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load this conversation.");
        }
      } finally {
        if (!cancelled) setLoadingHistory(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "instant" });
  }, [messages, sending]);

  async function pollForReply(prevCount: number): Promise<ChatHistoryItem[] | null> {
    for (let i = 0; i < 6; i++) {
      await new Promise((resolve) => setTimeout(resolve, 4000));
      try {
        const history = await fetchSessionMessages(sessionId);
        // prevCount = messages before this turn; backend saves user msg + model reply = +2
        if (history.length >= prevCount + 2) return history;
      } catch {
        // ignore transient errors while polling
      }
    }
    return null;
  }

  async function handleSend(preset?: string) {
    const text = (preset ?? input).trim();
    if (!text || sending) return;

    setError(null);
    setInput("");
    const prevCount = messages.length;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setSending(true);

    try {
      const response = await sendChatMessage(sessionId, text);
      setMessages((prev) => [...prev, { role: "model", text: response.reply, books: response.books }]);
      if (response.session_title) {
        onSessionRenamed(response.session_title);
      }
    } catch (err) {
      const isTimeout = err instanceof Error && err.message.includes("timed out");
      if (isTimeout) {
        setError("Still searching. Longer requests can take up to half a minute.");
        const recovered = await pollForReply(prevCount);
        if (recovered) {
          setError(null);
          setMessages(recovered.map((m) => ({ role: m.role, text: m.text, books: m.books })));
        } else {
          setError("The reply took too long. Your message was saved — refresh to see the response.");
        }
      } else {
        // A failed turn (rate limit, AI service unavailable…) saves nothing on the backend, so
        // take the message back out of the conversation and return it to the box to resend.
        setMessages((prev) => prev.slice(0, -1));
        setInput(text);
        setError(err instanceof Error ? err.message : "Something went wrong.");
      }
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="chat-panel">
      <header className="chat-header">
        <button className="sidebar-toggle" onClick={onToggleSidebar} aria-label="Show conversations">
          <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
            <path d="M2 4.5h14M2 9h14M2 13.5h14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </button>
        <h1 className="chat-header-title">{title}</h1>
        <div className="chat-header-user">
          {user?.photoURL && <img src={user.photoURL} alt="" className="avatar" />}
          <span className="user-name">{user?.displayName}</span>
          <button className="signout-btn" onClick={signOutUser}>
            Sign out
          </button>
        </div>
      </header>

      <div className="messages-scroll" ref={scrollRef}>
        <div className="messages">
          {loadingHistory ? (
            <p className="hint-text">Opening this conversation…</p>
          ) : messages.length === 0 ? (
            <div className="empty-state">
              <h2 className="empty-title">What do you feel like reading?</h2>
              <p className="empty-body">
                Describe a mood, a book you loved, or a subject you're curious about.
              </p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="suggestion" onClick={() => handleSend(s)} disabled={sending}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) => <MessageBubble key={i} message={m} />)
          )}
          {sending && (
            <div className="message from-model">
              <p className="model-text searching" role="status">
                Searching the shelves<span className="dots" aria-hidden="true" />
              </p>
            </div>
          )}
        </div>
      </div>

      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}

      <div className="composer">
        <div className="composer-box">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask for a book, an author, or a mood"
            aria-label="Message"
            maxLength={MAX_MESSAGE_LENGTH}
            rows={1}
          />
          <button className="send-btn" onClick={() => handleSend()} disabled={sending || !input.trim()}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
