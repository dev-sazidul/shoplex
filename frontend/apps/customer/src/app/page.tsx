import { CustomerStorefront } from "@shoplex/ui/CustomerStorefront";

export default async function CustomerHome() {
  const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const response = await fetch(`${api}/storefront/`, { next: { revalidate: 300 } }).catch(() => null);
  const initialData = response?.ok ? await response.json() : null;
  return <CustomerStorefront initialData={initialData} />;
}
