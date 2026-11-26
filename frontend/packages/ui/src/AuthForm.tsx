"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Button, Card, Notification, StatusPill, TextInput } from "./index";
import { useSession } from "./SessionProvider";

export function AuthForm({
  redirectTo = "/account",
  customerRedirectTo,
}: {
  redirectTo?: string;
  customerRedirectTo?: string;
}) {
  const router = useRouter();
  const { user, login, logout: signOut } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [logoutBusy, setLogoutBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const signedInUser = await login(email, password);
      router.replace(customerRedirectTo && !signedInUser.roles.includes("seller") ? customerRedirectTo : redirectTo);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to reach the authentication service.");
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setLogoutBusy(true);
    setError("");
    try {
      await signOut();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to reach the authentication service.");
    } finally {
      setLogoutBusy(false);
    }
  }

  return (
    <Card className="auth-card">
      {user ? (
        <div className="auth-success">
          <span className="auth-success__mark" aria-hidden="true">
            ✓
          </span>
          <StatusPill tone="success">Session Active</StatusPill>
          <h1 style={{ marginTop: 12 }}>Signed in</h1>
          <p>
            Signed in as <strong>{user.email}</strong>. Tokens remain in this page&apos;s memory and are not written to browser storage.
          </p>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
            <Button onClick={() => router.replace(redirectTo)}>Continue</Button>
            <Button variant="secondary" disabled={logoutBusy} onClick={logout}>
              {logoutBusy ? "Signing out…" : "Sign out"}
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={submit} className="auth-form">
          <p className="eyebrow">SHOPLEX Identity</p>
          <h1>Welcome back</h1>
          <p className="auth-intro">Sign in with your verified SHOPLEX account to access your portal.</p>

          <TextInput
            label="Email address"
            type="email"
            autoComplete="email"
            placeholder="name@company.com"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />

          <div className="auth-password-wrap">
            <TextInput
              label="Password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              placeholder="Enter your password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            <button
              type="button"
              className="auth-password-toggle"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>

          {error && (
            <Notification title="Authentication failed" tone="danger">
              {error}
            </Notification>
          )}

          <Button type="submit" size="lg" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>

          <div className="auth-links">
            <a href="/password-reset">Forgot password?</a>
            <a href="/verify-email">Verify email</a>
          </div>
          <p className="auth-note">
            Protected by Argon2 hashing, JWT refresh-token rotation, and server-side RBAC.
          </p>
        </form>
      )}
    </Card>
  );
}
