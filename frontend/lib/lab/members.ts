// Lab > Members: types, network layer and pure helpers for the owner-only member admin page.
// Same conventions as lib/lab/api.ts: HttpOnly session cookie (`credentials: "include"`), JSON
// bodies, 401 -> sign-in with ?next=, 404 -> the page renders the standard not-found UI.

import { API_BASE } from "../api";

export const MEMBERS_PATH = "/lab/members";
export const MEMBERS_SIGNIN_REDIRECT = `/signin?next=${MEMBERS_PATH}`;
export const ADMIN_BASE = "/api/lab/admin";

export interface MemberData {
  alert_preferences?: number;
  saved_markets?: number;
  alert_deliveries?: number;
  digest_deliveries?: number;
}

export interface Member {
  id: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
  created_at?: string | null;
  data?: MemberData;
}

export interface AuditEntry {
  id: number;
  at: string | null;
  actor_user_id: string;
  actor_email: string;
  action: string;
  target_user_id: string | null;
  target_email: string | null;
  detail: string | null;
}

export interface MembersSnapshot {
  users: Member[];
  me: string | null;
  audit: AuditEntry[];
}

export type MembersLoadResult =
  | { kind: "ok"; data: MembersSnapshot }
  | { kind: "unauthorized" }
  | { kind: "not_found" }
  | { kind: "error"; status: number; message: string };

export type MemberActionKind =
  | "password_reset"
  | "verification_email"
  | "verify"
  | "suspend"
  | "restore"
  | "admin_grant"
  | "admin_revoke"
  | "delete";

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;
const defaultFetch: FetchLike = (i, init) => fetch(i, init);

async function detailOf(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // not JSON
  }
  return res.statusText || `Request failed with status ${res.status}`;
}

function unreachable(status: number, message: string): string {
  return status === 0 || status >= 502 ? "Can't reach the Arepo API right now. Try again in a moment." : message;
}

async function getJson(path: string, fetchImpl: FetchLike): Promise<Response | null> {
  try {
    return await fetchImpl(`${API_BASE}${path}`, {
      method: "GET",
      credentials: "include",
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
  } catch {
    return null;
  }
}

/** Loads the member list and the recent audit log together. */
export async function loadMembers(fetchImpl: FetchLike = defaultFetch): Promise<MembersLoadResult> {
  const [usersRes, auditRes] = await Promise.all([
    getJson(`${ADMIN_BASE}/users`, fetchImpl),
    getJson(`${ADMIN_BASE}/audit`, fetchImpl),
  ]);
  if (!usersRes || !auditRes) return { kind: "error", status: 0, message: unreachable(0, "") };
  for (const res of [usersRes, auditRes]) {
    if (res.status === 401) return { kind: "unauthorized" };
  }
  for (const res of [usersRes, auditRes]) {
    // A signed-in non-owner gets 404 by design: the area must not reveal that it exists.
    if (res.status === 404) return { kind: "not_found" };
  }
  for (const res of [usersRes, auditRes]) {
    if (!res.ok) return { kind: "error", status: res.status, message: unreachable(res.status, await detailOf(res)) };
  }
  try {
    const u = (await usersRes.json()) as { users?: Member[]; me?: string };
    const a = (await auditRes.json()) as { entries?: AuditEntry[] };
    return {
      kind: "ok",
      data: {
        users: Array.isArray(u?.users) ? u.users : [],
        me: typeof u?.me === "string" ? u.me : null,
        audit: Array.isArray(a?.entries) ? a.entries : [],
      },
    };
  } catch {
    return { kind: "error", status: 200, message: "The members response was not valid JSON." };
  }
}

/** The HTTP request each action maps to (pure; unit tested). */
export function requestFor(
  kind: MemberActionKind,
  id: string,
  confirmEmail = "",
): { method: "POST" | "DELETE"; path: string; body?: Record<string, unknown> } {
  const base = `${ADMIN_BASE}/users/${encodeURIComponent(id)}`;
  switch (kind) {
    case "password_reset":
      return { method: "POST", path: `${base}/password-reset` };
    case "verification_email":
      return { method: "POST", path: `${base}/verification-email` };
    case "verify":
      return { method: "POST", path: `${base}/verify` };
    case "suspend":
      return { method: "POST", path: `${base}/suspend` };
    case "restore":
      return { method: "POST", path: `${base}/restore` };
    case "admin_grant":
      return { method: "POST", path: `${base}/admin`, body: { grant: true, confirm_email: confirmEmail } };
    case "admin_revoke":
      return { method: "POST", path: `${base}/admin`, body: { grant: false, confirm_email: confirmEmail } };
    case "delete":
      return { method: "DELETE", path: base, body: { confirm_email: confirmEmail } };
  }
}

export type MemberActionResult =
  | { ok: true }
  | { ok: false; status: number; message: string; unauthorized?: boolean };

export async function runMemberAction(
  kind: MemberActionKind,
  id: string,
  confirmEmail = "",
  fetchImpl: FetchLike = defaultFetch,
): Promise<MemberActionResult> {
  const req = requestFor(kind, id, confirmEmail);
  let res: Response;
  try {
    res = await fetchImpl(`${API_BASE}${req.path}`, {
      method: req.method,
      credentials: "include",
      cache: "no-store",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: req.body ? JSON.stringify(req.body) : undefined,
    });
  } catch {
    return { ok: false, status: 0, message: unreachable(0, "") };
  }
  if (res.ok) return { ok: true };
  if (res.status === 401) {
    return { ok: false, status: 401, message: "Your session has ended. Sign in again.", unauthorized: true };
  }
  if (res.status === 429) {
    return { ok: false, status: 429, message: await detailOf(res) };
  }
  if (res.status === 422) {
    const detail = await detailOf(res);
    return {
      ok: false,
      status: 422,
      message: detail.startsWith("The confirmation email") ? detail : "That request wasn't valid. Check the email and try again.",
    };
  }
  return { ok: false, status: res.status, message: unreachable(res.status, await detailOf(res)) };
}

// ---- pure helpers ------------------------------------------------------------------------------

/** Actions the page offers for a member; mirrors the API guards so refused actions are not shown. */
export function availableActions(m: Member, meId: string | null): MemberActionKind[] {
  const self = meId !== null && m.id === meId;
  const out: MemberActionKind[] = [];
  if (m.is_active) out.push("password_reset");
  if (!m.is_verified && m.is_active) out.push("verification_email");
  if (!m.is_verified) out.push("verify");
  if (m.is_superuser) {
    if (!self) out.push("admin_revoke");
  } else if (m.is_active && m.is_verified) {
    out.push("admin_grant");
  }
  if (!m.is_active) out.push("restore");
  else if (!self && !m.is_superuser) out.push("suspend");
  if (!self && !m.is_superuser) out.push("delete");
  return out;
}

export interface ActionCopy {
  label: string;
  title: (m: Member) => string;
  body: string;
  confirm: string;
  /** Requires typing the member's email to confirm. */
  typed: boolean;
  danger: boolean;
  done: (m: Member) => string;
}

export const ACTION_COPY: Record<MemberActionKind, ActionCopy> = {
  password_reset: {
    label: "Send password reset",
    title: (m) => `Send a password reset to ${m.email}?`,
    body: "They get the normal Arepo reset email and choose a new password themselves. You never see or set it.",
    confirm: "Send reset email",
    typed: false,
    danger: false,
    done: (m) => `Password reset email sent to ${m.email}.`,
  },
  verification_email: {
    label: "Resend verification email",
    title: (m) => `Resend the verification email to ${m.email}?`,
    body: "They get the normal Arepo verification email with a fresh link.",
    confirm: "Resend email",
    typed: false,
    danger: false,
    done: (m) => `Verification email sent to ${m.email}.`,
  },
  verify: {
    label: "Mark as verified",
    title: (m) => `Mark ${m.email} as verified?`,
    body: "Only do this if you know the address belongs to them. They will be able to sign in straight away.",
    confirm: "Mark verified",
    typed: false,
    danger: false,
    done: (m) => `${m.email} is now verified.`,
  },
  suspend: {
    label: "Suspend",
    title: (m) => `Suspend ${m.email}?`,
    body: "They can't use their account, and their alerts and digests stop, until you restore it. Nothing is deleted.",
    confirm: "Suspend account",
    typed: false,
    danger: true,
    done: (m) => `${m.email} is suspended.`,
  },
  restore: {
    label: "Restore",
    title: (m) => `Restore ${m.email}?`,
    body: "They can sign in again and their saved settings come back as they were.",
    confirm: "Restore account",
    typed: false,
    danger: false,
    done: (m) => `${m.email} is active again.`,
  },
  admin_grant: {
    label: "Make admin",
    title: (m) => `Make ${m.email} an admin?`,
    body: "Admins can open the Lab, pause the research machines and manage every member, including you.",
    confirm: "Make admin",
    typed: true,
    danger: true,
    done: (m) => `${m.email} is now an admin.`,
  },
  admin_revoke: {
    label: "Revoke admin",
    title: (m) => `Revoke admin access for ${m.email}?`,
    body: "They keep their account but lose access to the Lab and member management.",
    confirm: "Revoke admin",
    typed: true,
    danger: true,
    done: (m) => `${m.email} is no longer an admin.`,
  },
  delete: {
    label: "Delete account",
    title: (m) => `Permanently delete ${m.email}?`,
    body: "This removes the account and all of their saved markets, alert settings, alert history and digests. It can't be undone.",
    confirm: "Delete permanently",
    typed: true,
    danger: true,
    done: (m) => `${m.email} was deleted.`,
  },
};

export function emailMatches(typed: string, email: string): boolean {
  return typed.trim().toLowerCase() === email.trim().toLowerCase() && typed.trim() !== "";
}

export type MemberFilter = "all" | "admins" | "unverified" | "suspended";

export function matchesFilter(m: Member, f: MemberFilter): boolean {
  switch (f) {
    case "admins":
      return m.is_superuser;
    case "unverified":
      return !m.is_verified;
    case "suspended":
      return !m.is_active;
    default:
      return true;
  }
}

export function displayName(m: Member): string {
  return [m.first_name, m.last_name].filter((s) => typeof s === "string" && s.trim()).join(" ").trim();
}

export function filterMembers(members: Member[], query: string, f: MemberFilter): Member[] {
  const q = query.trim().toLowerCase();
  return members.filter((m) => {
    if (!matchesFilter(m, f)) return false;
    if (!q) return true;
    return m.email.toLowerCase().includes(q) || displayName(m).toLowerCase().includes(q);
  });
}

export function filterCounts(members: Member[]): Record<MemberFilter, number> {
  const out: Record<MemberFilter, number> = { all: 0, admins: 0, unverified: 0, suspended: 0 };
  for (const m of members) {
    for (const f of Object.keys(out) as MemberFilter[]) if (matchesFilter(m, f)) out[f] += 1;
  }
  return out;
}

/** Short plain-English summary of a member's saved data, e.g. "3 saved markets · alerts set up". */
export function dataSummary(d: MemberData | undefined): string {
  if (!d) return "No saved data";
  const parts: string[] = [];
  const n = (v: number | undefined) => (typeof v === "number" && v > 0 ? v : 0);
  if (n(d.saved_markets)) parts.push(`${n(d.saved_markets)} saved market${n(d.saved_markets) === 1 ? "" : "s"}`);
  if (n(d.alert_preferences)) parts.push("alert settings");
  if (n(d.alert_deliveries)) parts.push(`${n(d.alert_deliveries)} alert${n(d.alert_deliveries) === 1 ? "" : "s"}`);
  if (n(d.digest_deliveries)) parts.push(`${n(d.digest_deliveries)} digest${n(d.digest_deliveries) === 1 ? "" : "s"}`);
  return parts.length ? parts.join(" · ") : "No saved data";
}

const AUDIT_VERBS: Record<string, string> = {
  password_reset: "sent a password reset to",
  verification_email: "resent the verification email to",
  verify: "marked as verified",
  suspend: "suspended",
  restore: "restored",
  admin_grant: "made admin",
  admin_revoke: "revoked admin for",
  delete: "deleted",
};

export function auditSentence(e: AuditEntry): string {
  const verb = AUDIT_VERBS[e.action] ?? e.action.replace(/_/g, " ");
  return `${e.actor_email} ${verb} ${e.target_email ?? "a member"}`;
}

/** Applies a successful action to a local copy (used by the dev fixture, which never sends). */
export function applyLocally(members: Member[], kind: MemberActionKind, id: string): Member[] {
  if (kind === "delete") return members.filter((m) => m.id !== id);
  return members.map((m) => {
    if (m.id !== id) return m;
    switch (kind) {
      case "verify":
        return { ...m, is_verified: true };
      case "suspend":
        return { ...m, is_active: false };
      case "restore":
        return { ...m, is_active: true };
      case "admin_grant":
        return { ...m, is_superuser: true };
      case "admin_revoke":
        return { ...m, is_superuser: false };
      default:
        return m;
    }
  });
}
