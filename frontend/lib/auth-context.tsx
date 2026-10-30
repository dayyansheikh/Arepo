"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { AccountUser } from "./types";
import { ApiError, getMe, logoutAccount } from "./api";
import { LOCKED_EVENT, type LockedDetail } from "./stepup-events";

interface AuthContextValue {
  user: AccountUser | null;
  /**
   * Set when the session is valid but the account has a security key and this browser has not
   * been unlocked with it yet (API 403 hardware_key_required). Pages show the unlock screen.
   */
  locked: LockedDetail | null;
  loading: boolean;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Tracks the signed-in user by asking the API who the current cookie belongs to. A 401 simply
 * means "not signed in", which is a normal state (the public site works without an account), so
 * it is never surfaced as an error.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AccountUser | null>(null);
  const [locked, setLocked] = useState<LockedDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const me = await getMe();
      setUser(me);
      setLocked(null);
    } catch (err) {
      setUser(null);
      setLocked(err instanceof ApiError && err.locked ? err.locked : null);
    } finally {
      setLoading(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    try {
      await logoutAccount();
    } finally {
      setUser(null);
      setLocked(null);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Any account call that answers 403 hardware_key_required (e.g. after the unlock expires)
  // flips the whole site to the locked state.
  useEffect(() => {
    const onLocked = (e: Event) => {
      const detail = (e as CustomEvent<LockedDetail>).detail;
      setUser(null);
      setLocked(detail ?? { code: "hardware_key_required", message: "", keys: 1 });
    };
    window.addEventListener(LOCKED_EVENT, onLocked);
    return () => window.removeEventListener(LOCKED_EVENT, onLocked);
  }, []);

  const value = useMemo(
    () => ({ user, locked, loading, refresh, signOut }),
    [user, locked, loading, refresh, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
