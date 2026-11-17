import type { Metadata } from "next";
import { SessionProvider } from "@shoplex/ui/SessionProvider";
import "./globals.css";
export const metadata: Metadata = { title: "SHOPLEX Manager | Management", description: "The SHOPLEX manager portal.", robots: { index: false, follow: false } };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><SessionProvider portalRole="manager">{children}</SessionProvider></body></html>; }
