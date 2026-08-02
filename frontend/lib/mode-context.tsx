"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { DataMode } from "./types";

const STORAGE_KEY = "astrolabe:mode";
const VALID_MODES: DataMode[] = ["live", "cached", "replay"];

// The backend defaults to "live", which needs network access to the
// upstream Polymarket APIs. Astrolabe defaults to "replay" so the UI always
// has content to show, even fully offline; users can switch to Live.
const DEFAULT_MODE: DataMode = "replay";

function isDataMode(value: string | null): value is DataMode {
  return value !== null && (VALID_MODES as string[]).includes(value);
}

interface ModeContextValue {
  mode: DataMode;
  setMode: (mode: DataMode) => void;
}

const ModeContext = createContext<ModeContextValue | undefined>(undefined);

export function ModeProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setModeState] = useState<DataMode>(DEFAULT_MODE);
  const [hydrated, setHydrated] = useState(false);

  // Resolve initial mode once on mount: querystring wins, then localStorage,
  // then the app default.
  useEffect(() => {
    const fromQuery = searchParams.get("mode");
    if (isDataMode(fromQuery)) {
      setModeState(fromQuery);
      setHydrated(true);
      return;
    }
    try {
      const fromStorage = window.localStorage.getItem(STORAGE_KEY);
      if (isDataMode(fromStorage)) {
        setModeState(fromStorage);
        setHydrated(true);
        return;
      }
    } catch {
      // localStorage unavailable (private mode, etc.) — ignore
    }
    setHydrated(true);
    // Only run on initial mount; the querystring is otherwise driven by us.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setMode = useCallback(
    (next: DataMode) => {
      setModeState(next);
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // ignore storage errors
      }
      const params = new URLSearchParams(Array.from(searchParams.entries()));
      params.set("mode", next);
      router.replace(`?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  // Keep the URL in sync once hydrated so mode is always visible/shareable.
  useEffect(() => {
    if (!hydrated) return;
    const fromQuery = searchParams.get("mode");
    if (fromQuery !== mode) {
      const params = new URLSearchParams(Array.from(searchParams.entries()));
      params.set("mode", mode);
      router.replace(`?${params.toString()}`, { scroll: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated]);

  const value = useMemo(() => ({ mode, setMode }), [mode, setMode]);

  return <ModeContext.Provider value={value}>{children}</ModeContext.Provider>;
}

export function useMode(): ModeContextValue {
  const ctx = useContext(ModeContext);
  if (!ctx) {
    throw new Error("useMode must be used within a ModeProvider");
  }
  return ctx;
}
