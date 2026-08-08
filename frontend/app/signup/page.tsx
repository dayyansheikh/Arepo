"use client";

import { useState } from "react";
import { registerAccount, ApiError } from "@/lib/api";
import {
  AuthShell,
  Field,
  FormMessage,
  SubmitButton,
  TextLink,
} from "@/components/account/AuthUI";

export default function SignUpPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!consent) {
      setError("Please confirm you accept the terms to create an account.");
      return;
    }
    setPending(true);
    try {
      await registerAccount(email, password);
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError("That email is already registered, or the password is too weak.");
      } else {
        setError(err instanceof Error ? err.message : "Sign up failed.");
      }
    } finally {
      setPending(false);
    }
  }

  if (done) {
    return (
      <AuthShell
        title="Confirm your email"
        lead="Your account has been created."
        footer={
          <>
            Already confirmed? <TextLink href="/signin">Sign in</TextLink>.
          </>
        }
      >
        <FormMessage tone="ok">
          We have sent a verification link to <strong>{email}</strong>. Click it to activate your
          account, then sign in.
        </FormMessage>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Create a free account"
      lead="Create a free account to receive high-priority Arepo research alerts and manage the markets you follow."
      footer={
        <>
          Already have an account? <TextLink href="/signin">Sign in</TextLink>.
        </>
      }
    >
      <form onSubmit={onSubmit}>
        <FormMessage tone="error">{error}</FormMessage>
        <Field
          label="Email"
          type="email"
          value={email}
          onChange={setEmail}
          required
          autoComplete="email"
        />
        <Field
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          required
          autoComplete="new-password"
          hint="Use at least 8 characters."
        />
        <label className="mb-4 flex items-start gap-2 text-[13px] text-arepo-ink2">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="focus-ring mt-0.5"
          />
          <span>
            I understand Arepo provides statistical research signals, not financial advice, and I
            accept the terms.
          </span>
        </label>
        <SubmitButton pending={pending}>Create account</SubmitButton>
      </form>
    </AuthShell>
  );
}
