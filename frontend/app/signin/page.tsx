"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { loginAccount, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import {
  AuthShell,
  Field,
  FormMessage,
  SubmitButton,
  TextLink,
} from "@/components/account/AuthUI";

export default function SignInPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setPending(true);
    try {
      await loginAccount(email, password);
      await refresh();
      router.push("/account");
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError(
          "That email and password did not match, or the email is not yet verified. Check your inbox for the verification link."
        );
      } else {
        setError(err instanceof Error ? err.message : "Sign in failed.");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell
      title="Sign in"
      lead="Sign in to manage your research alerts, preferences and saved markets. The rest of Arepo works without an account."
      footer={
        <>
          New here? <TextLink href="/signup">Create a free account</TextLink>. Forgot your
          password? <TextLink href="/forgot">Reset it</TextLink>.
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
          autoComplete="current-password"
        />
        <SubmitButton pending={pending}>Sign in</SubmitButton>
      </form>
    </AuthShell>
  );
}
