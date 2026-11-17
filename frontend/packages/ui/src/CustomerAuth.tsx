"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Card, TextInput } from "./index";

const apiBase = () => process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

function AuthShell({ children, title }: { children: React.ReactNode; title: string }) {
  return <main className="simple-form-page"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><Card className="auth-card"><p className="eyebrow">SHOPLEX account</p><h1>{title}</h1>{children}</Card></main>;
}

export function CustomerRegistrationForm() {
  const [values, setValues] = useState({ first_name: "", last_name: "", email: "", phone_number: "", password: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setMessage(""); setError("");
    try {
      const response = await fetch(`${apiBase()}/auth/register/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? Object.values(data).flat().join(" ") ?? "Registration could not be completed.");
      setMessage("Account created. Verify your email before signing in.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to reach SHOPLEX."); }
    finally { setBusy(false); }
  }
  return <AuthShell title="Create your account"><form className="auth-form" onSubmit={submit}>
    <TextInput label="First name" autoComplete="given-name" required value={values.first_name} onChange={(e) => setValues({ ...values, first_name: e.target.value })} />
    <TextInput label="Last name" autoComplete="family-name" value={values.last_name} onChange={(e) => setValues({ ...values, last_name: e.target.value })} />
    <TextInput label="Email address" type="email" autoComplete="email" required value={values.email} onChange={(e) => setValues({ ...values, email: e.target.value })} />
    <TextInput label="Phone number" type="tel" autoComplete="tel" value={values.phone_number} onChange={(e) => setValues({ ...values, phone_number: e.target.value })} />
    <TextInput label="Password" type="password" autoComplete="new-password" minLength={12} required value={values.password} onChange={(e) => setValues({ ...values, password: e.target.value })} />
    {error && <p className="form-error" role="alert">{error}</p>}{message && <p className="form-success" role="status">{message}</p>}
    <Button type="submit" disabled={busy}>{busy ? "Creating account…" : "Create account"}</Button>
    <p className="auth-note">By continuing, you agree to the SHOPLEX terms and privacy policy.</p>
  </form></AuthShell>;
}

export function EmailVerificationForm() {
  const [token, setToken] = useState(""); const [message, setMessage] = useState(""); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setMessage("");
    const response = await fetch(`${apiBase()}/auth/verify-email/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) });
    const result = await response.json();
    if (response.ok) setMessage(result.detail); else setError(result.detail ?? "Verification failed.");
  }
  return <AuthShell title="Verify your email"><form className="auth-form" onSubmit={submit}><TextInput label="Verification token" required value={token} onChange={(e) => setToken(e.target.value)} /><p className="auth-note">Enter the token from your verification email. In local development, email content is printed by Django.</p>{error && <p className="form-error" role="alert">{error}</p>}{message && <p className="form-success" role="status">{message}</p>}<Button type="submit">Verify email</Button></form></AuthShell>;
}

export function PasswordRecoveryForm() {
  const [email, setEmail] = useState(""); const [message, setMessage] = useState(""); const [error, setError] = useState("");
  const [uid, setUid] = useState(""); const [token, setToken] = useState(""); const [password, setPassword] = useState("");
  async function requestReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setMessage("");
    const response = await fetch(`${apiBase()}/auth/password-reset/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) });
    const result = await response.json();
    if (response.ok) setMessage(result.detail); else setError(result.detail ?? "Request could not be completed.");
  }
  async function confirmReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setMessage("");
    const response = await fetch(`${apiBase()}/auth/password-reset/confirm/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ uid, token, new_password: password }) });
    const result = await response.json();
    if (response.ok) setMessage(result.detail); else setError(result.detail ?? Object.values(result).flat().join(" ") ?? "Password reset failed.");
  }
  return <AuthShell title="Account recovery"><form className="auth-form" onSubmit={requestReset}><h2>Request a reset</h2><TextInput label="Account email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /><Button type="submit" variant="secondary">Send reset instructions</Button></form><form className="auth-form recovery-confirm" onSubmit={confirmReset}><h2>Choose a new password</h2><TextInput label="Account ID from email" required value={uid} onChange={(e) => setUid(e.target.value)} /><TextInput label="Reset token" required value={token} onChange={(e) => setToken(e.target.value)} /><TextInput label="New password" type="password" minLength={12} required value={password} onChange={(e) => setPassword(e.target.value)} /><Button type="submit">Reset password</Button></form>{error && <p className="form-error" role="alert">{error}</p>}{message && <p className="form-success" role="status">{message}</p>}</AuthShell>;
}
