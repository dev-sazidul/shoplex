import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const site = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/account/", "/login", "/register", "/password-reset", "/verify-email", "/cart", "/checkout", "/orders/"] },
    sitemap: `${site}/sitemap.xml`,
  };
}
