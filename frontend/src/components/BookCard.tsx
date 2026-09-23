import type { BookResult } from "../lib/api";

// Bookcloth colours for books that have no cover image.
const CLOTH = ["#24503F", "#5A3E91", "#7A2E36", "#2D4A6B", "#6B5A2A", "#3E5A4C"];

function clothFor(id: string) {
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) | 0;
  return CLOTH[Math.abs(hash) % CLOTH.length];
}

export function BookCard({ book }: { book: BookResult }) {
  const authors = book.authors.join(", ");
  return (
    <a
      className="book"
      href={book.preview_link ?? undefined}
      target="_blank"
      rel="noreferrer"
      aria-label={`${book.title}${authors ? ` by ${authors}` : ""} (opens Google Books)`}
    >
      <div className="book-cover">
        {book.thumbnail ? (
          <img src={book.thumbnail} alt="" loading="lazy" />
        ) : (
          <div className="book-cover-cloth" style={{ background: clothFor(book.id) }}>
            <span className="book-cover-cloth-title">{book.title}</span>
            {authors && <span className="book-cover-cloth-author">{book.authors[0]}</span>}
          </div>
        )}
      </div>
      <div className="book-label">
        <span className="book-title">{book.title}</span>
        {authors && <span className="book-authors">{authors}</span>}
        {book.average_rating != null && (
          <span className="book-rating" aria-label={`Rated ${book.average_rating.toFixed(1)} out of 5`}>
            ★ {book.average_rating.toFixed(1)}
          </span>
        )}
      </div>
    </a>
  );
}
