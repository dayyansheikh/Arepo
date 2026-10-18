// The Lab fixture is a local visual-development aid only. It may be shown when, and only when, the
// build is not a production build AND the URL explicitly asks for it with `?fixture=1`. The hook
// additionally wraps the dynamic import in a literal `process.env.NODE_ENV !== "production"` check
// so the production bundle does not even contain the fixture module.

export function fixtureAllowed(nodeEnv: string | undefined, search: string | null | undefined): boolean {
  if (nodeEnv === "production") return false;
  if (!search) return false;
  try {
    return new URLSearchParams(search).get("fixture") === "1";
  } catch {
    return false;
  }
}
