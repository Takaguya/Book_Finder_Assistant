import Markdown, { type Components } from "react-markdown";
import type { BookResult } from "../lib/api";
import { BookCard } from "./BookCard";

export interface DisplayMessage {
  role: "user" | "model";
  text: string;
  books?: BookResult[];
}

// The assistant writes light Markdown (**bold** titles, bullet lists). react-markdown turns it
// into React elements, never raw HTML, so text from book descriptions can't inject markup.
// Only these elements are kept; anything else (images, tables…) is dropped or reduced to its text.
const ALLOWED_ELEMENTS = [
  "p", "strong", "em", "ul", "ol", "li", "a", "br", "code", "blockquote", "hr",
  "h1", "h2", "h3", "h4", "h5", "h6",
];

function Heading({ children }: { children?: React.ReactNode }) {
  // Headings inside a reply shouldn't compete with the page's own; show them as a bold lead-in.
  return <p className="model-heading">{children}</p>;
}

const COMPONENTS: Components = {
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  ),
  h1: Heading,
  h2: Heading,
  h3: Heading,
  h4: Heading,
  h5: Heading,
  h6: Heading,
};

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
      <div className="model-text">
        <Markdown allowedElements={ALLOWED_ELEMENTS} unwrapDisallowed components={COMPONENTS}>
          {message.text}
        </Markdown>
      </div>
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
