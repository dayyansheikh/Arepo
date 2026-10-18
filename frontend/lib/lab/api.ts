// Network layer for the owner-only Lab dashboard. Mirrors the account endpoints in lib/api.ts
// (`accountFetch`): the session lives in an HttpOnly cookie, so every request sends
// `credentials: "include"`; there is no CSRF header in the existing account convention, and
// production traffic stays first-party through the Next /api rewrite (API_BASE is "").

import { API_BASE } from "../api";
import type { CommandAction, CommandTarget, LabCommand, LabDashboardResponse } from "./types";

export const SIGNIN_REDIRECT = "/signin?next=/lab";

export type LabLoadResult =
  | { kind: "ok"; data: LabDashboardResponse }
  | { kind: "unauthorized" }
  | { kind: "not_found" }
  | { kind: "error"; message: string; status: number };

export type LabAction =
  | { type: "redirect"; to: string }
  | { type: "not_found" }
  | { type: "data"; data: LabDashboardResponse }
  | { type: "error"; message: string };

/** Pure mapping from a load result to what the page does (unit tested). */
export function actionForResult(result: LabLoadResult): LabAction {
  switch (result.kind) {
    case "unauthorized":
      return { type: "redirect", to: SIGNIN_REDIRECT };
    case "not_found":
      return { type: "not_found" };
    case "ok":
      return { type: "data", data: result.data };
    default:
      return {
        type: "error",
        message:
          result.status === 0 || result.status >= 502
            ? "Can't reach the Arepo API right now. Retrying automatically."
            : result.message,
      };
  }
}

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export const DASHBOARD_PATH = "/api/lab/dashboard";
export const COMMANDS_PATH = "/api/lab/commands";

async function detailOf(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // not JSON
  }
  return res.statusText || `Request failed with status ${res.status}`;
}

export async function loadLabDashboard(
  fetchImpl: FetchLike = (i, init) => fetch(i, init),
  signal?: AbortSignal,
): Promise<LabLoadResult> {
  let res: Response;
  try {
    res = await fetchImpl(`${API_BASE}${DASHBOARD_PATH}`, {
      method: "GET",
      credentials: "include",
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    return { kind: "error", status: 0, message: "Unable to reach the Arepo API." };
  }
  if (res.status === 401) return { kind: "unauthorized" };
  // A signed-in non-owner gets 404 from the API by design: the page does not reveal it exists.
  if (res.status === 404) return { kind: "not_found" };
  if (!res.ok) return { kind: "error", status: res.status, message: await detailOf(res) };
  try {
    const data = (await res.json()) as LabDashboardResponse;
    return { kind: "ok", data: data && typeof data === "object" ? data : {} };
  } catch {
    return { kind: "error", status: res.status, message: "The dashboard response was not valid JSON." };
  }
}

export type CommandPostResult =
  | { ok: true; command: LabCommand | null }
  | { ok: false; status: number; message: string };

export async function postLabCommand(
  target: CommandTarget,
  action: CommandAction,
  fetchImpl: FetchLike = (i, init) => fetch(i, init),
): Promise<CommandPostResult> {
  let res: Response;
  try {
    res = await fetchImpl(`${API_BASE}${COMMANDS_PATH}`, {
      method: "POST",
      credentials: "include",
      cache: "no-store",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ target, action }),
    });
  } catch {
    return { ok: false, status: 0, message: "Unable to reach the Arepo API." };
  }
  if (!res.ok) {
    const message =
      res.status === 429 ? "Too many commands this hour. Try again later." : await detailOf(res);
    return { ok: false, status: res.status, message };
  }
  try {
    return { ok: true, command: (await res.json()) as LabCommand };
  } catch {
    return { ok: true, command: null };
  }
}
