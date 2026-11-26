"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { ProductSummary } from "@shoplex/types";
import { Badge, Breadcrumbs, Button, EmptyState, Icon, LoadingState, Modal, StatusPill, TextInput } from "./index";
import { ProductCard } from "./CustomerStorefront";
import { useSession } from "./SessionProvider";

const apiBase = () => process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const money = (value: string) => `৳${Number(value).toLocaleString("en-BD", { minimumFractionDigits: 2 })}`;

interface ProductPageData {
  count: number;
  results: ProductSummary[];
}

export function ProductListing({
  category = "",
  brand = "",
  seller = "",
  initialQuery = "",
  initialData = null,
}: {
  category?: string;
  brand?: string;
  seller?: string;
  initialQuery?: string;
  initialData?: ProductPageData | null;
}) {
  const router = useRouter();
  const { user, apiFetch } = useSession();
  const [products, setProducts] = useState<ProductSummary[]>(initialData?.results ?? []);
  const [categories, setCategories] = useState<Array<{ name: string; slug: string }>>([]);
  const [brands, setBrands] = useState<Array<{ name: string; slug: string }>>([]);
  const [sellers, setSellers] = useState<Array<{ business_name: string; store_slug: string }>>([]);
  const [selectedBrand, setSelectedBrand] = useState(brand);
  const [selectedSeller, setSelectedSeller] = useState(seller);
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
  const [quickViewProduct, setQuickViewProduct] = useState<ProductSummary | null>(null);

  const title = useMemo(
    () =>
      category
        ? category.replaceAll("-", " ")
        : selectedBrand
          ? selectedBrand.replaceAll("-", " ")
          : selectedSeller
            ? selectedSeller.replaceAll("-", " ")
            : query
              ? `Search: ${query}`
              : "All Collections",
    [category, selectedBrand, selectedSeller, query]
  );
  const skipFirstFetch = useRef(Boolean(initialData));

  useEffect(() => {
    const base = apiBase();
    fetch(`${base}/categories/`)
      .then((response) => (response.ok ? response.json() : []))
      .then((data) => setCategories(data.results ?? data))
      .catch(() => undefined);
    fetch(`${base}/brands/`)
      .then((response) => (response.ok ? response.json() : []))
      .then((data) => setBrands(data.results ?? data))
      .catch(() => undefined);
    fetch(`${base}/storefront/`)
      .then((response) =>
        response.ok
          ? (response.json() as Promise<{ featured_sellers?: Array<{ business_name: string; store_slug: string }> }>)
          : Promise.resolve({ featured_sellers: [] })
      )
      .then((data) => setSellers(data.featured_sellers ?? []))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (skipFirstFetch.current) {
      skipFirstFetch.current = false;
      return;
    }
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (selectedBrand) params.set("brand", selectedBrand);
    if (selectedSeller) params.set("seller", selectedSeller);
    if (query.trim()) params.set("q", query.trim());
    if (minPrice) params.set("min_price", minPrice);
    if (maxPrice) params.set("max_price", maxPrice);
    if (inStock) params.set("in_stock", "true");
    params.set("sort", sort);
    params.set("page", String(page));
    setLoading(true);
    setError("");
    fetch(`${apiBase()}/products/?${params.toString()}`)
      .then(async (response) => {
        if (!response.ok) throw new Error("Products could not be loaded.");
        return response.json();
      })
      .then((data) => {
        setProducts(data.results ?? data);
        setCount(data.count ?? (data.results ?? data).length);
      })
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Unable to connect to the marketplace.")
      )
      .finally(() => setLoading(false));
  }, [category, selectedBrand, selectedSeller, query, minPrice, maxPrice, sort, page, inStock]);

  async function add(product: ProductSummary, wishlist = false) {
    if (!user) {
      router.push(`/login?next=${encodeURIComponent(wishlist ? "/account/wishlist" : "/cart")}`);
      return;
    }
    const response = await apiFetch(wishlist ? "/wishlist/" : "/cart/", {
      method: "POST",
      body: JSON.stringify(wishlist ? { product_id: product.id } : { product_id: product.id, quantity: 1 }),
    });
    setNotice(response.ok ? (wishlist ? "Saved to wishlist." : "Added to your bag.") : "The request could not be completed.");
  }

  const collectionJsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: `${title} | SHOPLEX`,
    description: `Browse ${title} from verified independent sellers on SHOPLEX.`,
    mainEntity: {
      "@type": "ItemList",
      numberOfItems: count,
      itemListElement: products.slice(0, 12).map((item, index) => ({
        "@type": "ListItem",
        position: index + 1,
        name: item.name,
        url: `https://shoplex.com/products/${item.slug}`,
      })),
    },
  };

  return (
    <main className="customer-site">
      <header className="market-header">
        <a className="wordmark" href="/">
          SHOP<span>LEX</span>
          <i>.</i>
        </a>
        <form
          className="market-search market-search--pill"
          onSubmit={(event) => {
            event.preventDefault();
            setPage(1);
          }}
        >
          <input
            aria-label="Search products"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
            placeholder="Search products, brands, and stores…"
          />
          <button aria-label="Search">
            <Icon name="search" size={15} />
          </button>
        </form>
        <nav className="market-actions">
          <a href="/account/wishlist">Wishlist</a>
          <a href="/cart">Bag</a>
          <a href={user ? "/account" : "/login"}>{user?.first_name ?? "Sign in"}</a>
        </nav>
      </header>

      <div style={{ padding: "16px 6vw 0" }}>
        <Breadcrumbs
          items={[
            { label: "Home", href: "/" },
            { label: "Discover", href: "/products" },
            ...(category || selectedBrand || selectedSeller ? [{ label: title }] : []),
          ]}
        />
      </div>

      <div className="listing-heading">
        <p className="eyebrow">SHOPLEX / DISCOVER</p>
        <h1>{title}</h1>
        <p>{count} curated products in the marketplace</p>
      </div>

      <div className="listing-layout">
        <aside className="listing-filters">
          <label>
            Category
            <select
              value={category}
              onChange={(event) =>
                router.push(event.target.value ? `/category/${event.target.value}` : "/products")
              }
            >
              <option value="">All categories</option>
              {categories.map((item) => (
                <option key={item.slug} value={item.slug}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Brand
            <select
              value={selectedBrand}
              onChange={(event) => {
                setSelectedBrand(event.target.value);
                setPage(1);
              }}
            >
              <option value="">All brands</option>
              {brands.map((item) => (
                <option key={item.slug} value={item.slug}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Verified Seller
            <select
              value={selectedSeller}
              onChange={(event) => {
                setSelectedSeller(event.target.value);
                setPage(1);
              }}
            >
              <option value="">All sellers</option>
              {sellers.map((item) => (
                <option key={item.store_slug} value={item.store_slug}>
                  {item.business_name}
                </option>
              ))}
            </select>
          </label>
          <TextInput
            label="Minimum price (BDT)"
            inputMode="decimal"
            value={minPrice}
            onChange={(event) => {
              setMinPrice(event.target.value);
              setPage(1);
            }}
          />
          <TextInput
            label="Maximum price (BDT)"
            inputMode="decimal"
            value={maxPrice}
            onChange={(event) => {
              setMaxPrice(event.target.value);
              setPage(1);
            }}
          />
          <label>
            Sort by
            <select
              value={sort}
              onChange={(event) => {
                setSort(event.target.value);
                setPage(1);
              }}
            >
              <option value="newest">Newest arrivals</option>
              <option value="popular">Best selling / Popular</option>
              <option value="price_asc">Price: low to high</option>
              <option value="price_desc">Price: high to low</option>
              <option value="rating">Customer rating</option>
            </select>
          </label>
          <label className="check-label">
            <input
              type="checkbox"
              checked={inStock}
              onChange={(event) => {
                setInStock(event.target.checked);
                setPage(1);
              }}
            />{" "}
            In-stock items only
          </label>
          {(selectedBrand || selectedSeller || minPrice || maxPrice || inStock || query) && (
            <Button
              variant="quiet"
              size="sm"
              onClick={() => {
                setSelectedBrand("");
                setSelectedSeller("");
                setMinPrice("");
                setMaxPrice("");
                setInStock(false);
                setQuery("");
                setPage(1);
              }}
            >
              Reset filters
            </Button>
          )}
        </aside>

        <section className="listing-results">
          {notice && (
            <p className="form-success" role="status">
              {notice}
            </p>
          )}
          {loading ? (
            <LoadingState label="Loading products" />
          ) : error ? (
            <EmptyState title="Could not load products">{error}</EmptyState>
          ) : products.length ? (
            <div className="product-grid">
              {products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  onAdd={(item) => void add(item)}
                  onWish={(item) => void add(item, true)}
                  onQuickView={setQuickViewProduct}
                />
              ))}
            </div>
          ) : (
            <EmptyState title="No matching products">Try changing your search or filters.</EmptyState>
          )}
          {count > 24 && (
            <div className="pagination">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
                Previous
              </Button>
              <span>
                Page {page} of {Math.ceil(count / 24)}
              </span>
              <Button
                variant="secondary"
                disabled={page >= Math.ceil(count / 24)}
                onClick={() => setPage((value) => value + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </section>
      </div>

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
            <div style={{ fontSize: 18, fontWeight: 700 }}>{money(quickViewProduct.price)}</div>
            <div style={{ display: "flex", gap: 10 }}>
              <Button
                disabled={!quickViewProduct.in_stock}
                onClick={() => {
                  void add(quickViewProduct);
                  setQuickViewProduct(null);
                }}
              >
                Add to bag
              </Button>
              <Button variant="secondary" onClick={() => router.push(`/products/${quickViewProduct.slug}`)}>
                Full details ↗
              </Button>
            </div>
          </div>
        )}
      </Modal>

      <footer className="market-footer">
        <a className="wordmark" href="/">
          SHOP<span>LEX</span>
          <i>.</i>
        </a>
        <span>One Marketplace. Endless Opportunities.</span>
      </footer>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(collectionJsonLd).replaceAll("<", "\\u003c") }}
      />
    </main>
  );
}

export function CustomerProductDetail({
  slug,
  initialProduct = null,
}: {
  slug: string;
  initialProduct?: ProductSummary | null;
}) {
  const router = useRouter();
  const { user, apiFetch } = useSession();
  const [product, setProduct] = useState<ProductSummary | null>(initialProduct);
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const [related, setRelated] = useState<ProductSummary[]>([]);
  const [reviews, setReviews] = useState<
    Array<{ id: number; rating: number; title: string; body: string; customer_name: string; created_at: string }>
  >([]);
  const [variant, setVariant] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [message, setMessage] = useState("");
  const [review, setReview] = useState({ rating: 5, title: "", body: "" });
  const [loading, setLoading] = useState(!initialProduct);

  useEffect(() => {
    const productRequest = initialProduct
      ? Promise.resolve(initialProduct)
      : fetch(`${apiBase()}/products/${slug}/`).then(async (response) => {
          if (!response.ok) throw new Error("Product not found.");
          return response.json() as Promise<ProductSummary>;
        });
    productRequest
      .then(async (item) => {
        setProduct(item);
        setActiveImageIndex(0);
        if (item.variants.length > 0) {
          const firstAvailable = item.variants.find((v) => v.stock_quantity > 0);
          if (firstAvailable) setVariant(firstAvailable.id);
        }
        const [relatedResponse, reviewResponse] = await Promise.all([
          fetch(`${apiBase()}/products/?category=${encodeURIComponent(item.category.slug)}`),
          fetch(`${apiBase()}/products/${slug}/reviews/`),
        ]);
        if (relatedResponse.ok) {
          const data = await relatedResponse.json();
          setRelated((data.results ?? data).filter((row: ProductSummary) => row.id !== item.id).slice(0, 4));
        }
        if (reviewResponse.ok) {
          const data = await reviewResponse.json();
          setReviews(data.results ?? data);
        }
      })
      .catch(() => setMessage("This product is unavailable."))
      .finally(() => setLoading(false));
  }, [slug, initialProduct]);

  async function addToBag() {
    if (!product) return;
    if (!user) {
      router.push("/login?next=%2Fcart");
      return;
    }
    const response = await apiFetch("/cart/", {
      method: "POST",
      body: JSON.stringify({
        product_id: product.id,
        quantity,
        ...(variant ? { variant_id: variant } : {}),
      }),
    });
    setMessage(response.ok ? "Added to your shopping bag." : "The selected quantity is not available.");
  }

  async function addToWishlist() {
    if (!product) return;
    if (!user) {
      router.push("/login?next=%2Faccount%2Fwishlist");
      return;
    }
    const response = await apiFetch("/wishlist/", {
      method: "POST",
      body: JSON.stringify({ product_id: product.id }),
    });
    setMessage(response.ok ? "Saved to your wishlist." : "Could not save this product.");
  }

  async function addRelated(item: ProductSummary, wishlist = false) {
    if (!user) {
      router.push(`/login?next=${encodeURIComponent(wishlist ? "/account/wishlist" : "/cart")}`);
      return;
    }
    const response = await apiFetch(wishlist ? "/wishlist/" : "/cart/", {
      method: "POST",
      body: JSON.stringify(wishlist ? { product_id: item.id } : { product_id: item.id, quantity: 1 }),
    });
    setMessage(
      response.ok ? (wishlist ? "Saved to your wishlist." : "Added to your bag.") : "The request could not be completed."
    );
  }

  async function submitReview(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user) {
      router.push("/login");
      return;
    }
    const response = await apiFetch(`/products/${slug}/reviews/`, {
      method: "POST",
      body: JSON.stringify(review),
    });
    const data = await response.json();
    if (!response.ok) {
      setMessage(data.detail ?? "A delivered purchase is required to review this item.");
      return;
    }
    setReviews((rows) => [data, ...rows]);
    setMessage("Your verified review was published.");
  }

  if (loading) return <main className="customer-site"><LoadingState label="Loading product" /></main>;
  if (!product) return <main className="customer-site"><EmptyState title="Product unavailable">{message}</EmptyState></main>;

  const selectedVariant = product.variants.find((row) => row.id === variant);
  const currentPrice = selectedVariant?.price ?? product.price;
  const activeSku = selectedVariant?.sku || product.sku || `SLX-${product.id.slice(0, 6).toUpperCase()}`;
  const activeImage = product.images[activeImageIndex] ?? product.images[0];
  const initials = product.name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

  const jsonLd = [
    {
      "@context": "https://schema.org",
      "@type": "Product",
      name: product.name,
      description: product.description,
      sku: activeSku,
      brand: product.brand ? { "@type": "Brand", name: product.brand.name } : undefined,
      image: product.images.map((image) => image.image_url),
      offers: {
        "@type": "Offer",
        priceCurrency: "BDT",
        price: currentPrice,
        availability: product.in_stock ? "https://schema.org/InStock" : "https://schema.org/OutOfStock",
        seller: { "@type": "Organization", name: product.seller.business_name },
        url: `https://shoplex.com/products/${product.slug}`,
      },
      aggregateRating: product.review_count
        ? { "@type": "AggregateRating", ratingValue: product.average_rating, reviewCount: product.review_count }
        : undefined,
    },
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Home", item: "https://shoplex.com/" },
        {
          "@type": "ListItem",
          position: 2,
          name: product.category.name,
          item: `https://shoplex.com/category/${product.category.slug}`,
        },
        {
          "@type": "ListItem",
          position: 3,
          name: product.name,
          item: `https://shoplex.com/products/${product.slug}`,
        },
      ],
    },
  ];

  return (
    <main className="customer-site">
      <header className="market-header">
        <a className="wordmark" href="/">
          SHOP<span>LEX</span>
          <i>.</i>
        </a>
        <nav className="market-actions">
          <a href="/products">Discover</a>
          <a href="/account/wishlist">Wishlist</a>
          <a href="/cart">Bag</a>
          <a href={user ? "/account" : "/login"}>{user?.first_name ?? "Sign in"}</a>
        </nav>
      </header>

      <div style={{ padding: "16px 8vw 0" }}>
        <Breadcrumbs
          items={[
            { label: "Home", href: "/" },
            { label: product.category.name, href: `/category/${product.category.slug}` },
            { label: product.name },
          ]}
        />
      </div>

      <section className="product-detail">
        <div className="product-gallery">
          {activeImage ? (
            <img
              className="product-gallery__main"
              src={activeImage.image_url}
              alt={activeImage.alt_text || product.name}
              style={{ borderRadius: "var(--radius-md)" }}
            />
          ) : (
            <div className="product-gallery__empty" style={{ borderRadius: "var(--radius-md)", overflow: "hidden" }}>
              <div className="product-card__visual">
                <span className="product-card__visual-tag">{product.category.name}</span>
                <span className="product-card__visual-monogram" style={{ width: 96, height: 96, fontSize: 32 }}>
                  {initials}
                </span>
                <div className="product-card__visual-foot">
                  <span>{product.brand?.name ?? "SHOPLEX Flagship Edition"}</span>
                  <span>SKU: {activeSku}</span>
                </div>
              </div>
            </div>
          )}
          {product.images.length > 1 && (
            <div className="product-gallery__thumbs">
              {product.images.map((image, idx) => (
                <button
                  key={image.id}
                  type="button"
                  onClick={() => setActiveImageIndex(idx)}
                  style={{
                    padding: 0,
                    border: idx === activeImageIndex ? "2px solid var(--cobalt)" : "1px solid var(--line)",
                    borderRadius: 6,
                    overflow: "hidden",
                    cursor: "pointer",
                    background: "none",
                  }}
                >
                  <img src={image.image_url} alt={image.alt_text || product.name} />
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="product-info">
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
            <Badge tone="gold">{product.brand?.name ?? product.category.name}</Badge>
            <span style={{ fontSize: 11, color: "var(--slate)", fontFamily: "monospace" }}>SKU: {activeSku}</span>
          </div>
          <h1>{product.name}</h1>
          <a className="seller-link" href={`/stores/${product.seller.store_slug}`}>
            Sold &amp; fulfilled by <strong>{product.seller.business_name}</strong> (Verified Partner)
          </a>
          <div className="detail-rating">
            {product.average_rating
              ? `★ ${product.average_rating.toFixed(1)} (${product.review_count} verified reviews)`
              : "★ New arrival · No reviews yet"}
          </div>
          <div className="detail-price">
            <strong>{money(currentPrice)}</strong>
            {product.compare_at_price && <del>{money(product.compare_at_price)}</del>}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <StatusPill tone={product.in_stock ? "success" : "danger"}>
              {product.in_stock ? "In Stock & Ready to Ship" : "Out of Stock"}
            </StatusPill>
            {selectedVariant && (
              <span style={{ fontSize: 12, color: "var(--slate)" }}>
                {selectedVariant.stock_quantity} units available
              </span>
            )}
          </div>
          <p className="product-description">{product.description}</p>

          {product.variants.length > 0 && (
            <div style={{ margin: "18px 0" }}>
              <span style={{ display: "block", fontSize: 12, fontWeight: 600, marginBottom: 8 }}>
                Select Variation (Size / Color)
              </span>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {product.variants.map((item) => {
                  const optionSummary = Object.entries(item.options ?? {})
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(" · ");
                  const isSelected = variant === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      disabled={item.stock_quantity < 1}
                      onClick={() => setVariant(item.id)}
                      style={{
                        padding: "8px 14px",
                        borderRadius: "var(--radius-sm)",
                        border: isSelected ? "2px solid var(--navy-deep)" : "1px solid var(--line)",
                        background: isSelected ? "var(--navy-deep)" : "#fff",
                        color: isSelected ? "#fff" : "var(--ink)",
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: item.stock_quantity < 1 ? "not-allowed" : "pointer",
                        opacity: item.stock_quantity < 1 ? 0.45 : 1,
                      }}
                    >
                      {item.name}
                      {optionSummary ? ` (${optionSummary})` : ""}
                      {item.stock_quantity < 1 ? " · Sold out" : ""}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <label className="select-field">
            Quantity
            <input
              type="number"
              min="1"
              max="99"
              value={quantity}
              onChange={(event) => setQuantity(Math.max(1, Number(event.target.value)))}
            />
          </label>
          <div className="detail-actions">
            <Button
              size="lg"
              disabled={!product.in_stock || (product.variants.length > 0 && !variant)}
              onClick={() => void addToBag()}
            >
              Add to Shopping Bag
            </Button>
            <Button variant="secondary" size="lg" onClick={() => void addToWishlist()}>
              Save to Wishlist ♡
            </Button>
          </div>
          {message && (
            <p className="form-success" role="status">
              {message}
            </p>
          )}
          <dl className="product-attributes">
            <div>
              <dt>SKU</dt>
              <dd>{activeSku}</dd>
            </div>
            <div>
              <dt>Department</dt>
              <dd>{product.category.name}</dd>
            </div>
            {product.brand && (
              <div>
                <dt>Brand</dt>
                <dd>{product.brand.name}</dd>
              </div>
            )}
            {Object.entries(product.attributes ?? {}).map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>{String(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="market-section reviews-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Verified Purchasers</p>
            <h2>Customer Reviews</h2>
          </div>
        </div>
        {reviews.length ? (
          reviews.map((item) => (
            <article className="review-row" key={item.id}>
              <strong>
                {"★".repeat(item.rating)}
                {"☆".repeat(5 - item.rating)} {item.title}
              </strong>
              <p>{item.body}</p>
              <small>
                {item.customer_name} · Verified Purchase · {new Date(item.created_at).toLocaleDateString()}
              </small>
            </article>
          ))
        ) : (
          <EmptyState title="No reviews yet">
            Reviews are available from customers with a delivered order.
          </EmptyState>
        )}
        {user && (
          <form className="review-form" onSubmit={submitReview}>
            <h3>Leave a Verified Review</h3>
            <label>
              Rating
              <select
                value={review.rating}
                onChange={(event) => setReview({ ...review, rating: Number(event.target.value) })}
              >
                {[5, 4, 3, 2, 1].map((rating) => (
                  <option value={rating} key={rating}>
                    {rating} stars
                  </option>
                ))}
              </select>
            </label>
            <TextInput
              label="Headline"
              value={review.title}
              onChange={(event) => setReview({ ...review, title: event.target.value })}
            />
            <label>
              Review details
              <textarea
                value={review.body}
                onChange={(event) => setReview({ ...review, body: event.target.value })}
              />
            </label>
            <Button type="submit">Submit review</Button>
          </form>
        )}
      </section>

      {related.length > 0 && (
        <section className="market-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Continue Exploring</p>
              <h2>Related Products</h2>
            </div>
          </div>
          <div className="product-grid">
            {related.map((item) => (
              <ProductCard
                key={item.id}
                product={item}
                onAdd={(row) => void addRelated(row)}
                onWish={(row) => void addRelated(row, true)}
              />
            ))}
          </div>
        </section>
      )}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replaceAll("<", "\\u003c") }}
      />
    </main>
  );
}
