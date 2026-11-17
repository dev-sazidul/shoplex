import type { Metadata } from "next";
import { SessionProvider } from "@shoplex/ui/SessionProvider";
import "./globals.css";
export const metadata: Metadata = { title: "SHOPLEX Owner | Executive console", description: "The SHOPLEX owner portal.", robots: { index: false, follow: false } };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><SessionProvider portalRole="owner">{children}</SessionProvider></body></html>; }
