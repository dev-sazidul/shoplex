import type { Metadata } from "next";
import { SessionProvider } from "@shoplex/ui/SessionProvider";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: "SHOPLEX | One Marketplace. Endless Opportunities.",
  description: "The SHOPLEX marketplace foundation.",
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><SessionProvider portalRole="customer">{children}</SessionProvider></body></html>;
}
