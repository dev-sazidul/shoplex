import type { Metadata } from "next";
import { ProductListing } from "@shoplex/ui/CustomerShopping";
const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const site = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
type PageProps = { params: Promise<{ slug: string }> };
export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  return { title: `${slug.replaceAll("-", " ")} | SHOPLEX`, description: `Explore products from ${slug.replaceAll("-", " ")} on SHOPLEX.`, alternates: { canonical: `${site}/brand/${slug}` } };
}
export default async function BrandPage({ params }: PageProps) { const { slug } = await params; const response = await fetch(`${api}/products/?${new URLSearchParams({ brand: slug })}`, { next: { revalidate: 300 } }).catch(() => null); const initialData = response?.ok ? await response.json() : null; return <ProductListing brand={slug} initialData={initialData} />; }
