// Pure URL query-state helpers (spec §10). Filters live in the URL, so Back/Forward/refresh and
// shared links restore them. These are the pure serialization functions; `useUrlState` binds them
// to the router. Keeping them pure lets the restoration/navigation logic be unit-tested.

/** Read a param from a query string, falling back to a default. */
export function readParam(search: string, key: string, dflt = ""): string {
  return new URLSearchParams(search).get(key) ?? dflt;
}

/**
 * Return the next query string after setting `key` to `value`. Setting a value equal to its
 * default (or empty) removes the key, so default filters keep URLs clean. Other keys are
 * preserved unchanged, so independent filters do not clobber each other.
 */
export function nextSearch(search: string, key: string, value: string, dflt = ""): string {
  const sp = new URLSearchParams(search);
  if (value === dflt || value === "") sp.delete(key);
  else sp.set(key, value);
  return sp.toString();
}

/** Apply several (key, value, default) updates in order (e.g. clearing all filters). */
export function applyParams(
  search: string,
  updates: Array<[key: string, value: string, dflt?: string]>,
): string {
  return updates.reduce(
    (acc, [key, value, dflt = ""]) => nextSearch(acc, key, value, dflt),
    search,
  );
}
