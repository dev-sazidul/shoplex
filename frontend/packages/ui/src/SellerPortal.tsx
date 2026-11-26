"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Card, DataTable, EmptyState, LoadingState, StatusPill, TextInput } from "./index";
import { useSession } from "./SessionProvider";

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export function SellerPortalHome() {
  const { user, apiFetch } = useSession();
  const [application, setApplication] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!user) return;
    setLoading(true);
    apiFetch("/seller/application/").then((response) => response.json()).then(setApplication).finally(() => setLoading(false));
  }, [user]);
  if (!user) return <main className="seller-front"><header className="market-header"><a className="wordmark" href="http://localhost:3000">SHOP<span>LEX</span><i>.</i></a><nav className="market-actions"><a href="/login">Sign in</a><a href="http://localhost:3000/register">Create customer account</a></nav></header><section className="seller-front__hero"><p className="eyebrow">SHOPLEX / SELLER PARTNER</p><h1>Your business,<br />with room to grow.</h1><p>Bring your products to a thoughtful marketplace of independent businesses.</p><div><Button onClick={() => window.location.assign("/login")}>Sign in to apply</Button><a className="text-link" href="http://localhost:3000/register">Create a SHOPLEX account</a></div></section><footer className="market-footer"><a href="http://localhost:3000">Customer marketplace</a><span>Seller applications are reviewed independently by Admin and Owner.</span></footer></main>;
  if (loading) return <main className="seller-front"><LoadingState label="Checking application status" /></main>;
  const sellerActive = user.roles.includes("seller");
  return <main className="seller-front"><header className="market-header"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><nav className="market-actions"><span>{user.first_name}</span><a href="/login">Switch account</a></nav></header><section className="seller-front__hero"><p className="eyebrow">SELLER / APPLICATION</p><h1>{sellerActive ? "Welcome to your store." : application?.status === "pending" ? "Your application is in review." : application?.status === "needs_info" ? "A little more information is needed." : application?.status === "rejected" ? "Your application needs another look." : "Start selling on SHOPLEX."}</h1><p>{sellerActive ? "Your seller workspace is ready." : application?.status === "pending" ? "Admin and Owner review applications independently. You will be notified when the status changes." : "Submit your business details and verification documents for review."}</p><div>{sellerActive ? <a className="button button--primary" href="/dashboard">Open seller dashboard</a> : <a className="button button--primary" href="/application">{application?.status === "needs_info" ? "Update application" : application?.status === "rejected" ? "Submit a new application" : application?.status === "pending" ? "View application" : "Apply to sell"}</a>}</div>{application && application.status !== "not_applied" && <div className="application-status"><StatusPill tone={application.status === "approved" ? "success" : application.status === "rejected" ? "danger" : "warning"}>{application.status.replaceAll("_", " ")}</StatusPill><p>{application.review_reason}</p><div>{application.approvals?.map((row: any, index: number) => <span key={index}>{row.reviewer_role}: {row.decision}</span>)}</div></div>}</section></main>;
}

function SellerFrame({ title, children }: { title: string; children: React.ReactNode }) {
  const router = useRouter(); const { user, logout } = useSession();
  useEffect(() => { if (!user) router.replace("/login"); }, [user, router]);
  useEffect(() => {
    if (user && title !== "Seller application" && !user.roles.includes("seller")) {
      router.replace("/application");
    }
  }, [title, user, router]);
  if (!user) return <main className="account-loading"><LoadingState label="Checking seller access" /></main>;
  if (title !== "Seller application" && !user.roles.includes("seller")) return <main className="account-loading"><LoadingState label="Checking seller approval" /></main>;
  return <main className="seller-shell"><header className="seller-topbar"><a className="wordmark" href="/">SHOP<span>LEX</span><i>.</i></a><span className="seller-topbar__title">SELLER / {title}</span><div><span>{user.email}</span><button onClick={() => void logout().then(() => router.replace("/"))}>Sign out</button></div></header><div className="seller-layout"><aside className="seller-sidebar"><p className="eyebrow">Store management</p><nav>{[["Overview", "/dashboard"], ["Products", "/products"], ["Orders", "/orders"], ["Returns", "/returns"], ["Earnings", "/earnings"], ["Application", "/application"]].map(([label, href]) => <a key={href} href={href}>{label}</a>)}</nav></aside><section className="seller-main"><div className="seller-page-heading"><p className="eyebrow">SHOPLEX / SELLER</p><h1>{title}</h1></div>{children}</section></div></main>;
}

export function SellerApplicationForm() {
  const { user, apiFetch } = useSession();
  const router = useRouter();
  const [error, setError] = useState(""); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  const [application, setApplication] = useState<any>(null);
  useEffect(() => { if (!user) { router.replace("/login"); return; } apiFetch("/seller/application/").then((response) => response.json()).then(setApplication).catch(() => undefined); }, [user]);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form); setBusy(true); setError("");
    const response = await apiFetch("/seller/application/", { method: "POST", body: data });
    const result = await response.json();
    if (!response.ok) setError(result.detail ?? Object.values(result).flat().join(" ") ?? "Application could not be submitted.");
    else { setApplication(result); setMessage("Application submitted for Admin and Owner review."); }
    setBusy(false);
  }
  return <SellerFrame title="Seller application">{application?.status === "pending" && <Card><StatusPill tone="warning">Pending review</StatusPill><p>Both Admin and Owner must approve your application before seller tools are enabled.</p></Card>}{application?.status !== "pending" && <form className="seller-form" onSubmit={submit} encType="multipart/form-data"><h2>Business details</h2><label>Business name<input name="business_name" defaultValue={application?.business_name ?? ""} required maxLength={180} /></label><label>Business type<select name="business_type" defaultValue={application?.business_type ?? "retail"}><option value="retail">Retail</option><option value="brand">Brand / manufacturer</option><option value="artisan">Independent maker</option><option value="other">Other</option></select></label><label>Business address<textarea name="business_address" defaultValue={application?.business_address ?? ""} required /></label><label>Business phone<input name="business_phone" defaultValue={user?.phone_number ?? ""} required /></label><label>Store description<textarea name="store_description" defaultValue="" maxLength={1500} /></label><label>Verification reference<input name="verification_reference" defaultValue={application?.verification_reference ?? ""} placeholder="Business registration or ID reference" /></label><label>Supporting documents<input name="documents" type="file" accept=".pdf,.png,.jpg,.jpeg" multiple /></label><p className="auth-note">PDF, PNG, or JPEG; max 10 MB per file. Documents are stored privately and only reviewers can access them.</p>{error && <p className="form-error" role="alert">{error}</p>}{message && <p className="form-success" role="status">{message}</p>}<Button type="submit" disabled={busy}>{busy ? "Submitting…" : application?.status === "needs_info" ? "Resubmit for review" : "Submit application"}</Button></form>}</SellerFrame>;
}

export function SellerDashboard() {
  const { apiFetch } = useSession(); const [data, setData] = useState<any>(null); const [error, setError] = useState("");
  useEffect(() => { apiFetch("/seller/dashboard/").then(async (response) => { if (!response.ok) throw new Error("An approved seller profile is required."); setData(await response.json()); }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load seller metrics.")); }, []);
  return <SellerFrame title="Overview">{error && <p className="form-error">{error}</p>}{data ? <><div className="seller-stat-grid"><Metric label="Products" value={data.products.total} /><Metric label="Published" value={data.products.published} /><Metric label="Pending review" value={data.products.pending} /><Metric label="Orders" value={data.orders.total} /><Metric label="Completed" value={data.orders.completed} /><Metric label="Units sold" value={data.orders.units_sold} /></div><div className="seller-finance-grid"><Metric label="Gross sales" value={`৳${Number(data.finance.gross_sales).toFixed(2)}`} /><Metric label="Platform commission" value={`৳${Number(data.finance.platform_commission).toFixed(2)}`} /><Metric label="Net earnings" value={`৳${Number(data.finance.net_earnings).toFixed(2)}`} /><Metric label="Available balance" value={`৳${Number(data.finance.available_balance).toFixed(2)}`} /></div><Card><h2>Fulfillment at a glance</h2><p>{data.finance.pending_settlement ? `৳${Number(data.finance.pending_settlement).toFixed(2)} in order earnings are not yet completed.` : "No pending order settlements."}</p><a className="text-link" href="/orders">Manage orders</a></Card></> : <LoadingState label="Loading your store" />}</SellerFrame>;
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) { return <article className="seller-metric"><span>{label}</span><strong>{value}</strong></article>; }

interface SellerProduct { id: string; name: string; slug: string; description: string; sku: string; price: string; compare_at_price: string | null; stock_quantity: number; status: string; category: string; approval_history: Array<{ reviewer_role: string; decision: string; reason: string }> }
interface SellerVariant { id: string; name: string; sku: string; options: Record<string, string>; price: string | null; stock_quantity: number; is_active: boolean }

export function SellerProducts() {
  const { apiFetch } = useSession(); const [products, setProducts] = useState<SellerProduct[]>([]); const [categories, setCategories] = useState<Array<{ slug: string; name: string }>>([]); const [selected, setSelected] = useState<SellerProduct | null>(null); const [files, setFiles] = useState<FileList | null>(null); const [error, setError] = useState(""); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  const [variantProduct, setVariantProduct] = useState<SellerProduct | null>(null); const [variants, setVariants] = useState<SellerVariant[]>([]);
  async function refresh() { const [p, c] = await Promise.all([apiFetch("/seller/products/"), fetch(`${api}/categories/`)]); if (p.ok) { const result = await p.json(); setProducts(result.results ?? result); } if (c.ok) { const result = await c.json(); setCategories(result.results ?? result); } }
  useEffect(() => { refresh().catch(() => setError("Products could not be loaded.")); }, []);
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const formData = new FormData(form); const payload = Object.fromEntries(formData.entries()); setBusy(true); setError(""); setMessage("");
    const response = await apiFetch(selected ? `/seller/products/${selected.id}/` : "/seller/products/", { method: selected ? "PATCH" : "POST", body: JSON.stringify(payload) });
    const product = await response.json();
    if (!response.ok) { setError(product.detail ?? Object.values(product).flat().join(" ") ?? "Product could not be saved."); setBusy(false); return; }
    if (files?.length) {
      for (const file of Array.from(files)) { const image = new FormData(); image.append("image", file); image.append("alt_text", product.name); const upload = await apiFetch(`/seller/products/${product.id}/images/`, { method: "POST", body: image }); if (!upload.ok) { setError("Product saved, but an image could not be uploaded."); setBusy(false); return; } }
    }
    setMessage("Draft saved. Add images and submit it for review when ready."); setSelected(null); setFiles(null); form.reset(); await refresh(); setBusy(false);
  }
  async function submitProduct(product: SellerProduct) { const response = await apiFetch(`/seller/products/${product.id}/submit/`, { method: "POST" }); if (!response.ok) { const result = await response.json(); setError(result.detail ?? Object.values(result).flat().join(" ")); return; } setMessage(`${product.name} submitted to Admin and Owner.`); await refresh(); }
  async function remove(product: SellerProduct) { const response = await apiFetch(`/seller/products/${product.id}/`, { method: "DELETE" }); if (response.ok) await refresh(); else setError("Only draft or returned products may be deleted."); }
  async function manageVariants(product: SellerProduct) { setVariantProduct(product); const response = await apiFetch(`/seller/products/${product.id}/variants/`); if (!response.ok) { setError("Product options could not be loaded."); return; } const data = await response.json(); setVariants(data.results ?? data); }
  async function addVariant(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!variantProduct) return;
    const form = event.currentTarget; const data = new FormData(form); let options: Record<string, string>;
    try { options = JSON.parse(String(data.get("options") || "{}")); } catch { setError('Options must be valid JSON, such as {"color":"Blue"}.'); return; }
    const payload = { name: data.get("name"), sku: data.get("sku"), options, price: data.get("price") || null, stock_quantity: Number(data.get("stock_quantity")), is_active: true };
    const response = await apiFetch(`/seller/products/${variantProduct.id}/variants/`, { method: "POST", body: JSON.stringify(payload) });
    const result = await response.json(); if (!response.ok) { setError(result.detail ?? Object.values(result).flat().join(" ")); return; }
    form.reset(); await manageVariants(variantProduct);
  }
  async function updateVariant(variant: SellerVariant, stock: number) {
    if (!variantProduct) return;
    const response = await apiFetch(`/seller/products/${variantProduct.id}/variants/${variant.id}/`, { method: "PATCH", body: JSON.stringify({ stock_quantity: stock }) });
    if (!response.ok) { setError("Variant stock could not be updated."); return; }
    setVariants((rows) => rows.map((row) => row.id === variant.id ? { ...row, stock_quantity: stock } : row));
  }
  return (
    <SellerFrame title="Products">
      <div className="seller-toolbar"><p>Manage your own listings, inventory, and approval status.</p><StatusPill>{products.length} products</StatusPill></div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {message && <p className="form-success" role="status">{message}</p>}
      <Card className="seller-editor">
        <h2>{selected ? "Edit draft" : "New product"}</h2>
        <form className="seller-form seller-form--grid" onSubmit={save}>
          <label>Product name<input name="name" defaultValue={selected?.name ?? ""} required /></label>
          <label>SKU<input name="sku" defaultValue={selected?.sku ?? ""} /></label>
          <label>Category<select name="category" defaultValue={selected?.category ?? ""} required><option value="">Choose category</option>{categories.map((category) => <option value={category.slug} key={category.slug}>{category.name}</option>)}</select></label>
          <label>Price (BDT)<input name="price" type="number" min="0.01" step="0.01" defaultValue={selected?.price ?? ""} required /></label>
          <label>Compare-at price<input name="compare_at_price" type="number" min="0.01" step="0.01" defaultValue={selected?.compare_at_price ?? ""} /></label>
          <label>Stock quantity<input name="stock_quantity" type="number" min="0" defaultValue={selected?.stock_quantity ?? 0} required /></label>
          <label className="seller-form__wide">Description<textarea name="description" defaultValue={selected?.description ?? ""} required /></label>
          <label>Product images<input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(event) => setFiles(event.target.files)} /></label>
          <div className="seller-form__actions"><Button type="submit" disabled={busy}>{busy ? "Saving…" : "Save draft"}</Button>{selected && <Button type="button" variant="secondary" onClick={() => setSelected(null)}>Cancel edit</Button>}</div>
        </form>
      </Card>
      <div className="seller-table-wrap"><table className="seller-table"><thead><tr><th>Product</th><th>SKU</th><th>Price</th><th>Stock</th><th>Status</th><th>Actions</th></tr></thead><tbody>
        {products.map((product) => <tr key={product.id}><td><strong>{product.name}</strong>{product.approval_history[0]?.reason && <small className="table-note">{product.approval_history[0].reason}</small>}</td><td>{product.sku || "—"}</td><td>৳{Number(product.price).toFixed(2)}</td><td>{product.stock_quantity}</td><td><StatusPill tone={product.status === "published" ? "success" : product.status.includes("reject") ? "danger" : "warning"}>{product.status.replaceAll("_", " ")}</StatusPill></td><td><div className="table-actions"><Button variant="quiet" onClick={() => setSelected(product)}>Edit</Button><Button variant="quiet" onClick={() => void manageVariants(product)}>Options</Button>{["draft", "rejected", "changes_requested"].includes(product.status) && <Button variant="quiet" onClick={() => void submitProduct(product)}>Submit</Button>}{["draft", "rejected", "changes_requested"].includes(product.status) && <Button variant="quiet" onClick={() => void remove(product)}>Delete</Button>}</div></td></tr>)}
      </tbody></table>{products.length === 0 && <EmptyState title="No products yet">Create a draft listing to start your catalog.</EmptyState>}</div>
      {variantProduct && <Card className="seller-editor"><div className="seller-toolbar"><h2>Options · {variantProduct.name}</h2><Button variant="quiet" onClick={() => setVariantProduct(null)}>Close</Button></div>{variants.map((variant) => <div className="variant-row" key={variant.id}><div><strong>{variant.name}</strong><small>{variant.sku} · {JSON.stringify(variant.options)}{variant.price ? ` · ৳${variant.price}` : ""}</small></div><label>Stock<input type="number" min="0" value={variant.stock_quantity} onChange={(event) => void updateVariant(variant, Number(event.target.value))} /></label></div>)}{["draft", "rejected", "changes_requested"].includes(variantProduct.status) && <form className="seller-form seller-form--grid" onSubmit={addVariant}><label>Option name<input name="name" placeholder="Blue / Large" required /></label><label>SKU<input name="sku" required /></label><label>Options JSON<input name="options" placeholder='{"color":"Blue","size":"M"}' required /></label><label>Price override<input name="price" type="number" min="0.01" step="0.01" /></label><label>Stock<input name="stock_quantity" type="number" min="0" defaultValue="0" required /></label><Button type="submit">Add option</Button></form>}</Card>}
    </SellerFrame>
  );
}

export function SellerOrders() {
  const { apiFetch } = useSession(); const [orders, setOrders] = useState<any[]>([]); const [error, setError] = useState(""); const [tracking, setTracking] = useState<Record<string, string>>({}); const [carrier, setCarrier] = useState<Record<string, string>>({});
  async function refresh() { const response = await apiFetch("/seller/orders/"); if (!response.ok) throw new Error("Seller orders could not be loaded."); const data = await response.json(); setOrders(data.results ?? data); }
  useEffect(() => { refresh().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load orders.")); }, []);
  async function advance(order: any, next: string) { const response = await apiFetch(`/seller/orders/${order.id}/fulfillment/`, { method: "POST", body: JSON.stringify({ status: next, carrier: carrier[order.id] ?? "", tracking_number: tracking[order.id] ?? "" }) }); if (!response.ok) { const result = await response.json(); setError(result.detail ?? result.tracking_number?.[0] ?? "Status update failed."); return; } await refresh(); }
  return <SellerFrame title="Orders">{error && <p className="form-error">{error}</p>}<div className="order-list">{orders.map((order) => <article className="order-card" key={order.id}><div className="order-card__head"><div><strong>{order.order_number}</strong><small>{new Date(order.created_at).toLocaleDateString()}</small></div><StatusPill>{order.status.replaceAll("_", " ")}</StatusPill></div><ul>{order.items.map((item: any, index: number) => <li key={index}>{item.product_name} × {item.quantity} · ৳{Number(item.line_total).toFixed(2)}</li>)}</ul><p>Seller net: ৳{Number(order.net_earnings).toFixed(2)}</p>{order.status === "processing" && <div className="fulfillment-controls"><input placeholder="Carrier" value={carrier[order.id] ?? ""} onChange={(event) => setCarrier({ ...carrier, [order.id]: event.target.value })} /><input placeholder="Tracking number" value={tracking[order.id] ?? ""} onChange={(event) => setTracking({ ...tracking, [order.id]: event.target.value })} /><Button onClick={() => void advance(order, "shipped")}>Mark shipped</Button></div>}{order.status === "shipped" && <Button onClick={() => void advance(order, "delivered")}>Mark delivered</Button>}{order.status === "delivered" && <Button onClick={() => void advance(order, "completed")}>Complete order</Button>}</article>)}{!orders.length && <EmptyState title="No orders yet">Orders containing your products will appear here.</EmptyState>}</div></SellerFrame>;
}

export function SellerReturns() {
  const { apiFetch } = useSession(); const [returns, setReturns] = useState<any[]>([]); const [error, setError] = useState("");
  async function refresh() { const response = await apiFetch("/seller/returns/"); if (response.ok) { const data = await response.json(); setReturns(data.results ?? data); } }
  useEffect(() => { refresh().catch(() => setError("Return requests could not be loaded.")); }, []);
  async function decide(row: any, decision: string) { const response = await apiFetch(`/seller/returns/${row.id}/review/`, { method: "POST", body: JSON.stringify({ decision }) }); if (!response.ok) { setError("Return decision could not be saved."); return; } await refresh(); }
  return <SellerFrame title="Returns">{error && <p className="form-error">{error}</p>}{returns.map((row) => <Card className="return-row" key={row.id}><div><strong>{row.order_number}</strong><StatusPill>{row.status}</StatusPill></div><p>{row.reason}</p>{row.status === "requested" && <div className="table-actions"><Button onClick={() => void decide(row, "approved")}>Approve request</Button><Button variant="secondary" onClick={() => void decide(row, "rejected")}>Decline</Button></div>}</Card>)}{!returns.length && <EmptyState title="No return requests">Customer return requests for your products will appear here.</EmptyState>}</SellerFrame>;
}

export function SellerEarnings() {
  const { apiFetch } = useSession(); const [data, setData] = useState<any>(null); const [payouts, setPayouts] = useState<any[]>([]); const [amount, setAmount] = useState(""); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  async function refresh() { const [summary, requests] = await Promise.all([apiFetch("/seller/dashboard/"), apiFetch("/seller/payout-requests/")]); if (summary.ok) setData(await summary.json()); if (requests.ok) { const result = await requests.json(); setPayouts(result.results ?? result); } }
  useEffect(() => { refresh().catch(() => setError("Earnings could not be loaded.")); }, []);
  async function requestPayout(event: React.FormEvent<HTMLFormElement>) { event.preventDefault(); const response = await apiFetch("/seller/payout-requests/", { method: "POST", body: JSON.stringify({ amount }) }); const result = await response.json(); if (!response.ok) setError(result.amount?.[0] ?? result.detail ?? "Payout request could not be submitted."); else { setMessage("Payout request sent for review."); setAmount(""); await refresh(); } }
  return <SellerFrame title="Earnings">{error && <p className="form-error">{error}</p>}{message && <p className="form-success">{message}</p>}{data ? <><div className="seller-finance-grid"><Metric label="Gross sales" value={`৳${Number(data.finance.gross_sales).toFixed(2)}`} /><Metric label="Commission" value={`৳${Number(data.finance.platform_commission).toFixed(2)}`} /><Metric label="Refunds" value={`৳${Number(data.finance.refunds).toFixed(2)}`} /><Metric label="Net earnings" value={`৳${Number(data.finance.net_earnings).toFixed(2)}`} /><Metric label="Available balance" value={`৳${Number(data.finance.available_balance).toFixed(2)}`} /><Metric label="Pending payout requests" value={data.finance.pending_payouts} /></div><Card><h2>Request a payout</h2><form className="payout-form" onSubmit={requestPayout}><TextInput label="Amount (BDT)" type="number" min="0.01" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} required /><Button type="submit">Submit request</Button></form><p className="auth-note">Requests are validated against completed eligible earnings and require Owner settlement review.</p></Card><h2>Payout requests</h2>{payouts.map((row) => <div className="payout-row" key={row.id}><strong>৳{Number(row.amount).toFixed(2)}</strong><StatusPill>{row.status}</StatusPill><small>{new Date(row.requested_at).toLocaleString()}</small></div>)}{!payouts.length && <EmptyState title="No payout requests" />}</> : <LoadingState label="Loading earnings" />}</SellerFrame>;
}
