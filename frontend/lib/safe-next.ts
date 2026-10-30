/**
 * Post-sign-in destination from a `?next=` parameter. Only same-site absolute paths are accepted
 * ("/lab"), never protocol-relative ("//evil.com"), backslash tricks or full URLs, so the sign-in
 * page cannot be used as an open redirect. Anything else falls back to the account page.
 */
export function safeNextPath(next: string | null | undefined, fallback = "/account"): string {
  if (!next) return fallback;
  if (!next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return fallback;
  if (/[\u0000-\u001f\\]/.test(next)) return fallback;
  return next;
}
