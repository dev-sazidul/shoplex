import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CustomerProductDetail } from "@shoplex/ui/CustomerShopping";

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const site = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

type PageProps = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  try {
    const response = await fetch(`${api}/products/${slug}/`, { next: { revalidate: 300 } });
    if (!response.ok) return { title: "Product not found | SHOPLEX", robots: { index: false, follow: false } };
    const product = await response.json();
    return {
      title: `${product.name} | SHOPLEX`,
      description: product.description.slice(0, 155),
      alternates: { canonical: `${site}/products/${product.slug}` },
      openGraph: { title: `${product.name} | SHOPLEX`, description: product.description.slice(0, 155), images: product.images?.[0]?.image_url ? [product.images[0].image_url] : [] },
    };
  } catch { return { title: "SHOPLEX product", robots: { index: false, follow: false } }; }
}

export default async function ProductPage({ params }: PageProps) {
  const { slug } = await params;
  const response = await fetch(`${api}/products/${slug}/`, { next: { revalidate: 300 } }).catch(() => null);
  if (!response?.ok) notFound();
  const product = await response.json();
  return <CustomerProductDetail slug={slug} initialProduct={product} />;
}
