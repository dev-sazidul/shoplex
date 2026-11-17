import type { Metadata } from "next";
import { ProductListing } from "@shoplex/ui/CustomerShopping";
const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const site = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
type PageProps = { params: Promise<{ slug: string }> };
export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  return { title: `${slug.replaceAll("-", " ")} store | SHOPLEX`, description: `Shop independent products from ${slug.replaceAll("-", " ")}.`, alternates: { canonical: `${site}/stores/${slug}` } };
}
export default async function StorePage({ params }: PageProps) { const { slug } = await params; const response = await fetch(`${api}/products/?${new URLSearchParams({ seller: slug })}`, { next: { revalidate: 300 } }).catch(() => null); const initialData = response?.ok ? await response.json() : null; return <ProductListing seller={slug} initialData={initialData} />; }
