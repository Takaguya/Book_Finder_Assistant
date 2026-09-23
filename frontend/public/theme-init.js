// Apply the saved light/dark choice before first paint (see src/lib/theme.ts).
// Kept as a file rather than an inline <script> so the Content Security Policy can forbid
// inline scripts entirely.
(function () {
  var stored;
  try {
    stored = localStorage.getItem("bookfinder-theme");
  } catch {
    // Storage blocked: fall back to the OS setting.
  }
  var dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme =
    stored === "light" || stored === "dark" ? stored : dark ? "dark" : "light";
})();
