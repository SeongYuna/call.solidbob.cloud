import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactElement,
  type ReactNode,
} from "react";

export type Theme = "dark" | "light";

export const THEME_STORAGE_KEY = "callguard-platform-theme";

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readTheme(fallback: Theme): Theme {
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "light" || stored === "dark") {
    return stored;
  }
  return fallback;
}

function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
}

export function ThemeProvider({
  children,
  fallback = "dark",
}: {
  children: ReactNode;
  fallback?: Theme;
}): ReactElement {
  const [theme, setTheme] = useState<Theme>(fallback);

  useEffect(() => {
    const next = readTheme(fallback);
    setTheme(next);
    applyTheme(next);
  }, [fallback]);

  useEffect(() => {
    function onStorage(event: StorageEvent): void {
      if (event.key !== THEME_STORAGE_KEY) {
        return;
      }
      if (event.newValue === "light" || event.newValue === "dark") {
        setTheme(event.newValue);
        applyTheme(event.newValue);
      }
    }
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next: Theme = current === "dark" ? "light" : "dark";
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
      applyTheme(next);
      return next;
    });
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (value === null) {
    throw new Error("ThemeProvider 안에서만 테마를 쓸 수 있습니다.");
  }
  return value;
}
