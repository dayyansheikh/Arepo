"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { verifyEmail } from "@/lib/api";
import { AuthShell, FormMessage, TextLink } from "@/components/account/AuthUI";

function VerifyInner() {
  const params = useSearchParams();
  const token = params.get("token");
  const [state, setState] = useState<"working" | "ok" | "error">("working");

  useEffect(() => {
    if (!token) {
      setState("error");
      return;
    }
    verifyEmail(token)
      .then(() => setState("ok"))
      .catch(() => setState("error"));
  }, [token]);

  return (
    <AuthShell
      title="Email verification"
      footer={<TextLink href="/signin">Go to sign in</TextLink>}
    >
      {state === "working" && (
        <p className="text-[14px] text-arepo-muted">Verifying your email…</p>
      )}
      {state === "ok" && (
        <FormMessage tone="ok">
          Your email is verified. You can now sign in and set up your alerts.
        </FormMessage>
      )}
      {state === "error" && (
        <FormMessage tone="error">
          This verification link is invalid or has expired. Sign in and request a new one, or
          create an account.
        </FormMessage>
      )}
    </AuthShell>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyInner />
    </Suspense>
  );
}
