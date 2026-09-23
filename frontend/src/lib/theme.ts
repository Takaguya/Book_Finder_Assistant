import { useState } from "react";

export type ThemeChoice = "light" | "dark" | "system";

// Keep the key and resolution logic in sync with public/theme-init.js, which applies the theme
// before first paint so the page never flashes the wrong colours.
const STORAGE_KEY = "bookfinder-theme";
const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

function readChoice(): ThemeChoice {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // Storage can be blocked (private mode, site-data settings); fall back to the OS setting.
  }
  return "system";
}

function applyTheme(choice: ThemeChoice) {
  const theme = choice === "system" ? (darkQuery.matches ? "dark" : "light") : choice;
  document.documentElement.dataset.theme = theme;
}

// Follow OS light/dark changes while the choice is "system" — registered once at module load
// so it works on every screen, not only while the theme switch is mounted.
darkQuery.addEventListener("change", () => {
  if (readChoice() === "system") applyTheme("system");
});

export function useThemeChoice() {
  const [choice, setChoice] = useState<ThemeChoice>(readChoice);

  function update(next: ThemeChoice) {
    try {
      if (next === "system") localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Not persisted, but still applied for this visit.
    }
    applyTheme(next);
    setChoice(next);
  }

  return [choice, update] as const;
}
