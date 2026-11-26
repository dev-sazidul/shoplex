"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Button, Card, TextInput } from "./index";
import { useSession } from "./SessionProvider";

export function AuthForm({ redirectTo = "/account", customerRedirectTo }: { redirectTo?: string; customerRedirectTo?: string }) {
  const router = useRouter();
  const { user, login, logout: signOut } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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

  return <Card className="auth-card">
    {user ? <div className="auth-success"><span className="auth-success__mark" aria-hidden="true">✓</span><h1>Signed in</h1><p>Your session is active. Tokens remain in this page's memory and are not written to browser storage.</p>{error && <p className="form-error" role="alert">{error}</p>}<Button variant="secondary" disabled={logoutBusy} onClick={logout}>{logoutBusy ? "Signing out…" : "Sign out"}</Button></div> : <form onSubmit={submit} className="auth-form">
      <p className="eyebrow">SHOPLEX account</p><h1>Welcome back</h1><p className="auth-intro">Use your verified account to continue.</p>
      <TextInput label="Email address" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
      <TextInput label="Password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} />
      {error && <p className="form-error" role="alert">{error}</p>}
      <Button type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button>
      <p className="auth-note">Email verification and password recovery are available through the central API.</p>
    </form>}
  </Card>;
}
