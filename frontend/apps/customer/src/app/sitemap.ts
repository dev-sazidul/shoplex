import type { MetadataRoute } from "next";

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const site = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [{ url: site, changeFrequency: "daily", priority: 1 }, { url: `${site}/products`, changeFrequency: "daily", priority: 0.9 }, { url: `${site}/brands`, changeFrequency: "weekly", priority: 0.6 }];
  try {
    async function allPages(path: string) {
      const rows: Array<{ slug: string; published_at?: string }> = [];
      for (let page = 1; page <= 1000; page += 1) {
        const response = await fetch(`${api}${path}${path.includes("?") ? "&" : "?"}page=${page}`, { next: { revalidate: 3600 } });
        if (!response.ok) break;
        const data = await response.json();
        rows.push(...(data.results ?? data));
        if (!data.next || !data.results) break;
      }
      return rows;
    }
    const [products, categories, brands, storefrontResponse] = await Promise.all([
      allPages("/products/"), allPages("/categories/"), allPages("/brands/"),
      fetch(`${api}/storefront/`, { next: { revalidate: 3600 } }),
    ]);
    for (const product of products) entries.push({ url: `${site}/products/${product.slug}`, ...(product.published_at ? { lastModified: product.published_at } : {}), changeFrequency: "weekly", priority: 0.7 });
    for (const category of categories) entries.push({ url: `${site}/category/${category.slug}`, changeFrequency: "weekly", priority: 0.65 });
    for (const brand of brands) entries.push({ url: `${site}/brand/${brand.slug}`, changeFrequency: "weekly", priority: 0.55 });
    if (storefrontResponse.ok) {
      const storefront = await storefrontResponse.json();
      for (const seller of storefront.featured_sellers ?? []) entries.push({ url: `${site}/stores/${seller.store_slug}`, changeFrequency: "weekly", priority: 0.6 });
    }
  } catch { return entries; }
  return entries;
}
