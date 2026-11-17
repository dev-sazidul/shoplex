"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, EmptyState, LoadingState, StatusPill } from "./index";
import { useSession } from "./SessionProvider";

interface CartData {
  items: Array<{ id: number; product: { id: string; name: string; slug: string; price: string; images: Array<{ image_url: string; alt_text: string }>; seller: { business_name: string } }; variant: { id: string; name: string } | null; quantity: number; unit_price: string; line_total: string }>;
  subtotal: string;
  item_count: number;
}
interface Address { id: string; label: string; recipient_name: string; phone_number: string; address_line1: string; city: string; country_code: string; is_default: boolean }
const base = () => process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const money = (value: string) => `৳${Number(value).toFixed(2)}`;

export function CustomerCart({ checkout = false }: { checkout?: boolean }) {
  const router = useRouter();
  const { user, apiFetch } = useSession();
  const [cart, setCart] = useState<CartData | null>(null);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [addressId, setAddressId] = useState("");
  const [shippingTotal, setShippingTotal] = useState("0.00");
  const [coupon, setCoupon] = useState("");
  const [discount, setDiscount] = useState("0.00");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    if (!user) { setLoading(false); return; }
    const [cartResponse, addressResponse] = await Promise.all([apiFetch("/cart/"), apiFetch("/addresses/")]);
    if (!cartResponse.ok || !addressResponse.ok) throw new Error("Shopping information could not be loaded.");
    const cartData = await cartResponse.json(); const addressData = await addressResponse.json();
    setCart(cartData); const rows = addressData.results ?? addressData; setAddresses(rows);
    if (!addressId) setAddressId(rows.find((address: Address) => address.is_default)?.id ?? rows[0]?.id ?? "");
  }

  useEffect(() => { load().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load your bag.")).finally(() => setLoading(false)); }, [user]);

  useEffect(() => {
    if (!checkout || !addressId || !user) return;
    apiFetch(`/shipping/quote/?address_id=${encodeURIComponent(addressId)}`)
      .then(async (response) => { if (!response.ok) throw new Error("Shipping could not be calculated."); const quote = await response.json(); setShippingTotal(quote.shipping_total); })
      .catch(() => setError("Shipping could not be calculated for this address."));
  }, [checkout, addressId, user]);

  async function updateQuantity(itemId: number, quantity: number) {
    const response = await apiFetch(`/cart/items/${itemId}/`, { method: "PATCH", body: JSON.stringify({ quantity }) });
    if (!response.ok) { setError("Quantity could not be updated."); return; }
    setCart(await response.json());
  }

  async function removeItem(itemId: number) {
    const response = await apiFetch(`/cart/items/${itemId}/`, { method: "DELETE" });
    if (!response.ok) { setError("Item could not be removed."); return; }
    setCart(await response.json());
  }

  async function validateCoupon() {
    if (!cart || !coupon.trim()) return;
    const response = await apiFetch("/coupons/validate/", { method: "POST", body: JSON.stringify({ code: coupon, subtotal: cart.subtotal }) });
    const result = await response.json();
    if (!response.ok) { setError(result.code?.[0] ?? result.detail ?? "Coupon is not valid."); setDiscount("0.00"); return; }
    setError(""); setDiscount(result.discount); setMessage(`Coupon ${result.code} applied.`);
  }

  async function submitCheckout(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!cart?.items.length || !addressId) { setError("Choose a shipping address before placing your order."); return; }
    setBusy(true); setError("");
    const key = idempotencyKey || crypto.randomUUID(); setIdempotencyKey(key);
    try {
      const response = await apiFetch("/checkout/", {
        method: "POST",
        body: JSON.stringify({ address_id: addressId, payment_method: "cod", coupon_code: coupon.trim(), idempotency_key: key }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? Object.values(result).flat().join(" ") ?? "Checkout could not be completed.");
      router.push(`/orders/${result.id}`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Checkout could not be completed."); }
    finally { setBusy(false); }
  }

  if (!user) return <main className="simple-form-page"><EmptyState title="Sign in to view your bag"><a href="/login?next=%2Fcart">Sign in</a> or <a href="/register">create an account</a>.</EmptyState></main>;
  if (loading) return <main className="customer-site"><LoadingState label="Loading your bag" /></main>;
  const items = cart?.items ?? [];
  return <main className="customer-site"><header className="market-header"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><nav className="market-actions"><a href="/products">Continue shopping</a><a href="/account">Account</a></nav></header><div className="listing-heading"><p className="eyebrow">SHOPLEX / {checkout ? "CHECKOUT" : "YOUR BAG"}</p><h1>{checkout ? "Secure checkout" : "Your shopping bag"}</h1><p>{cart?.item_count ?? 0} items</p></div>
    {error && <p className="form-error market-message" role="alert">{error}</p>}{message && <p className="form-success market-message" role="status">{message}</p>}
    {!items.length ? <section className="market-section"><EmptyState title="Your bag is empty"><a className="text-link" href="/products">Explore the marketplace</a></EmptyState></section> : <div className="cart-layout"><section className="cart-items">{items.map((item) => <article className="cart-row" key={item.id}><a href={`/products/${item.product.slug}`} className="cart-row__image">{item.product.images[0] && <img src={item.product.images[0].image_url} alt={item.product.images[0].alt_text || item.product.name} />}</a><div className="cart-row__main"><a href={`/products/${item.product.slug}`}><strong>{item.product.name}</strong></a><small>{item.product.seller.business_name}{item.variant ? ` · ${item.variant.name}` : ""}</small><div className="cart-row__controls"><label>Quantity<select value={item.quantity} onChange={(event) => void updateQuantity(item.id, Number(event.target.value))}>{Array.from({ length: 10 }, (_, index) => index + 1).map((quantity) => <option value={quantity} key={quantity}>{quantity}</option>)}</select></label><Button variant="quiet" onClick={() => void removeItem(item.id)}>Remove</Button></div></div><strong>{money(item.line_total)}</strong></article>)}</section>
      <aside className="checkout-summary"><h2>Order summary</h2><div><span>Subtotal</span><strong>{money(cart?.subtotal ?? "0")}</strong></div>{Number(discount) > 0 && <div><span>Discount</span><strong>−{money(discount)}</strong></div>}<div><span>Shipping</span><strong>{checkout ? money(shippingTotal) : "Calculated at checkout"}</strong></div><div className="checkout-summary__total"><span>Total</span><strong>{money((Number(cart?.subtotal ?? 0) - Number(discount) + Number(shippingTotal)).toFixed(2))}</strong></div>
        <form className="coupon-form" onSubmit={(event) => { event.preventDefault(); void validateCoupon(); }}><label htmlFor="coupon-code">Coupon code</label><div><input id="coupon-code" value={coupon} onChange={(event) => setCoupon(event.target.value)} /><Button variant="secondary" type="submit">Apply</Button></div></form>
        {checkout ? <form className="checkout-form" onSubmit={submitCheckout}><label>Shipping address<select value={addressId} onChange={(event) => setAddressId(event.target.value)} required><option value="">Select an address</option>{addresses.map((address) => <option key={address.id} value={address.id}>{address.label}: {address.recipient_name}, {address.address_line1}, {address.city}</option>)}</select></label>{!addresses.length && <a className="text-link" href="/account/addresses">Add a shipping address</a>}<label>Payment method<select value="cod" disabled><option value="cod">Cash on delivery</option></select></label><p className="auth-note">Payment is collected on delivery. Online payment providers are not enabled in this phase.</p><Button type="submit" disabled={busy || !addresses.length}>{busy ? "Placing order…" : "Place order"}</Button></form> : <Button onClick={() => router.push("/checkout")}>Continue to checkout</Button>}
      </aside>
    </div>}
    <footer className="market-footer"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><span>One Marketplace. Endless Opportunities.</span></footer></main>;
}

export function CustomerOrderDetail({ orderId }: { orderId: string }) {
  const { user, apiFetch } = useSession();
  const router = useRouter();
  const [order, setOrder] = useState<any>(null);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (!user) { router.replace("/login"); return; }
    apiFetch(`/orders/${orderId}/`).then(async (response) => { if (!response.ok) throw new Error("Order not found."); setOrder(await response.json()); }).catch((failure: unknown) => setError(failure instanceof Error ? failure.message : "Order could not be loaded."));
  }, [orderId, user]);
  async function requestReturn(suborderId: string) {
    const response = await apiFetch(`/orders/suborders/${suborderId}/returns/`, { method: "POST", body: JSON.stringify({ reason }) });
    const data = await response.json();
    if (!response.ok) { setError(data.detail ?? "Return request could not be created."); return; }
    setMessage("Return request submitted.");
  }
  if (!order) return <main className="customer-site">{error ? <EmptyState title="Order unavailable">{error}</EmptyState> : <LoadingState label="Loading order" />}</main>;
  return <main className="customer-site"><header className="market-header"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><a href="/account/orders">Order history</a></header><div className="listing-heading"><p className="eyebrow">ORDER / {order.order_number}</p><h1>Order details</h1><StatusPill>{order.status.replaceAll("_", " ")}</StatusPill></div>{error && <p className="form-error">{error}</p>}{message && <p className="form-success">{message}</p>}
    {order.seller_orders.map((suborder: any) => <article className="order-card" key={suborder.id}><div className="order-card__head"><strong>{suborder.seller_name}</strong><StatusPill>{suborder.status.replaceAll("_", " ")}</StatusPill></div>{suborder.items.map((item: any, index: number) => <p key={index}>{item.product_name} × {item.quantity} · {money(item.line_total)}</p>)}{suborder.tracking_number && <p>Tracking: {suborder.carrier} / {suborder.tracking_number}</p>}{["delivered", "completed"].includes(suborder.status) && <form className="return-form" onSubmit={(event) => { event.preventDefault(); void requestReturn(suborder.id); }}><label>Return reason<textarea required minLength={8} value={reason} onChange={(event) => setReason(event.target.value)} /></label><Button variant="secondary" type="submit">Request return</Button></form>}</article>)}
    <footer className="market-footer"><span>Total paid on delivery: {money(order.total)}</span></footer></main>;
}
