import { useCallback, useEffect, useState } from "react";
import { createChatSession, deleteChatSession, listChatSessions, type ChatSession } from "../lib/api";
import { ChatPanel } from "./ChatPanel";
import { Sidebar } from "./Sidebar";

export function ChatLayout() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await listChatSessions();
        if (cancelled) return;
        if (list.length === 0) {
          const created = await createChatSession();
          if (cancelled) return;
          setSessions([created]);
          setActiveSessionId(created.id);
        } else {
          setSessions(list);
          setActiveSessionId(list[0].id);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load your conversations.");
        }
      } finally {
        if (!cancelled) setLoadingSessions(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleNewChat = useCallback(async () => {
    setError(null);
    try {
      const created = await createChatSession();
      setSessions((prev) => [created, ...prev]);
      setActiveSessionId(created.id);
      setSidebarOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't start a new chat.");
    }
  }, []);

  const handleDelete = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        await deleteChatSession(id);
      } catch (err) {
        console.error("Failed to delete conversation", err);
        return false;
      }
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (id === activeSessionId) {
        // Move to the next most recent conversation, or start a fresh one if that was the last.
        const next = sessions.find((s) => s.id !== id);
        setActiveSessionId(next?.id ?? null);
        if (!next) await handleNewChat();
      }
      return true;
    },
    [activeSessionId, sessions, handleNewChat],
  );

  const handleSelect = useCallback((id: string) => {
    setActiveSessionId(id);
    setSidebarOpen(false);
  }, []);

  const handleSessionRenamed = useCallback((id: string, title: string) => {
    setSessions((prev) => {
      const next = prev.map((s) => (s.id === id ? { ...s, title } : s));
      const idx = next.findIndex((s) => s.id === id);
      if (idx > 0) {
        const [item] = next.splice(idx, 1);
        next.unshift(item);
      }
      return next;
    });
  }, []);

  return (
    <div className="app-shell">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={handleSelect}
        onNewChat={handleNewChat}
        onDelete={handleDelete}
        loading={loadingSessions}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="chat-main">
        {error && <p className="error-text">{error}</p>}
        {activeSessionId ? (
          <ChatPanel
            key={activeSessionId}
            sessionId={activeSessionId}
            title={sessions.find((s) => s.id === activeSessionId)?.title || "New conversation"}
            onSessionRenamed={(title) => handleSessionRenamed(activeSessionId, title)}
            onToggleSidebar={() => setSidebarOpen((v) => !v)}
          />
        ) : (
          !loadingSessions && <p className="hint-text">Starting a new conversation…</p>
        )}
      </div>
    </div>
  );
}
