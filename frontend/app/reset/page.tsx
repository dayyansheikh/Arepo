"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { resetPassword, ApiError } from "@/lib/api";
import {
  AuthShell,
  Field,
  FormMessage,
  SubmitButton,
  TextLink,
} from "@/components/account/AuthUI";

function ResetInner() {
  const token = useSearchParams().get("token");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!token) {
      setError("This reset link is missing its token. Request a new one.");
      return;
    }
    setPending(true);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError("This reset link is invalid or has expired. Request a new one.");
      } else {
        setError(err instanceof Error ? err.message : "Could not reset the password.");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell title="Choose a new password" footer={<TextLink href="/signin">Sign in</TextLink>}>
      {done ? (
        <FormMessage tone="ok">
          Your password has been reset. You can now sign in with your new password.
        </FormMessage>
      ) : (
        <form onSubmit={onSubmit}>
          <FormMessage tone="error">{error}</FormMessage>
          <Field
            label="New password"
            type="password"
            value={password}
            onChange={setPassword}
            required
            autoComplete="new-password"
            hint="Use at least 8 characters."
          />
          <SubmitButton pending={pending}>Set new password</SubmitButton>
        </form>
      )}
    </AuthShell>
  );
}

export default function ResetPage() {
  return (
    <Suspense fallback={null}>
      <ResetInner />
    </Suspense>
  );
}
