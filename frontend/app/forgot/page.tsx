"use client";

import { useState } from "react";
import { forgotPassword } from "@/lib/api";
import {
  AuthShell,
  Field,
  FormMessage,
  SubmitButton,
  TextLink,
} from "@/components/account/AuthUI";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    try {
      // fastapi-users always returns success here, so we never reveal whether an email exists.
      await forgotPassword(email);
    } catch {
      // Deliberately ignored: do not leak whether the address is registered.
    } finally {
      setDone(true);
      setPending(false);
    }
  }

  return (
    <AuthShell
      title="Reset your password"
      lead="Enter your email and we will send a link to choose a new password."
      footer={<TextLink href="/signin">Back to sign in</TextLink>}
    >
      {done ? (
        <FormMessage tone="ok">
          If an account exists for <strong>{email}</strong>, a reset link has been sent. In local
          development the link is printed to the backend server log.
        </FormMessage>
      ) : (
        <form onSubmit={onSubmit}>
          <Field
            label="Email"
            type="email"
            value={email}
            onChange={setEmail}
            required
            autoComplete="email"
          />
          <SubmitButton pending={pending}>Send reset link</SubmitButton>
        </form>
      )}
    </AuthShell>
  );
}
