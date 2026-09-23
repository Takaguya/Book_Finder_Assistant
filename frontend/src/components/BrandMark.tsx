// Three book spines of different heights leaning together on a shelf.
export function BrandMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" className="brand-mark">
      <rect x="3" y="6" width="4.5" height="15" rx="0.8" fill="var(--cloth)" />
      <rect x="8.5" y="3" width="4" height="18" rx="0.8" fill="var(--stamp)" />
      <rect x="14.2" y="7" width="4.2" height="14.6" rx="0.8" fill="var(--brass)" transform="rotate(-12 16.3 21)" />
      <rect x="2" y="21" width="20" height="1.6" rx="0.8" fill="var(--ink)" />
    </svg>
  );
}
