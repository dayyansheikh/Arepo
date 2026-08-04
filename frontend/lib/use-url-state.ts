"use client";

import { useCallback } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

/**
 * Two-way bind a single string value to a URL query parameter, so that browser Back/Forward,
 * refresh and shared links restore the exact state (spec §9). The value lives in the URL, not in
 * component state, so there is a single source of truth and no hydration drift.
 *
 * Setting the value to its default (or "") removes the parameter to keep URLs clean. Updates use
 * `router.replace` with `scroll: false` so filtering does not push history entries or jump the
 * page; deep-linking still works because the initial value is read from the URL on mount.
 */
export function useUrlState(
  key: string,
  defaultValue = "",
): [string, (value: string) => void] {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const value = params.get(key) ?? defaultValue;

  const set = useCallback(
    (next: string) => {
      const sp = new URLSearchParams(params.toString());
      if (next === defaultValue || next === "") sp.delete(key);
      else sp.set(key, next);
      const qs = sp.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [params, router, pathname, key, defaultValue],
  );

  return [value, set];
}
