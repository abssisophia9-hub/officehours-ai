import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const STORAGE_KEY = "officehours_theme";
const ThemeContext = createContext(null);

function systemTheme() {
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function storedTheme() {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    return null;
  }
}

function applyTheme(theme, { animate = false } = {}) {
  const root = document.documentElement;
  if (animate) {
    root.classList.add("theme-anim");
    window.setTimeout(() => root.classList.remove("theme-anim"), 350);
  }
  root.setAttribute("data-theme", theme);
}

export function ThemeProvider({ children }) {
  // `choice` is the user's explicit pick; null means "follow the system".
  const [choice, setChoice] = useState(storedTheme);
  const [system, setSystem] = useState(systemTheme);
  const theme = choice ?? system;

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    if (!window.matchMedia) return undefined;
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (event) => setSystem(event.matches ? "dark" : "light");
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  const setTheme = useCallback((next) => {
    setChoice(next);
    try {
      if (next === null) localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Private browsing - theme still applies for this session.
    }
    applyTheme(next ?? systemTheme(), { animate: true });
  }, []);

  const toggle = useCallback(() => {
    setTheme(theme === "dark" ? "light" : "dark");
  }, [theme, setTheme]);

  const value = useMemo(
    () => ({ theme, source: choice ? "user" : "system", setTheme, toggle }),
    [theme, choice, setTheme, toggle],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used inside ThemeProvider");
  return context;
}
