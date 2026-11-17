"use client";

import { useEffect, useState } from "react";
import { EmptyState, LoadingState } from "./index";

export function BrandDirectory() {
  const [brands, setBrands] = useState<Array<{ name: string; slug: string; description: string; logo_url: string }>>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
    fetch(`${base}/brands/`).then((response) => response.ok ? response.json() : []).then((data) => setBrands(data.results ?? data)).finally(() => setLoading(false));
  }, []);
  return <main className="customer-site"><header className="market-header"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><nav className="market-actions"><a href="/products">Discover</a><a href="/cart">Bag</a></nav></header><div className="listing-heading"><p className="eyebrow">SHOPLEX / BRANDS</p><h1>Brands with intention</h1><p>Browse makers and labels currently available on SHOPLEX.</p></div><section className="brand-directory">{loading ? <LoadingState label="Loading brands" /> : brands.length ? brands.map((brand, index) => <a className="brand-row" href={`/brand/${brand.slug}`} key={brand.slug}><span>0{index + 1}</span><strong>{brand.name}</strong><p>{brand.description}</p><i aria-hidden="true">↗</i></a>) : <EmptyState title="No brands listed yet">Brands appear here when the marketplace catalog is set up.</EmptyState>}</section><footer className="market-footer"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><span>One Marketplace. Endless Opportunities.</span></footer></main>;
}

export function StoreDirectory() {
  const [stores, setStores] = useState<Array<{ store_slug: string; business_name: string; store_description: string; product_count: number }>>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
    fetch(`${base}/storefront/`).then((response) => response.ok ? response.json() : Promise.reject()).then((data) => setStores(data.featured_sellers ?? [])).catch(() => setStores([])).finally(() => setLoading(false));
  }, []);
  return <main className="customer-site"><header className="market-header"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><nav className="market-actions"><a href="/products">Discover</a><a href="/brands">Brands</a></nav></header><div className="listing-heading"><p className="eyebrow">SHOPLEX / SELLERS</p><h1>Independent stores</h1><p>Meet the people and businesses behind the products.</p></div><section className="brand-directory">{loading ? <LoadingState label="Loading stores" /> : stores.length ? stores.map((store, index) => <a className="brand-row" href={`/stores/${store.store_slug}`} key={store.store_slug}><span>0{index + 1}</span><strong>{store.business_name}</strong><p>{store.store_description || `${store.product_count} published products`}</p><i aria-hidden="true">↗</i></a>) : <EmptyState title="No stores listed yet">Approved stores will appear here as they publish products.</EmptyState>}</section><footer className="market-footer"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><span>One Marketplace. Endless Opportunities.</span></footer></main>;
}
