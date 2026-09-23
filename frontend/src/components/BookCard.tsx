import type { BookResult } from "../lib/api";

// Bookcloth colours for books that have no cover image.
const CLOTH = ["#24503F", "#5A3E91", "#7A2E36", "#2D4A6B", "#6B5A2A", "#3E5A4C"];

// Links and images come from Google Books data. Only web URLs are used (never javascript: or
// data:), and Google's http:// links are upgraded so they load on the https site.
function webUrl(url: string | null): string | undefined {
  if (!url) return undefined;
  if (url.startsWith("https://")) return url;
  if (url.startsWith("http://")) return `https://${url.slice("http://".length)}`;
  return undefined;
}

function clothFor(id: string) {
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) | 0;
  return CLOTH[Math.abs(hash) % CLOTH.length];
}

export function BookCard({ book }: { book: BookResult }) {
  const authors = book.authors.join(", ");
  const thumbnail = webUrl(book.thumbnail);
  return (
    <a
      className="book"
      href={webUrl(book.preview_link)}
      target="_blank"
      rel="noreferrer"
      aria-label={`${book.title}${authors ? ` by ${authors}` : ""} (opens Google Books)`}
    >
      <div className="book-cover">
        {thumbnail ? (
          <img src={thumbnail} alt="" loading="lazy" />
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
