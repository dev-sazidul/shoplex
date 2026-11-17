"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, DataTable, EmptyState, LoadingState, StatusPill } from "./index";
import { useSession } from "./SessionProvider";

interface Address {
  id: string; label: string; recipient_name: string; phone_number: string; address_line1: string;
  address_line2: string; city: string; region: string; postal_code: string; country_code: string; is_default: boolean;
}
interface Order {
  id: string; order_number: string; status: string; payment_method: string; total: string; created_at: string;
  seller_orders: Array<{ id: string; seller_name: string; status: string; carrier: string; tracking_number: string; items: Array<{ product_name: string; quantity: number; line_total: string }> }>;
}

const sections = [
  ["Overview", "/account"], ["Profile", "/account/profile"], ["Addresses", "/account/addresses"],
  ["Orders", "/account/orders"], ["Wishlist", "/account/wishlist"], ["Notifications", "/account/notifications"], ["Security", "/account/security"],
  ["Payments", "/account/payments"], ["My reviews", "/account/reviews"],
] as const;

function AccountFrame({ section, children }: { section: string; children: React.ReactNode }) {
  const router = useRouter();
  const { user, logout } = useSession();
  useEffect(() => { if (!user) router.replace(`/login?next=${encodeURIComponent(window.location.pathname)}`); }, [user, router]);
  if (!user) return <main className="account-loading"><LoadingState label="Checking your account" /></main>;
  return <main className="account-shell">
    <header className="market-header"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><nav className="market-actions"><a href="/cart">Bag</a><button onClick={() => void logout().then(() => router.replace("/"))}>Sign out</button></nav></header>
    <div className="account-layout"><aside className="account-nav"><p className="eyebrow">Your account</p><h1>{user.first_name} {user.last_name}</h1><p>{user.email}</p><nav aria-label="Account navigation">{sections.map(([label, href]) => <a key={href} className={section === href ? "is-active" : ""} href={href}>{label}</a>)}</nav></aside><section className="account-content">{children}</section></div>
  </main>;
}

export function CustomerAccount({ section = "/account" }: { section?: string }) {
  const { user, apiFetch } = useSession();
  const [profile, setProfile] = useState<Record<string, string> | null>(null);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [wishlist, setWishlist] = useState<Array<{ id: string; name: string; slug: string; price: string }>>([]);
  const [notifications, setNotifications] = useState<Array<{ id: string; title: string; body: string; read_at: string | null; created_at: string }>>([]);
  const [payments, setPayments] = useState<Array<{ id: number; order_number: string; method: string; status: string; amount: string; currency: string; created_at: string }>>([]);
  const [reviews, setReviews] = useState<Array<{ id: number; product_name: string; product_slug: string; rating: number; title: string; body: string; is_verified_purchase: boolean; created_at: string }>>([]);
  const [sessions, setSessions] = useState<Array<{ id: string; user_agent: string; ip_address: string; created_at: string; current: boolean; revoked: boolean }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load(path: string) {
    const response = await apiFetch(path);
    if (!response.ok) throw new Error("Account information could not be loaded.");
    const data = await response.json();
    if (path === "/profile/") setProfile(data);
    if (path === "/addresses/") setAddresses(data.results ?? data);
    if (path === "/orders/") setOrders(data.results ?? data);
    if (path === "/wishlist/") setWishlist(data.results ?? data);
    if (path === "/notifications/") setNotifications(data.results ?? data);
    if (path === "/auth/sessions/") setSessions(data.results ?? data);
    if (path === "/payments/") setPayments(data.results ?? data);
    if (path === "/reviews/mine/") setReviews(data.results ?? data);
  }

  useEffect(() => {
    if (!user) { setLoading(false); return; }
    const paths = section === "/account/profile" ? ["/profile/"]
      : section === "/account/addresses" ? ["/addresses/"]
      : section === "/account/orders" ? ["/orders/"]
      : section === "/account/wishlist" ? ["/wishlist/"]
      : section === "/account/notifications" ? ["/notifications/"]
      : section === "/account/security" ? ["/auth/sessions/"]
      : section === "/account/payments" ? ["/payments/"]
      : section === "/account/reviews" ? ["/reviews/mine/"]
      : ["/auth/me/", "/orders/", "/addresses/", "/wishlist/"];
    Promise.all(paths.map(load)).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load account data."))
      .finally(() => setLoading(false));
  }, [user, section]);

  async function saveProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!profile) return;
    const response = await apiFetch("/profile/", { method: "PATCH", body: JSON.stringify(profile) });
    if (!response.ok) { setError("Profile changes could not be saved."); return; }
    setProfile(await response.json()); setMessage("Profile updated.");
  }

  async function createAddress(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload = Object.fromEntries(form.entries());
    const response = await apiFetch("/addresses/", { method: "POST", body: JSON.stringify({ ...payload, is_default: form.get("is_default") === "on" }) });
    if (!response.ok) { setError("Address could not be saved."); return; }
    const address = await response.json() as Address;
    setAddresses((rows) => [address, ...rows]); setMessage("Address saved."); formElement.reset();
  }

  async function cancelOrder(order: Order) {
    const response = await apiFetch(`/orders/${order.id}/cancel/`, { method: "POST" });
    if (!response.ok) { setError("This order can no longer be cancelled."); return; }
    setOrders((rows) => rows.map((row) => row.id === order.id ? { ...row, status: "cancelled" } : row));
  }

  async function downloadInvoice(order: Order) {
    const response = await apiFetch(`/orders/${order.id}/invoice/`);
    if (!response.ok) { setError("Invoice could not be loaded."); return; }
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a"); link.href = url; link.download = `${order.order_number}-invoice.html`; link.click(); URL.revokeObjectURL(url);
  }

  async function markRead(id: string) {
    const response = await apiFetch(`/notifications/${id}/read/`, { method: "POST" });
    if (response.ok) setNotifications((rows) => rows.map((row) => row.id === id ? { ...row, read_at: new Date().toISOString() } : row));
  }

  async function revokeSession(id: string) {
    const response = await apiFetch(`/auth/sessions/${id}/`, { method: "DELETE" });
    if (response.ok) setSessions((rows) => rows.map((row) => row.id === id ? { ...row, revoked: true } : row));
  }

  const title = sections.find(([, href]) => href === section)?.[0] ?? "Overview";
  return <AccountFrame section={section}><div className="account-heading"><p className="eyebrow">SHOPLEX / ACCOUNT</p><h2>{title}</h2></div>
    {error && <p className="form-error" role="alert">{error}</p>}{message && <p className="form-success" role="status">{message}</p>}
    {loading ? <LoadingState label="Loading your account" /> : <>
      {section === "/account" && <div className="account-overview"><div className="account-stat"><span>Orders</span><strong>{orders.length}</strong><a href="/account/orders">View history →</a></div><div className="account-stat"><span>Saved items</span><strong>{wishlist.length}</strong><a href="/account/wishlist">View wishlist →</a></div><div className="account-stat"><span>Addresses</span><strong>{addresses.length}</strong><a href="/account/addresses">Manage addresses →</a></div><div className="account-wide"><h3>Recent orders</h3>{orders.slice(0, 3).map((order) => <OrderRow key={order.id} order={order} onCancel={cancelOrder} onInvoice={downloadInvoice} />)}{!orders.length && <EmptyState title="No orders yet">Your orders will appear here after checkout.</EmptyState>}</div></div>}
      {section === "/account/profile" && profile && <form className="account-form" onSubmit={saveProfile}><label>First name<input value={profile.first_name ?? ""} onChange={(e) => setProfile({ ...profile, first_name: e.target.value })} /></label><label>Last name<input value={profile.last_name ?? ""} onChange={(e) => setProfile({ ...profile, last_name: e.target.value })} /></label><label>Email<input value={profile.email ?? ""} disabled /></label><label>Phone<input value={profile.phone_number ?? ""} onChange={(e) => setProfile({ ...profile, phone_number: e.target.value })} /></label><label>Language<input value={profile.locale ?? "en"} onChange={(e) => setProfile({ ...profile, locale: e.target.value })} /></label><label>Time zone<input value={profile.timezone ?? "UTC"} onChange={(e) => setProfile({ ...profile, timezone: e.target.value })} /></label><Button type="submit">Save profile</Button></form>}
      {section === "/account/addresses" && <div className="address-panel"><form className="account-form" onSubmit={createAddress}><h3>Add a shipping address</h3><label>Label<input name="label" defaultValue="Home" /></label><label>Recipient name<input name="recipient_name" required /></label><label>Phone<input name="phone_number" required /></label><label>Address line<input name="address_line1" required /></label><label>Address line 2<input name="address_line2" /></label><label>City<input name="city" required /></label><label>Region<input name="region" /></label><label>Postal code<input name="postal_code" /></label><label>Country code<input name="country_code" defaultValue="BD" maxLength={2} required /></label><label className="check-label"><input name="is_default" type="checkbox" /> Make default</label><Button type="submit">Save address</Button></form><div><h3>Saved addresses</h3>{addresses.map((address) => <article className="address-card" key={address.id}><div><strong>{address.label}</strong>{address.is_default && <StatusPill tone="success">Default</StatusPill>}</div><p>{address.recipient_name} · {address.phone_number}<br />{address.address_line1}, {address.city}, {address.country_code}</p></article>)}{!addresses.length && <EmptyState title="No saved addresses">Add an address for faster checkout.</EmptyState>}</div></div>}
      {section === "/account/orders" && <div className="order-list">{orders.map((order) => <OrderRow key={order.id} order={order} onCancel={cancelOrder} onInvoice={downloadInvoice} />)}{!orders.length && <EmptyState title="No orders yet">Your order history will appear here.</EmptyState>}</div>}
      {section === "/account/wishlist" && <div className="wishlist-list">{wishlist.map((product) => <a className="wishlist-row" href={`/products/${product.slug}`} key={product.id}><span>{product.name}</span><strong>৳{Number(product.price).toFixed(2)}</strong></a>)}{!wishlist.length && <EmptyState title="Your wishlist is empty">Save products you would like to revisit.</EmptyState>}</div>}
      {section === "/account/notifications" && <div className="notification-list">{notifications.map((notice) => <article className="notification-row" key={notice.id}><div><strong>{notice.title}</strong><p>{notice.body}</p><small>{new Date(notice.created_at).toLocaleString()}</small></div>{!notice.read_at && <Button variant="quiet" onClick={() => markRead(notice.id)}>Mark read</Button>}</article>)}{!notifications.length && <EmptyState title="You're all caught up">Important updates will appear here.</EmptyState>}</div>}
      {section === "/account/payments" && <div className="payment-list">{payments.map((payment) => <a className="payment-row" href={`/account/orders`} key={payment.id}><div><strong>{payment.order_number}</strong><small>{new Date(payment.created_at).toLocaleString()} · {payment.method.toUpperCase()}</small></div><div><strong>৳{Number(payment.amount).toFixed(2)}</strong><StatusPill>{payment.status}</StatusPill></div></a>)}{!payments.length && <EmptyState title="No payments yet">Payment records appear here when an order is placed.</EmptyState>}</div>}
      {section === "/account/reviews" && <div className="review-history">{reviews.map((review) => <article className="notification-row" key={review.id}><div><a href={`/products/${review.product_slug}`}><strong>{review.product_name}</strong></a><p>{"★".repeat(review.rating)} {review.title}</p><small>{review.is_verified_purchase ? "Verified purchase" : "Review"} · {new Date(review.created_at).toLocaleDateString()}</small></div></article>)}{!reviews.length && <EmptyState title="No reviews yet">Reviews you leave will appear here.</EmptyState>}</div>}
      {section === "/account/security" && <div className="session-list"><p>Active devices and recent sign-ins for this account.</p>{sessions.map((session) => <article className="session-row" key={session.id}><div><strong>{session.user_agent || "Unknown device"}</strong><p>{session.ip_address || "IP unavailable"} · {new Date(session.created_at).toLocaleString()}</p></div><div>{session.current && <StatusPill tone="success">Current session</StatusPill>}{!session.current && !session.revoked && <Button variant="secondary" onClick={() => revokeSession(session.id)}>Revoke</Button>}{session.revoked && <StatusPill>Revoked</StatusPill>}</div></article>)}{!sessions.length && <EmptyState title="No sessions found">Sign-in sessions will appear here.</EmptyState>}</div>}
    </>}
  </AccountFrame>;
}

function OrderRow({ order, onCancel, onInvoice }: { order: Order; onCancel: (order: Order) => void; onInvoice: (order: Order) => void }) {
  return <article className="order-card"><div className="order-card__head"><div><strong>{order.order_number}</strong><small>{new Date(order.created_at).toLocaleDateString()}</small></div><StatusPill tone={order.status === "completed" ? "success" : order.status === "cancelled" ? "danger" : "neutral"}>{order.status.replaceAll("_", " ")}</StatusPill></div><div className="order-card__sellers">{order.seller_orders.map((sellerOrder) => <div key={sellerOrder.id}><strong>{sellerOrder.seller_name}</strong><span>{sellerOrder.status.replaceAll("_", " ")}{sellerOrder.tracking_number ? ` · ${sellerOrder.carrier} ${sellerOrder.tracking_number}` : ""}</span><ul>{sellerOrder.items.map((item, index) => <li key={`${sellerOrder.id}-${index}`}>{item.product_name} × {item.quantity}</li>)}</ul></div>)}</div><div className="order-card__foot"><strong>৳{Number(order.total).toFixed(2)}</strong><div><Button variant="quiet" onClick={() => onInvoice(order)}>Invoice</Button>{order.status === "processing" && <Button variant="quiet" onClick={() => onCancel(order)}>Cancel order</Button>}</div></div></article>;
}
