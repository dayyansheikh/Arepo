// Tiny dependency-free module (imported by lib/api.ts and lib/webauthn.ts) describing the API's
// "unlock with your security key first" answer: 403 {"detail": {"code": "hardware_key_required"}}.

export const LOCKED_CODE = "hardware_key_required";
/** Window event fired whenever any API call answers 403 hardware_key_required. */
export const LOCKED_EVENT = "arepo:locked";

export interface LockedDetail {
  code: typeof LOCKED_CODE;
  message: string;
  keys: number;
}

/** The parsed 403 detail when the API says a security-key unlock is needed, else null. */
export function lockedDetail(body: unknown): LockedDetail | null {
  const d = (body as { detail?: unknown } | null)?.detail as Partial<LockedDetail> | undefined;
  if (d && typeof d === "object" && d.code === LOCKED_CODE) {
    return { code: LOCKED_CODE, message: String(d.message ?? ""), keys: Number(d.keys ?? 0) };
  }
  return null;
}

export function announceLocked(detail: LockedDetail): void {
  if (typeof window !== "undefined" && typeof window.dispatchEvent === "function") {
    window.dispatchEvent(new CustomEvent(LOCKED_EVENT, { detail }));
  }
}

