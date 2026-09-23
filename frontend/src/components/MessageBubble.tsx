import type { BookResult } from "../lib/api";
import { BookCard } from "./BookCard";

export interface DisplayMessage {
  role: "user" | "model";
  text: string;
  books?: BookResult[];
}

export function MessageBubble({ message }: { message: DisplayMessage }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="message from-user">
        <p className="user-slip">{message.text}</p>
      </div>
    );
  }

  return (
    <div className="message from-model">
      <p className="model-text">{message.text}</p>
      {message.books && message.books.length > 0 && (
        <div className="shelf" role="list" aria-label="Recommended books">
          {message.books.map((book) => (
            <div role="listitem" key={book.id}>
              <BookCard book={book} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
