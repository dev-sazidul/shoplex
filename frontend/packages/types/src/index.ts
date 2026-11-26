export type PortalRole = "customer" | "seller" | "admin" | "manager" | "owner";

export interface ApiHealth {
  status: "ok" | "error";
  service: string;
  api_version: string;
}

export interface ApiError {
  detail?: string;
  [field: string]: unknown;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface AuthenticatedUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  status: string;
  roles: PortalRole[];
}

export interface ProductImage {
  id: number;
  image_url: string;
  alt_text: string;
  sort_order: number;
}

export interface ProductSummary {
  id: string;
  name: string;
  slug: string;
  description: string;
  sku?: string;
  price: string;
  compare_at_price: string | null;
  attributes: Record<string, unknown>;
  category: { name: string; slug: string };
  brand: { name: string; slug: string } | null;
  seller: { business_name: string; store_slug: string; store_description: string };
  images: ProductImage[];
  average_rating: number | null;
  review_count: number;
  in_stock: boolean;
  variants: Array<{ id: string; name: string; sku?: string; options: Record<string, string>; price: string | null; stock_quantity: number }>;
}
