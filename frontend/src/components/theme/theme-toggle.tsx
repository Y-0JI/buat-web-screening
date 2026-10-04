"use client";

import { useTheme } from "./theme-provider";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const toLight = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggle}
      className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-2 transition-colors shrink-0"
      aria-label={toLight ? "Mode terang" : "Mode gelap"}
      title={toLight ? "Mode terang" : "Mode gelap"}
    >
      {toLight ? (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 3v2m0 14v2m9-9h-2M5 12H3m14.5-6.5l-1.5 1.5M7 17l-1.5 1.5m11 0L15 17m-8-10L5.5 5.5M12 8a4 4 0 100 8 4 4 0 000-8z" />
        </svg>
      ) : (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M20.35 14.5A8.5 8.5 0 019.5 3.65a8.5 8.5 0 1010.85 10.85z" />
        </svg>
      )}
    </button>
  );
}
