import type { Metadata } from "next";
import { ProductListing } from "@shoplex/ui/CustomerShopping";

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const site = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
type PageProps = { params: Promise<{ slug: string }> };

async function categoryFor(slug: string) {
  const response = await fetch(`${api}/categories/`, { next: { revalidate: 900 } });
  if (!response.ok) return null;
  const data = await response.json();
  return (data.results ?? data).find((item: { slug: string }) => item.slug === slug) ?? null;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const category = await categoryFor(slug);
  const title = category ? `${category.name} | SHOPLEX` : "Category | SHOPLEX";
  const description = category?.description || `Browse ${category?.name ?? "SHOPLEX"} products from verified sellers.`;
  return {
    title,
    description,
    alternates: { canonical: `${site}/category/${slug}` },
    openGraph: { title, description, url: `${site}/category/${slug}`, type: "website" },
  };
}

export default async function CategoryPage({ params }: PageProps) {
  const { slug } = await params;
  const response = await fetch(`${api}/products/?${new URLSearchParams({ category: slug })}`, { next: { revalidate: 300 } }).catch(() => null);
  const initialData = response?.ok ? await response.json() : null;
  return <ProductListing category={slug} initialData={initialData} />;
}
