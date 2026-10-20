"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { fixtureAllowed } from "./fixture-guard";
import {
  applyLocally,
  loadMembers,
  MEMBERS_SIGNIN_REDIRECT,
  runMemberAction,
  type MemberActionKind,
  type MemberActionResult,
  type MembersSnapshot,
} from "./members";

export interface MembersState {
  data: MembersSnapshot | null;
  loading: boolean;
  error: string | null;
  notFound: boolean;
  /** Set when a security-key unlock is needed (403 hardware_key_required). */
  locked: { keys: number } | null;
  isFixture: boolean;
}

/**
 * Loads members + audit once (and on demand), redirects to sign-in on 401 and reports 404 so the
 * page renders the standard not-found UI. `act` runs one action and refreshes afterwards. In
 * development only, `?fixture=1` swaps in a labelled fixture whose actions never leave the page.
 */
export function useMembers() {
  const router = useRouter();
  const [state, setState] = useState<MembersState>({
    data: null,
    loading: true,
    error: null,
    notFound: false,
    locked: null,
    isFixture: false,
  });
  const fixtureMode = useRef(false);
  const seq = useRef(0);

  const refresh = useCallback(async () => {
    if (fixtureMode.current) return;
    const mine = ++seq.current;
    setState((s) => ({ ...s, loading: true }));
    const result = await loadMembers();
    if (mine !== seq.current) return; // a newer load superseded this one
    if (result.kind === "unauthorized") {
      router.replace(MEMBERS_SIGNIN_REDIRECT);
      return;
    }
    if (result.kind === "locked") {
      setState((s) => ({ ...s, loading: false, locked: { keys: result.keys } }));
      return;
    }
    if (result.kind === "not_found") {
      setState((s) => ({ ...s, loading: false, notFound: true }));
      return;
    }
    if (result.kind === "error") {
      setState((s) => ({ ...s, loading: false, error: result.message }));
      return;
    }
    setState({ data: result.data, loading: false, error: null, notFound: false, locked: null, isFixture: false });
  }, [router]);

  useEffect(() => {
    // Literal NODE_ENV check so the production build drops the fixture branch and chunk entirely;
    // fixtureAllowed() refuses production as a second guard.
    if (process.env.NODE_ENV !== "production") {
      if (fixtureAllowed(process.env.NODE_ENV, window.location.search)) {
        fixtureMode.current = true;
        void import("./members-fixture").then((m) => {
          setState({ data: m.buildMembersFixture(Date.now()), loading: false, error: null, notFound: false, locked: null, isFixture: true });
        });
        return;
      }
    }
    void refresh();
  }, [refresh]);

  const act = useCallback(
    async (kind: MemberActionKind, id: string, confirmEmail = ""): Promise<MemberActionResult> => {
      if (fixtureMode.current) {
        setState((s) => (s.data ? { ...s, data: { ...s.data, users: applyLocally(s.data.users, kind, id) } } : s));
        return { ok: true };
      }
      const res = await runMemberAction(kind, id, confirmEmail);
      if (!res.ok && res.unauthorized) {
        router.replace(MEMBERS_SIGNIN_REDIRECT);
        return res;
      }
      // Refresh after success, and after a conflict / not-found (someone else may have changed it).
      if (res.ok || res.status === 404 || res.status === 409) void refresh();
      return res;
    },
    [refresh, router],
  );

  return { ...state, refresh, act };
}
