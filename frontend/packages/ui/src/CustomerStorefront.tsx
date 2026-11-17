"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { ProductSummary } from "@shoplex/types";
import { Button, EmptyState, StatusPill } from "./index";
import { useSession } from "./SessionProvider";

interface StorefrontData {
  categories: Array<{ name: string; slug: string }>;
  banners: Array<{ title: string; subtitle: string; image_url: string; target_url: string }>;
  featured_products: ProductSummary[];
  trending_products: ProductSummary[];
  best_sellers: ProductSummary[];
  new_arrivals: ProductSummary[];
  special_offers: ProductSummary[];
  featured_sellers: Array<{ store_slug: string; business_name: string; store_description: string; product_count: number }>;
}

function money(amount: string | null) {
  return amount ? `৳${Number(amount).toLocaleString("en-BD", { minimumFractionDigits: 2 })}` : "Price on request";
}

export function ProductCard({ product, onAdd, onWish }: { product: ProductSummary; onAdd: (product: ProductSummary) => void; onWish: (product: ProductSummary) => void }) {
  const image = product.images[0];
  return <article className="product-card">
    <a className="product-card__media" href={`/products/${product.slug}`}>
      {image ? <img src={image.image_url} alt={image.alt_text || product.name} loading="lazy" /> : <span className="product-card__placeholder">SHOPLEX / OBJECT</span>}
      {product.compare_at_price && <span className="product-card__offer">Offer</span>}
    </a>
    <div className="product-card__details">
      <p className="product-card__category">{product.brand?.name ?? product.category.name}</p>
      <a href={`/products/${product.slug}`} className="product-card__name">{product.name}</a>
      <div className="product-card__price"><strong>{money(product.price)}</strong>{product.compare_at_price && <del>{money(product.compare_at_price)}</del>}</div>
      <div className="product-card__meta"><span>{product.average_rating ? `★ ${product.average_rating.toFixed(1)}` : "New"}{product.review_count ? ` · ${product.review_count} reviews` : ""}</span><span>{product.in_stock ? "In stock" : "Sold out"}</span></div>
      <div className="product-card__actions"><Button disabled={!product.in_stock} onClick={() => onAdd(product)}>Add to bag</Button><Button variant="quiet" aria-label={`Add ${product.name} to wishlist`} onClick={() => onWish(product)}>♡</Button></div>
    </div>
  </article>;
}

function ProductSection({ title, eyebrow, items, onAdd, onWish, href }: { title: string; eyebrow: string; items: ProductSummary[]; onAdd: (product: ProductSummary) => void; onWish: (product: ProductSummary) => void; href?: string }) {
  return <section className="market-section">
    <div className="section-heading"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>{href && <a className="text-link" href={href}>View all <span aria-hidden="true">↗</span></a>}</div>
    {items.length ? <div className="product-grid">{items.map((product) => <ProductCard key={product.id} product={product} onAdd={onAdd} onWish={onWish} />)}</div> : <EmptyState title="No items available yet">Products appear here as sellers publish approved listings.</EmptyState>}
  </section>;
}

export function CustomerStorefront({ initialData = null }: { initialData?: StorefrontData | null }) {
  const router = useRouter();
  const { user, apiFetch } = useSession();
  const [data, setData] = useState<StorefrontData | null>(initialData);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Array<{ name: string; slug: string }>>([]);
  const [notice, setNotice] = useState("");
  const deferredQuery = query.trim();

  useEffect(() => {
    if (initialData) return;
    const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
    fetch(`${base}/storefront/`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Marketplace data could not be loaded.");
        return response.json() as Promise<StorefrontData>;
      })
      .then(setData)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to connect to SHOPLEX."));
  }, [initialData]);

  useEffect(() => {
    if (deferredQuery.length < 2) { setSuggestions([]); return; }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
      fetch(`${base}/products/suggestions/?q=${encodeURIComponent(deferredQuery)}`, { signal: controller.signal })
        .then((response) => response.ok ? response.json() : [])
        .then(setSuggestions)
        .catch(() => setSuggestions([]));
    }, 180);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [deferredQuery]);

  function search() {
    const value = query.trim();
    if (value) router.push(`/products?q=${encodeURIComponent(value)}`);
  }

  async function addToCart(product: ProductSummary) {
    if (!user) { router.push("/login?next=%2Fcart"); return; }
    try {
      const response = await apiFetch("/cart/", { method: "POST", body: JSON.stringify({ product_id: product.id, quantity: 1 }) });
      if (!response.ok) throw new Error("This product could not be added to your bag.");
      setNotice(`${product.name} added to your bag.`);
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : "Please sign in before adding items.");
    }
  }

  async function addToWishlist(product: ProductSummary) {
    if (!user) { router.push("/login?next=%2Fwishlist"); return; }
    try {
      const response = await apiFetch("/wishlist/", { method: "POST", body: JSON.stringify({ product_id: product.id }) });
      if (!response.ok) throw new Error("This product could not be saved.");
      setNotice(`${product.name} saved to your wishlist.`);
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : "Please try again.");
    }
  }

  const hero = data?.banners[0];
  return <main className="customer-site">
    <header className="market-header">
      <a className="wordmark" href="/" aria-label="SHOPLEX home">SHOP<span>LEX</span><i>.</i></a>
      <form className="market-search" onSubmit={(event) => { event.preventDefault(); search(); }} role="search">
        <label className="sr-only" htmlFor="market-search">Search products</label>
        <input id="market-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search the marketplace" autoComplete="off" />
        <button type="submit" aria-label="Search">⌕</button>
        {suggestions.length > 0 && <ul className="search-suggestions">{suggestions.map((item) => <li key={item.slug}><a href={`/products/${item.slug}`}>{item.name}</a></li>)}</ul>}
      </form>
      <nav className="market-actions" aria-label="Customer navigation"><a href="/wishlist" title="Wishlist">♡</a><a href="/cart" title="Shopping bag">Bag</a><a href={user ? "/account" : "/login"}>{user ? user.first_name : "Sign in"}</a></nav>
    </header>
    <nav className="category-nav" aria-label="Product categories"><a href="/products">Discover</a>{data?.categories.slice(0, 7).map((category) => <a key={category.slug} href={`/category/${category.slug}`}>{category.name}</a>)}<a href="/stores">Independent stores</a></nav>

    <section className="customer-hero" style={hero?.image_url ? { backgroundImage: `linear-gradient(90deg, rgba(21,27,41,.82), rgba(21,27,41,.08)), url('${hero.image_url}')` } : undefined}>
      <div className="customer-hero__copy"><p className="eyebrow">SHOPLEX / A NEW PERSPECTIVE</p><h1>{hero?.title ?? "A marketplace, thoughtfully found."}</h1><p>{hero?.subtitle ?? "Meet considered goods from independent businesses, all in one place."}</p><a className="hero-cta" href={hero?.target_url || "/products"}>Explore the collection <span aria-hidden="true">↗</span></a></div>
      <div className="customer-hero__aside"><span>01</span><span>Discover<br />something well made.</span></div>
    </section>

    {notice && <div className="market-notice" role="status">{notice}<button onClick={() => setNotice("")} aria-label="Dismiss">×</button></div>}
    {error ? <section className="market-section"><EmptyState title="Marketplace unavailable">{error}</EmptyState></section> : <>
      <section className="category-band"><div className="section-heading"><div><p className="eyebrow">Browse by interest</p><h2>Find your corner</h2></div></div>{data?.categories.length ? <div className="category-list">{data.categories.map((category, index) => <a key={category.slug} className="category-tile" href={`/category/${category.slug}`}><span>0{index + 1}</span><strong>{category.name}</strong><i aria-hidden="true">↗</i></a>)}</div> : <EmptyState title="Categories are being prepared">Browse products once the marketplace catalog is available.</EmptyState>}</section>
      {data && <>
        <ProductSection title="Featured finds" eyebrow="Selected for you" items={data.featured_products} onAdd={addToCart} onWish={addToWishlist} />
        <section className="seller-band"><div className="section-heading"><div><p className="eyebrow">Independent businesses</p><h2>Stores with a point of view</h2></div></div>{data.featured_sellers.length ? <div className="seller-list">{data.featured_sellers.map((seller, index) => <a key={seller.store_slug} href={`/stores/${seller.store_slug}`} className="seller-row"><span className="seller-row__index">0{index + 1}</span><span><strong>{seller.business_name}</strong><small>{seller.store_description || `${seller.product_count} published products`}</small></span><i aria-hidden="true">↗</i></a>)}</div> : <EmptyState title="No featured stores yet">Approved sellers will appear here as their catalogs go live.</EmptyState>}</section>
        <ProductSection title="Trending now" eyebrow="Moving through the marketplace" items={data.trending_products} onAdd={addToCart} onWish={addToWishlist} href="/products?sort=popular" />
        <ProductSection title="The latest edit" eyebrow="Just published" items={data.new_arrivals} onAdd={addToCart} onWish={addToWishlist} href="/products?sort=newest" />
        <ProductSection title="Worth a closer look" eyebrow="Special offers" items={data.special_offers} onAdd={addToCart} onWish={addToWishlist} />
        <ProductSection title="Best-selling" eyebrow="Loved across SHOPLEX" items={data.best_sellers} onAdd={addToCart} onWish={addToWishlist} />
      </>}
    </>}

    <NewsletterForm />
    <footer className="market-footer"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><p>One Marketplace. Endless Opportunities.</p><div><a href="/account">Your account</a><a href="/account/orders">Orders</a><a href="http://localhost:3001">Sell on SHOPLEX</a></div><small>© SHOPLEX 2026</small></footer>
  </main>;
}

function NewsletterForm() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(`${base}/newsletter/subscribe/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) });
    const result = await response.json();
    setMessage(response.ok ? "You are subscribed." : result.detail ?? "Subscription could not be completed.");
    if (response.ok) setEmail("");
  }
  return <section className="newsletter-band"><div><p className="eyebrow">Notes from the marketplace</p><h2>Good things, delivered occasionally.</h2><p>New stores, useful finds, and small moments worth opening.</p></div><form onSubmit={submit}><label htmlFor="newsletter-email">Email address</label><div><input id="newsletter-email" type="email" value={email} required onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /><Button type="submit">Subscribe</Button></div><span aria-live="polite">{message}</span></form></section>;
}
