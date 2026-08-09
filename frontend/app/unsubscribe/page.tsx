"use client";

import { useEffect, useState } from "react";
import { unsubscribeDigest } from "@/lib/api";
import { PageHeader } from "@/components/ui";
import { TextLink } from "@/components/account/AuthUI";

export default function UnsubscribePage() {
  const [state, setState] = useState<"working" | "done" | "error">("working");

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) {
      setState("error");
      return;
    }
    unsubscribeDigest(token)
      .then(() => setState("done"))
      .catch(() => setState("error"));
  }, []);

  return (
    <div className="mx-auto max-w-md">
      <PageHeader title="Signal digests" />
      <div className="rounded-card border border-arepo-border bg-arepo-surface p-6 text-[14px] text-arepo-ink2">
        {state === "working" && <p>Updating your preference…</p>}
        {state === "done" && (
          <>
            <p>Arepo signal digests are now off.</p>
            <p className="mt-2 text-arepo-muted">
              Your account and security emails are unchanged. You can turn digests back on from{" "}
              <TextLink href="/account?tab=preferences">Preferences</TextLink>.
            </p>
          </>
        )}
        {state === "error" && (
          <p>
            This link could not be used. Sign in and update your{" "}
            <TextLink href="/account?tab=preferences">Preferences</TextLink> instead.
          </p>
        )}
      </div>
    </div>
  );
}
