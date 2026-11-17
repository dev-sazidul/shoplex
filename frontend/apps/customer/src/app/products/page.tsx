import { ProductListing } from "@shoplex/ui/CustomerShopping";
export const metadata = { title: "Shop all products | SHOPLEX", description: "Discover products from independent SHOPLEX sellers.", alternates: { canonical: "/products" } };
type PageProps = { searchParams: Promise<{ q?: string }> };
export default async function ProductsPage({ searchParams }: PageProps) {
	const { q = "" } = await searchParams;
	const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
	const response = await fetch(`${api}/products/?${new URLSearchParams({ ...(q ? { q } : {}), sort: "newest" })}`, { next: { revalidate: 120 } }).catch(() => null);
	const initialData = response?.ok ? await response.json() : null;
	return <ProductListing initialQuery={q} initialData={initialData} />;
}
