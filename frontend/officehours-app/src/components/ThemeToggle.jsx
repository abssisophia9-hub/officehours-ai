import { useTheme } from "../theme/ThemeContext.jsx";

export default function ThemeToggle({ className = "" }) {
  const { theme, toggle } = useTheme();
  const dark = theme === "dark";
  const label = dark ? "Switch to light mode" : "Switch to dark mode";

  return (
    <button
      type="button"
      className={`theme-toggle ${className}`.trim()}
      onClick={toggle}
      aria-label={label}
      aria-pressed={dark}
      title={label}
    >
      {dark ? (
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="4.2" />
          <path d="M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4M5.2 5.2l1.7 1.7M17.1 17.1l1.7 1.7M18.8 5.2l-1.7 1.7M6.9 17.1l-1.7 1.7" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M20.6 14.2a8.6 8.6 0 0 1-10.8-10.8 0.55 0.55 0 0 0-0.7-0.68A9.8 9.8 0 1 0 21.3 14.9a0.55 0.55 0 0 0-0.68-0.7z" />
        </svg>
      )}
      <span className="theme-toggle-label">{dark ? "Light" : "Dark"} mode</span>
    </button>
  );
}
