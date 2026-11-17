"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { ProductSummary } from "@shoplex/types";
import { Button, EmptyState, LoadingState, StatusPill, TextInput } from "./index";
import { ProductCard } from "./CustomerStorefront";
import { useSession } from "./SessionProvider";

const apiBase = () => process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const money = (value: string) => `৳${Number(value).toLocaleString("en-BD", { minimumFractionDigits: 2 })}`;

interface ProductPageData { count: number; results: ProductSummary[] }

export function ProductListing({ category = "", brand = "", seller = "", initialQuery = "", initialData = null }: { category?: string; brand?: string; seller?: string; initialQuery?: string; initialData?: ProductPageData | null }) {
  const router = useRouter();
  const { user, apiFetch } = useSession();
  const [products, setProducts] = useState<ProductSummary[]>(initialData?.results ?? []);
  const [categories, setCategories] = useState<Array<{ name: string; slug: string }>>([]);
  const [query, setQuery] = useState(initialQuery);
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [sort, setSort] = useState("newest");
  const [inStock, setInStock] = useState(false);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(initialData?.count ?? 0);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const title = useMemo(() => category ? category.replaceAll("-", " ") : brand ? brand.replaceAll("-", " ") : seller ? "Store products" : query ? `Search: ${query}` : "All products", [category, brand, seller, query]);
  const skipFirstFetch = useRef(Boolean(initialData));

  useEffect(() => {
    const base = apiBase();
    fetch(`${base}/categories/`).then((response) => response.ok ? response.json() : []).then((data) => setCategories(data.results ?? data)).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (skipFirstFetch.current) { skipFirstFetch.current = false; return; }
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (brand) params.set("brand", brand);
    if (seller) params.set("seller", seller);
    if (query.trim()) params.set("q", query.trim());
    if (minPrice) params.set("min_price", minPrice);
    if (maxPrice) params.set("max_price", maxPrice);
    if (inStock) params.set("in_stock", "true");
    params.set("sort", sort); params.set("page", String(page));
    setLoading(true); setError("");
    fetch(`${apiBase()}/products/?${params.toString()}`)
      .then(async (response) => { if (!response.ok) throw new Error("Products could not be loaded."); return response.json(); })
      .then((data) => { setProducts(data.results ?? data); setCount(data.count ?? (data.results ?? data).length); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to connect to the marketplace."))
      .finally(() => setLoading(false));
  }, [category, brand, seller, query, minPrice, maxPrice, sort, page, inStock]);

  async function add(product: ProductSummary, wishlist = false) {
    if (!user) { router.push(`/login?next=${encodeURIComponent(wishlist ? "/wishlist" : "/cart")}`); return; }
    const response = await apiFetch(wishlist ? "/wishlist/" : "/cart/", { method: "POST", body: JSON.stringify(wishlist ? { product_id: product.id } : { product_id: product.id, quantity: 1 }) });
    setNotice(response.ok ? wishlist ? "Saved to wishlist." : "Added to your bag." : "The request could not be completed.");
  }

  return <main className="customer-site"><header className="market-header"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><form className="market-search" onSubmit={(event) => { event.preventDefault(); setPage(1); }}><input aria-label="Search products" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Search products" /><button aria-label="Search">⌕</button></form><nav className="market-actions"><a href="/wishlist">♡</a><a href="/cart">Bag</a><a href={user ? "/account" : "/login"}>{user?.first_name ?? "Sign in"}</a></nav></header>
    <div className="listing-heading"><p className="eyebrow">SHOPLEX / DISCOVER</p><h1>{title}</h1><p>{count} products in the marketplace</p></div>
    <div className="listing-layout">
      <aside className="listing-filters">
        <label>Category<select value={category} onChange={(event) => router.push(event.target.value ? `/category/${event.target.value}` : "/products")}><option value="">All categories</option>{categories.map((item) => <option key={item.slug} value={item.slug}>{item.name}</option>)}</select></label>
        <TextInput label="Minimum price" inputMode="decimal" value={minPrice} onChange={(event) => setMinPrice(event.target.value)} />
        <TextInput label="Maximum price" inputMode="decimal" value={maxPrice} onChange={(event) => setMaxPrice(event.target.value)} />
        <label>Sort by<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="newest">Newest</option><option value="popular">Popularity</option><option value="price_asc">Price: low to high</option><option value="price_desc">Price: high to low</option><option value="rating">Rating</option></select></label>
        <label className="check-label"><input type="checkbox" checked={inStock} onChange={(event) => setInStock(event.target.checked)} /> Available products</label>
      </aside>
      <section className="listing-results">{notice && <p className="form-success" role="status">{notice}</p>}{loading ? <LoadingState label="Loading products" /> : error ? <EmptyState title="Could not load products">{error}</EmptyState> : products.length ? <div className="product-grid">{products.map((product) => <ProductCard key={product.id} product={product} onAdd={(item) => void add(item)} onWish={(item) => void add(item, true)} />)}</div> : <EmptyState title="No matching products">Try changing your search or filters.</EmptyState>}
      {count > 24 && <div className="pagination"><Button variant="secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</Button><span>Page {page} of {Math.ceil(count / 24)}</span><Button variant="secondary" disabled={page >= Math.ceil(count / 24)} onClick={() => setPage((value) => value + 1)}>Next</Button></div>}</section>
    </div><footer className="market-footer"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><span>One Marketplace. Endless Opportunities.</span></footer></main>;
}

export function CustomerProductDetail({ slug, initialProduct = null }: { slug: string; initialProduct?: ProductSummary | null }) {
  const router = useRouter();
  const { user, apiFetch } = useSession();
  const [product, setProduct] = useState<ProductSummary | null>(initialProduct);
  const [related, setRelated] = useState<ProductSummary[]>([]);
  const [reviews, setReviews] = useState<Array<{ id: number; rating: number; title: string; body: string; customer_name: string; created_at: string }>>([]);
  const [variant, setVariant] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [message, setMessage] = useState("");
  const [review, setReview] = useState({ rating: 5, title: "", body: "" });
  const [loading, setLoading] = useState(!initialProduct);

  useEffect(() => {
    const productRequest = initialProduct
      ? Promise.resolve(initialProduct)
      : fetch(`${apiBase()}/products/${slug}/`).then(async (response) => { if (!response.ok) throw new Error("Product not found."); return response.json() as Promise<ProductSummary>; });
    productRequest
      .then(async (item) => {
        setProduct(item);
        const [relatedResponse, reviewResponse] = await Promise.all([
          fetch(`${apiBase()}/products/?category=${encodeURIComponent(item.category.slug)}`),
          fetch(`${apiBase()}/products/${slug}/reviews/`),
        ]);
        if (relatedResponse.ok) { const data = await relatedResponse.json(); setRelated((data.results ?? data).filter((row: ProductSummary) => row.id !== item.id).slice(0, 4)); }
        if (reviewResponse.ok) { const data = await reviewResponse.json(); setReviews(data.results ?? data); }
      })
      .catch(() => setMessage("This product is unavailable."))
      .finally(() => setLoading(false));
  }, [slug, initialProduct]);

  async function addToBag() {
    if (!product) return;
    if (!user) { router.push("/login?next=%2Fcart"); return; }
    const response = await apiFetch("/cart/", { method: "POST", body: JSON.stringify({ product_id: product.id, quantity, ...(variant ? { variant_id: variant } : {}) }) });
    setMessage(response.ok ? "Added to your bag." : "The selected quantity is not available.");
  }

  async function addToWishlist() {
    if (!product) return;
    if (!user) { router.push("/login?next=%2Fwishlist"); return; }
    const response = await apiFetch("/wishlist/", { method: "POST", body: JSON.stringify({ product_id: product.id }) });
    setMessage(response.ok ? "Saved to your wishlist." : "Could not save this product.");
  }

  async function addRelated(item: ProductSummary, wishlist = false) {
    if (!user) { router.push(`/login?next=${encodeURIComponent(wishlist ? "/wishlist" : "/cart")}`); return; }
    const response = await apiFetch(wishlist ? "/wishlist/" : "/cart/", { method: "POST", body: JSON.stringify(wishlist ? { product_id: item.id } : { product_id: item.id, quantity: 1 }) });
    setMessage(response.ok ? wishlist ? "Saved to your wishlist." : "Added to your bag." : "The request could not be completed.");
  }

  async function submitReview(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user) { router.push("/login"); return; }
    const response = await apiFetch(`/products/${slug}/reviews/`, { method: "POST", body: JSON.stringify(review) });
    const data = await response.json();
    if (!response.ok) { setMessage(data.detail ?? "A delivered purchase is required to review this item."); return; }
    setReviews((rows) => [data, ...rows]); setMessage("Your review was added.");
  }

  if (loading) return <main className="customer-site"><LoadingState label="Loading product" /></main>;
  if (!product) return <main className="customer-site"><EmptyState title="Product unavailable">{message}</EmptyState></main>;
  const selectedVariant = product.variants.find((row) => row.id === variant);
  const currentPrice = selectedVariant?.price ?? product.price;
  const jsonLd = { "@context": "https://schema.org", "@type": "Product", name: product.name, description: product.description, sku: product.variants.find((row) => row.id === variant)?.id, image: product.images.map((image) => image.image_url), offers: { "@type": "Offer", priceCurrency: "BDT", price: currentPrice, availability: product.in_stock ? "https://schema.org/InStock" : "https://schema.org/OutOfStock", url: `https://shoplex.com/products/${product.slug}` }, aggregateRating: product.review_count ? { "@type": "AggregateRating", ratingValue: product.average_rating, reviewCount: product.review_count } : undefined };
  return <main className="customer-site"><header className="market-header"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><nav className="market-actions"><a href="/products">Discover</a><a href="/wishlist">♡</a><a href="/cart">Bag</a><a href={user ? "/account" : "/login"}>{user?.first_name ?? "Sign in"}</a></nav></header><nav className="breadcrumbs"><a href="/">Home</a><span>/</span><a href={`/category/${product.category.slug}`}>{product.category.name}</a><span>/</span><span>{product.name}</span></nav>
    <section className="product-detail"><div className="product-gallery">{product.images[0] ? <img className="product-gallery__main" src={product.images[0].image_url} alt={product.images[0].alt_text || product.name} /> : <div className="product-gallery__empty">SHOPLEX / OBJECT</div>}<div className="product-gallery__thumbs">{product.images.map((image) => <img src={image.image_url} key={image.id} alt={image.alt_text || product.name} />)}</div></div><div className="product-info"><p className="eyebrow">{product.brand?.name ?? product.category.name}</p><h1>{product.name}</h1><a className="seller-link" href={`/stores/${product.seller.store_slug}`}>Sold by {product.seller.business_name}</a><div className="detail-rating">{product.average_rating ? `★ ${product.average_rating.toFixed(1)} (${product.review_count} reviews)` : "No reviews yet"}</div><div className="detail-price"><strong>{money(currentPrice)}</strong>{product.compare_at_price && <del>{money(product.compare_at_price)}</del>}</div><StatusPill tone={product.in_stock ? "success" : "danger"}>{product.in_stock ? "Available" : "Out of stock"}</StatusPill><p className="product-description">{product.description}</p>
      {product.variants.length > 0 && <label className="select-field">Choose an option<select value={variant} onChange={(event) => setVariant(event.target.value)}><option value="">Select option</option>{product.variants.map((item) => <option key={item.id} value={item.id} disabled={item.stock_quantity < 1}>{item.name}{item.stock_quantity < 1 ? " · sold out" : ""}</option>)}</select></label>}
      <label className="select-field">Quantity<input type="number" min="1" max="99" value={quantity} onChange={(event) => setQuantity(Math.max(1, Number(event.target.value)))} /></label><div className="detail-actions"><Button disabled={!product.in_stock || product.variants.length > 0 && !variant} onClick={() => void addToBag()}>Add to bag</Button><Button variant="secondary" onClick={() => void addToWishlist()}>Save ♡</Button></div>{message && <p className="form-success" role="status">{message}</p>}<dl className="product-attributes">{Object.entries(product.attributes ?? {}).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{String(value)}</dd></div>)}</dl></div></section>
    <section className="market-section reviews-section"><div className="section-heading"><div><p className="eyebrow">Customer notes</p><h2>Reviews</h2></div></div>{reviews.length ? reviews.map((item) => <article className="review-row" key={item.id}><strong>{"★".repeat(item.rating)}{"☆".repeat(5 - item.rating)} {item.title}</strong><p>{item.body}</p><small>{item.customer_name} · {new Date(item.created_at).toLocaleDateString()}</small></article>) : <EmptyState title="No reviews yet">Reviews are available from customers with a delivered order.</EmptyState>}{user && <form className="review-form" onSubmit={submitReview}><h3>Leave a review</h3><label>Rating<select value={review.rating} onChange={(event) => setReview({ ...review, rating: Number(event.target.value) })}>{[5, 4, 3, 2, 1].map((rating) => <option value={rating} key={rating}>{rating} stars</option>)}</select></label><TextInput label="Title" value={review.title} onChange={(event) => setReview({ ...review, title: event.target.value })} /><label>Review<textarea value={review.body} onChange={(event) => setReview({ ...review, body: event.target.value })} /></label><Button type="submit">Submit review</Button></form>}</section>
    {related.length > 0 && <section className="market-section"><div className="section-heading"><div><p className="eyebrow">Continue exploring</p><h2>Related products</h2></div></div><div className="product-grid">{related.map((item) => <ProductCard key={item.id} product={item} onAdd={(row) => void addRelated(row)} onWish={(row) => void addRelated(row, true)} />)}</div></section>}
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replaceAll("<", "\\u003c") }} />
  </main>;
}
