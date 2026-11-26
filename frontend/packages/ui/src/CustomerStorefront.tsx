"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { ProductSummary } from "@shoplex/types";
import { Badge, Button, EmptyState, Icon, Modal, StatusPill } from "./index";
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

function discountPercent(price: string, compareAt: string | null) {
  if (!compareAt) return null;
  const p = Number(price);
  const c = Number(compareAt);
  if (!c || c <= p) return null;
  return Math.round(((c - p) / c) * 100);
}

export function ProductCard({
  product,
  onAdd,
  onWish,
  onQuickView,
}: {
  product: ProductSummary;
  onAdd: (product: ProductSummary) => void;
  onWish: (product: ProductSummary) => void;
  onQuickView?: (product: ProductSummary) => void;
}) {
  const image = product.images[0];
  const discount = discountPercent(product.price, product.compare_at_price);
  const initials = product.name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

  return (
    <article className="product-card">
      <a className="product-card__media" href={`/products/${product.slug}`}>
        {image ? (
          <img src={image.image_url} alt={image.alt_text || product.name} loading="lazy" />
        ) : (
          <div className="product-card__visual">
            <span className="product-card__visual-tag">{product.category.name}</span>
            <span className="product-card__visual-monogram">{initials}</span>
            <div className="product-card__visual-foot">
              <span>{product.brand?.name ?? "SHOPLEX Edition"}</span>
              <span>Verified</span>
            </div>
          </div>
        )}
        {discount && <span className="product-card__offer">−{discount}%</span>}
      </a>
      <div className="product-card__details">
        <p className="product-card__category">{product.brand?.name ?? product.category.name}</p>
        <a href={`/products/${product.slug}`} className="product-card__name">
          {product.name}
        </a>
        <span className="product-card__seller">by {product.seller.business_name}</span>
        <div className="product-card__price">
          <strong>{money(product.price)}</strong>
          {product.compare_at_price && <del>{money(product.compare_at_price)}</del>}
          {discount && <span className="product-card__discount">Save {discount}%</span>}
        </div>
        <div className="product-card__meta">
          <span>
            {product.average_rating ? `★ ${product.average_rating.toFixed(1)}` : "★ Curated"}
            {product.review_count ? ` (${product.review_count})` : ""}
          </span>
          <span>{product.in_stock ? "In stock" : "Sold out"}</span>
        </div>
        <div className="product-card__actions">
          <Button disabled={!product.in_stock} onClick={() => onAdd(product)}>
            Add to bag
          </Button>
          {onQuickView && (
            <Button
              variant="secondary"
              size="sm"
              aria-label={`Quick view ${product.name}`}
              onClick={() => onQuickView(product)}
            >
              <Icon name="eye" size={15} />
            </Button>
          )}
          <Button variant="quiet" aria-label={`Add ${product.name} to wishlist`} onClick={() => onWish(product)}>
            ♡
          </Button>
        </div>
      </div>
    </article>
  );
}

function ProductSection({
  title,
  eyebrow,
  items,
  onAdd,
  onWish,
  onQuickView,
  href,
}: {
  title: string;
  eyebrow: string;
  items: ProductSummary[];
  onAdd: (product: ProductSummary) => void;
  onWish: (product: ProductSummary) => void;
  onQuickView?: (product: ProductSummary) => void;
  href?: string;
}) {
  return (
    <section className="market-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        {href && (
          <a className="text-link" href={href}>
            View all <span aria-hidden="true">↗</span>
          </a>
        )}
      </div>
      {items.length ? (
        <div className="product-grid">
          {items.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              onAdd={onAdd}
              onWish={onWish}
              onQuickView={onQuickView}
            />
          ))}
        </div>
      ) : (
        <EmptyState title="No items available yet">
          Products appear here as sellers publish approved listings.
        </EmptyState>
      )}
    </section>
  );
}

export function CustomerStorefront({ initialData = null }: { initialData?: StorefrontData | null }) {
  const router = useRouter();
  const { user, apiFetch } = useSession();
  const [data, setData] = useState<StorefrontData | null>(initialData);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Array<{ name: string; slug: string }>>([]);
  const [notice, setNotice] = useState("");
  const [quickViewProduct, setQuickViewProduct] = useState<ProductSummary | null>(null);
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
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Unable to connect to SHOPLEX.")
      );
  }, [initialData]);

  useEffect(() => {
    if (deferredQuery.length < 2) {
      setSuggestions([]);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
      fetch(`${base}/products/suggestions/?q=${encodeURIComponent(deferredQuery)}`, {
        signal: controller.signal,
      })
        .then((response) => (response.ok ? response.json() : []))
        .then(setSuggestions)
        .catch(() => setSuggestions([]));
    }, 180);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [deferredQuery]);

  function search() {
    const value = query.trim();
    if (value) router.push(`/products?q=${encodeURIComponent(value)}`);
  }

  async function addToCart(product: ProductSummary) {
    if (!user) {
      router.push("/login?next=%2Fcart");
      return;
    }
    try {
      const response = await apiFetch("/cart/", {
        method: "POST",
        body: JSON.stringify({ product_id: product.id, quantity: 1 }),
      });
      if (!response.ok) throw new Error("This product could not be added to your bag.");
      setNotice(`${product.name} added to your shopping bag.`);
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : "Please sign in before adding items.");
    }
  }

  async function addToWishlist(product: ProductSummary) {
    if (!user) {
      router.push("/login?next=%2Faccount%2Fwishlist");
      return;
    }
    try {
      const response = await apiFetch("/wishlist/", {
        method: "POST",
        body: JSON.stringify({ product_id: product.id }),
      });
      if (!response.ok) throw new Error("This product could not be saved.");
      setNotice(`${product.name} saved to your wishlist.`);
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : "Please try again.");
    }
  }

  const hero = data?.banners[0];
  return (
    <main className="customer-site">
      <div className="market-announcement">
        <span>
          <strong>SHOPLEX</strong> · One Marketplace. Endless Opportunities. Dual-verified sellers &amp; buyer protection on every order.
        </span>
        <div className="market-announcement__links">
          <a href="/stores">Verified Stores</a>
          <a href="/brands">Brands</a>
          <a href="http://localhost:3001">Sell on SHOPLEX</a>
        </div>
      </div>

      <header className="market-header">
        <a className="wordmark" href="/" aria-label="SHOPLEX home">
          SHOP<span>LEX</span>
          <i>.</i>
        </a>
        <form
          className="market-search market-search--pill"
          onSubmit={(event) => {
            event.preventDefault();
            search();
          }}
          role="search"
        >
          <label className="sr-only" htmlFor="market-search">
            Search products
          </label>
          <input
            id="market-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search products, luxury brands, and verified stores…"
            autoComplete="off"
          />
          <button type="submit" aria-label="Search">
            <Icon name="search" size={16} />
          </button>
          {suggestions.length > 0 && (
            <ul className="search-suggestions">
              {suggestions.map((item) => (
                <li key={item.slug}>
                  <a href={`/products/${item.slug}`}>{item.name}</a>
                </li>
              ))}
            </ul>
          )}
        </form>
        <nav className="market-actions" aria-label="Customer navigation">
          <a className="market-action-link" href="/account/wishlist" title="Wishlist">
            <Icon name="heart" size={16} />
            <span>Wishlist</span>
          </a>
          <a className="market-action-link" href="/cart" title="Shopping bag">
            <Icon name="bag" size={16} />
            <span>Bag</span>
          </a>
          <a className="market-action-link" href={user ? "/account" : "/login"}>
            <Icon name="user" size={16} />
            <span>{user ? user.first_name : "Sign in"}</span>
          </a>
        </nav>
      </header>

      <nav className="category-nav" aria-label="Product categories">
        <a href="/products">All Collections</a>
        {data?.categories.slice(0, 7).map((category) => (
          <a key={category.slug} href={`/category/${category.slug}`}>
            {category.name}
          </a>
        ))}
        <a href="/brands">Brands</a>
        <a href="/stores">Independent Stores</a>
      </nav>

      <section
        className="customer-hero customer-hero--luxury"
        style={
          hero?.image_url
            ? {
                backgroundImage: `linear-gradient(90deg, rgba(15,23,42,.88), rgba(15,23,42,.25)), url('${hero.image_url}')`,
              }
            : undefined
        }
      >
        <div className="customer-hero__copy">
          <p className="eyebrow">SHOPLEX / INTERNATIONAL MARKETPLACE</p>
          <h1>{hero?.title ?? "Curated excellence from verified merchants."}</h1>
          <p>
            {hero?.subtitle ??
              "Discover flagship electronics, contemporary fashion, and artisanal home design from dual-approved independent businesses."}
          </p>
          <div className="hero-actions">
            <Button variant="gold" size="lg" onClick={() => router.push(hero?.target_url || "/products")}>
              Explore Collection <span aria-hidden="true">↗</span>
            </Button>
            <a className="hero-cta" href="/stores">
              Meet Verified Sellers <span>→</span>
            </a>
          </div>
          <div className="customer-hero__badges">
            <span className="customer-hero__badge">Dual-Verified Merchants</span>
            <span className="customer-hero__badge">Split-Order Checkout</span>
            <span className="customer-hero__badge">Authentic Guarantee</span>
          </div>
        </div>

        <div className="customer-hero__showcase" aria-label="Featured marketplace highlights">
          <a className="hero-showcase-card" href="/category/electronics">
            <span>01 / Flagship Tech</span>
            <strong>Northline Audio &amp; Wearables</strong>
            <small>Precision engineering · Official warranty</small>
          </a>
          <a className="hero-showcase-card" href="/category/fashion">
            <span>02 / Apparel Edit</span>
            <strong>Atelier Dhaka Heritage</strong>
            <small>Handloom textiles &amp; tailored linen</small>
          </a>
          <a className="hero-showcase-card" href="/category/watches-accessories">
            <span>03 / Horology</span>
            <strong>Automatic Timepieces</strong>
            <small>Sapphire crystal &amp; full-grain leather</small>
          </a>
          <a className="hero-showcase-card" href="/category/home-living">
            <span>04 / Living</span>
            <strong>Verde Ceramic Studio</strong>
            <small>Sustainable stoneware &amp; craft</small>
          </a>
        </div>
      </section>

      <section className="trust-strip" aria-label="Customer assurances">
        <div className="trust-item">
          <span className="trust-item__icon">
            <Icon name="shield" size={18} />
          </span>
          <div>
            <strong>Dual-Verified Sellers</strong>
            <span>Every merchant is independently approved by Admin and Owner.</span>
          </div>
        </div>
        <div className="trust-item">
          <span className="trust-item__icon">
            <Icon name="sparkles" size={18} />
          </span>
          <div>
            <strong>Curated Authenticity</strong>
            <span>Every listing passes quality moderation before publication.</span>
          </div>
        </div>
        <div className="trust-item">
          <span className="trust-item__icon">
            <Icon name="truck" size={18} />
          </span>
          <div>
            <strong>Transparent Fulfillment</strong>
            <span>Real-time per-seller shipment tracking and printable invoices.</span>
          </div>
        </div>
        <div className="trust-item">
          <span className="trust-item__icon">
            <Icon name="refresh" size={18} />
          </span>
          <div>
            <strong>Protected Returns</strong>
            <span>Direct suborder return requests with platform oversight.</span>
          </div>
        </div>
      </section>

      {notice && (
        <div className="market-notice" role="status">
          <span>{notice}</span>
          <button onClick={() => setNotice("")} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}

      {error ? (
        <section className="market-section">
          <EmptyState title="Marketplace unavailable">{error}</EmptyState>
        </section>
      ) : (
        <>
          <section className="category-band">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Browse by Department</p>
                <h2>Curated Categories</h2>
              </div>
              <a className="text-link" href="/products">
                All departments <span aria-hidden="true">↗</span>
              </a>
            </div>
            {data?.categories.length ? (
              <div className="category-list">
                {data.categories.map((category, index) => (
                  <a key={category.slug} className="category-tile" href={`/category/${category.slug}`}>
                    <span>0{index + 1}</span>
                    <strong>{category.name}</strong>
                    <i aria-hidden="true">↗</i>
                  </a>
                ))}
              </div>
            ) : (
              <EmptyState title="Categories are being prepared">
                Browse products once the marketplace catalog is available.
              </EmptyState>
            )}
          </section>

          {data && (
            <>
              <ProductSection
                title="Featured Collections"
                eyebrow="Selected by SHOPLEX Curators"
                items={data.featured_products}
                onAdd={addToCart}
                onWish={addToWishlist}
                onQuickView={setQuickViewProduct}
                href="/products"
              />

              <section className="promo-banner" aria-label="Promotional highlight">
                <div>
                  <Badge tone="gold">Limited Edition Offers</Badge>
                  <h2>Privileged pricing across flagship collections.</h2>
                  <p>
                    Enjoy transparent savings directly from verified brand partners and independent studios.
                  </p>
                </div>
                <Button variant="gold" size="lg" onClick={() => router.push("/products")}>
                  Shop Special Offers
                </Button>
              </section>

              <ProductSection
                title="Trending Now"
                eyebrow="Most Sought-After Across SHOPLEX"
                items={data.trending_products}
                onAdd={addToCart}
                onWish={addToWishlist}
                onQuickView={setQuickViewProduct}
                href="/products?sort=popular"
              />

              <section className="seller-band">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Verified Flagship Stores</p>
                    <h2>Independent Merchants with Distinction</h2>
                  </div>
                  <a className="text-link" href="/stores">
                    All stores <span aria-hidden="true">↗</span>
                  </a>
                </div>
                {data.featured_sellers.length ? (
                  <div className="seller-list">
                    {data.featured_sellers.map((seller, index) => (
                      <a key={seller.store_slug} href={`/stores/${seller.store_slug}`} className="seller-row">
                        <span className="seller-row__index">0{index + 1}</span>
                        <span>
                          <strong>{seller.business_name}</strong>
                          <small>
                            {seller.store_description || `${seller.product_count} published products`} ·{" "}
                            {seller.product_count} items
                          </small>
                        </span>
                        <i aria-hidden="true">↗</i>
                      </a>
                    ))}
                  </div>
                ) : (
                  <EmptyState title="No featured stores yet">
                    Approved sellers will appear here as their catalogs go live.
                  </EmptyState>
                )}
              </section>

              <ProductSection
                title="New Arrivals"
                eyebrow="Recently Approved & Published"
                items={data.new_arrivals}
                onAdd={addToCart}
                onWish={addToWishlist}
                onQuickView={setQuickViewProduct}
                href="/products?sort=newest"
              />

              <ProductSection
                title="Special Offers"
                eyebrow="Considered Value"
                items={data.special_offers}
                onAdd={addToCart}
                onWish={addToWishlist}
                onQuickView={setQuickViewProduct}
              />

              <ProductSection
                title="Best Sellers"
                eyebrow="Customer Favorites"
                items={data.best_sellers}
                onAdd={addToCart}
                onWish={addToWishlist}
                onQuickView={setQuickViewProduct}
              />
            </>
          )}
        </>
      )}

      <Modal
        open={Boolean(quickViewProduct)}
        title={quickViewProduct?.name ?? "Product preview"}
        onClose={() => setQuickViewProduct(null)}
      >
        {quickViewProduct && (
          <div style={{ display: "grid", gap: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <Badge tone="gold">{quickViewProduct.brand?.name ?? quickViewProduct.category.name}</Badge>
              <StatusPill tone={quickViewProduct.in_stock ? "success" : "danger"}>
                {quickViewProduct.in_stock ? "In Stock" : "Out of Stock"}
              </StatusPill>
            </div>
            <p style={{ margin: 0, color: "var(--slate)", fontSize: 13, lineHeight: 1.65 }}>
              {quickViewProduct.description}
            </p>
            <div style={{ fontSize: 18, fontWeight: 700 }}>
              {money(quickViewProduct.price)}{" "}
              {quickViewProduct.compare_at_price && (
                <del style={{ color: "var(--slate)", fontSize: 13, fontWeight: 400 }}>
                  {money(quickViewProduct.compare_at_price)}
                </del>
              )}
            </div>
            <p style={{ margin: 0, fontSize: 12, color: "var(--slate)" }}>
              Sold by <strong>{quickViewProduct.seller.business_name}</strong>
            </p>
            <div style={{ display: "flex", gap: 10, marginTop: 6 }}>
              <Button
                disabled={!quickViewProduct.in_stock}
                onClick={() => {
                  void addToCart(quickViewProduct);
                  setQuickViewProduct(null);
                }}
              >
                Add to bag
              </Button>
              <Button
                variant="secondary"
                onClick={() => router.push(`/products/${quickViewProduct.slug}`)}
              >
                Full details ↗
              </Button>
            </div>
          </div>
        )}
      </Modal>

      <NewsletterForm />

      <footer className="market-footer-rich">
        <div className="market-footer-rich__grid">
          <div>
            <a className="wordmark wordmark--light" href="/">
              SHOP<span>LEX</span>
              <i>.</i>
            </a>
            <p style={{ marginTop: 12, fontSize: 13, lineHeight: 1.6, maxWidth: 320 }}>
              One Marketplace. Endless Opportunities. An international multi-vendor platform connecting discerning customers with verified independent merchants.
            </p>
          </div>
          <div>
            <h4>Marketplace</h4>
            <ul>
              <li><a href="/products">All Collections</a></li>
              <li><a href="/brands">Featured Brands</a></li>
              <li><a href="/stores">Independent Stores</a></li>
              <li><a href="/products?sort=newest">New Arrivals</a></li>
            </ul>
          </div>
          <div>
            <h4>Customer Care</h4>
            <ul>
              <li><a href="/account">My Account</a></li>
              <li><a href="/account/orders">Order Tracking</a></li>
              <li><a href="/account/wishlist">Saved Wishlist</a></li>
              <li><a href="/account/addresses">Address Book</a></li>
            </ul>
          </div>
          <div>
            <h4>Ecosystem Portals</h4>
            <ul>
              <li><a href="http://localhost:3001">Seller Workspace (3001)</a></li>
              <li><a href="http://localhost:3002">Admin Operations (3002)</a></li>
              <li><a href="http://localhost:3003">Manager Analytics (3003)</a></li>
              <li><a href="http://localhost:3004">Owner Console (3004)</a></li>
            </ul>
          </div>
        </div>
        <div className="market-footer-rich__bottom">
          <span>© 2026 SHOPLEX Marketplace. All rights reserved.</span>
          <span>Secured by Argon2 · Rotating JWT · Server-Enforced RBAC</span>
        </div>
      </footer>
    </main>
  );
}

function NewsletterForm() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(`${base}/newsletter/subscribe/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const result = await response.json();
    setMessage(
      response.ok ? "Thank you for subscribing to the SHOPLEX private dispatch." : result.detail ?? "Subscription could not be completed."
    );
    if (response.ok) setEmail("");
  }
  return (
    <section className="newsletter-band">
      <div>
        <p className="eyebrow">Private Dispatch</p>
        <h2>Curated arrivals, delivered occasionally.</h2>
        <p>Receive invitations to new flagship store launches, seasonal edits, and private offers.</p>
      </div>
      <form onSubmit={submit}>
        <label htmlFor="newsletter-email">Email address</label>
        <div>
          <input
            id="newsletter-email"
            type="email"
            value={email}
            required
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />
          <Button type="submit">Subscribe</Button>
        </div>
        <span aria-live="polite">{message}</span>
      </form>
    </section>
  );
}
