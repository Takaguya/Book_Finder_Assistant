import { useEffect, useRef, useState } from "react";
import type { ChatSession } from "../lib/api";
import { BrandMark } from "./BrandMark";
import { ThemeSwitch } from "./ThemeSwitch";

interface SidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onDelete: (id: string) => Promise<boolean>;
  loading: boolean;
  open: boolean;
  onClose: () => void;
}

export function Sidebar({
  sessions,
  activeSessionId,
  onSelect,
  onNewChat,
  onDelete,
  loading,
  open,
  onClose,
}: SidebarProps) {
  // Only one conversation can be awaiting delete confirmation at a time.
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [failedId, setFailedId] = useState<string | null>(null);

  function startConfirm(id: string) {
    setFailedId(null);
    setConfirmingId(id);
  }

  async function confirmDelete(id: string) {
    setFailedId(null);
    setDeletingId(id);
    const deleted = await onDelete(id);
    setDeletingId(null);
    if (deleted) setConfirmingId(null);
    else setFailedId(id);
  }

  return (
    <>
      <div className={`sidebar-backdrop ${open ? "visible" : ""}`} onClick={onClose} />
      <aside className={`sidebar ${open ? "open" : ""}`} aria-label="Conversations">
        <div className="sidebar-brand">
          <BrandMark />
          <span className="sidebar-brand-text">Book Finder</span>
        </div>

        <button className="new-chat-btn" onClick={onNewChat}>
          New conversation
        </button>

        <nav className="session-list">
          {loading ? (
            <p className="sidebar-hint">Loading conversations…</p>
          ) : sessions.length === 0 ? (
            <p className="sidebar-hint">Your conversations will appear here.</p>
          ) : (
            sessions.map((s) => (
              <SessionRow
                key={s.id}
                session={s}
                active={s.id === activeSessionId}
                confirming={s.id === confirmingId}
                deleting={s.id === deletingId}
                failed={s.id === failedId}
                onSelect={() => onSelect(s.id)}
                onRequestDelete={() => startConfirm(s.id)}
                onConfirmDelete={() => confirmDelete(s.id)}
                onCancelDelete={() => setConfirmingId(null)}
              />
            ))
          )}
        </nav>

        <div className="sidebar-footer">
          <ThemeSwitch />
        </div>
      </aside>
    </>
  );
}

interface SessionRowProps {
  session: ChatSession;
  active: boolean;
  confirming: boolean;
  deleting: boolean;
  failed: boolean;
  onSelect: () => void;
  onRequestDelete: () => void;
  onConfirmDelete: () => void;
  onCancelDelete: () => void;
}

function SessionRow({
  session,
  active,
  confirming,
  deleting,
  failed,
  onSelect,
  onRequestDelete,
  onConfirmDelete,
  onCancelDelete,
}: SessionRowProps) {
  const deleteBtnRef = useRef<HTMLButtonElement>(null);
  const wasConfirming = useRef(false);

  // When the confirmation closes without deleting, put keyboard focus back on the trash button
  // instead of dropping it to the top of the page.
  useEffect(() => {
    if (wasConfirming.current && !confirming) deleteBtnRef.current?.focus();
    wasConfirming.current = confirming;
  }, [confirming]);

  if (confirming) {
    return (
      <div
        className="session-row confirming"
        role="group"
        aria-label={`Delete ${session.title}`}
        onKeyDown={(e) => {
          if (e.key === "Escape" && !deleting) onCancelDelete();
        }}
      >
        <p className="session-confirm-text">
          Delete <span className="session-confirm-title">{session.title}</span>? This can't be undone.
        </p>
        {failed && (
          <p className="session-confirm-error" role="alert">
            Couldn't delete it. Check your connection and try again.
          </p>
        )}
        <div className="session-confirm-actions">
          <button className="session-confirm-delete" onClick={onConfirmDelete} disabled={deleting}>
            {deleting ? "Deleting…" : "Delete"}
          </button>
          <button className="session-confirm-cancel" onClick={onCancelDelete} disabled={deleting} autoFocus>
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`session-row ${active ? "active" : ""}`}>
      <button
        className="session-item"
        aria-current={active ? "page" : undefined}
        onClick={onSelect}
        title={session.title}
      >
        {session.title}
      </button>
      <button
        ref={deleteBtnRef}
        className="session-delete"
        onClick={onRequestDelete}
        aria-label={`Delete ${session.title}`}
        title="Delete conversation"
      >
        <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true">
          <path
            d="M2.5 4h11M6.5 4V2.5h3V4M4 4l.7 9.1a1 1 0 0 0 1 .9h4.6a1 1 0 0 0 1-.9L12 4M6.8 6.5v5M9.2 6.5v5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </div>
  );
}
