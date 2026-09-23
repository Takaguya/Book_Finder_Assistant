import type { ReactNode } from "react";
import { useThemeChoice, type ThemeChoice } from "../lib/theme";

const OPTIONS: { value: ThemeChoice; label: string; icon: ReactNode }[] = [
  {
    value: "light",
    label: "Light",
    icon: (
      <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
        <circle cx="8" cy="8" r="3" fill="currentColor" />
        <path
          d="M8 1v1.6M8 13.4V15M1 8h1.6M13.4 8H15M3.05 3.05l1.13 1.13M11.82 11.82l1.13 1.13M3.05 12.95l1.13-1.13M11.82 4.18l1.13-1.13"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
  {
    value: "dark",
    label: "Dark",
    icon: (
      <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
        <path d="M13.5 10.2A5.8 5.8 0 0 1 5.8 2.5a5.8 5.8 0 1 0 7.7 7.7z" fill="currentColor" />
      </svg>
    ),
  },
  {
    value: "system",
    label: "System",
    icon: (
      <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
        <rect x="1.5" y="2.5" width="13" height="8.5" rx="1.2" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <path d="M5.5 14h5M8 11v3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    ),
  },
];

export function ThemeSwitch() {
  const [choice, setChoice] = useThemeChoice();

  return (
    <fieldset className="theme-switch">
      <legend className="visually-hidden">Colour theme</legend>
      {OPTIONS.map((o) => (
        <label key={o.value} className={`theme-option ${choice === o.value ? "checked" : ""}`}>
          <input
            type="radio"
            name="theme"
            value={o.value}
            checked={choice === o.value}
            onChange={() => setChoice(o.value)}
          />
          {o.icon}
          <span>{o.label}</span>
        </label>
      ))}
    </fieldset>
  );
}
