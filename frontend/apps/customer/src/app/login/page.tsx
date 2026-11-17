import Link from "next/link";
import type { Metadata } from "next";
import { AuthForm } from "@shoplex/ui/AuthForm";

export const metadata: Metadata = { title: "Sign in | SHOPLEX", robots: { index: false, follow: false } };

export default function CustomerLogin() {
  return <main className="auth-page"><section className="auth-aside"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><h2>Find your next favorite thing.</h2><p>One Marketplace. Endless Opportunities.</p></section><section className="auth-main"><div className="auth-column"><AuthForm redirectTo="/account" /><div className="auth-links"><Link href="/register">Create an account</Link><Link href="/password-reset">Forgot password?</Link></div></div></section></main>;
}
