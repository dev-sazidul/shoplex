"use client";

import { useEffect, useState } from "react";
import type { ApiHealth } from "@shoplex/types";
import {
  Badge,
  BarChart,
  Button,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  LoadingState,
  Notification,
  PortalShell,
  StatCard,
  StatusPill,
} from "./index";
import type { SidebarItem } from "./index";
import { useSession } from "./SessionProvider";

function money(amount: string | number | undefined | null) {
  const num = Number(amount ?? 0);
  return `৳${num.toLocaleString("en-BD", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function AdminPortal() {
  const { user, apiFetch, logout } = useSession();
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [activeTab, setActiveTab] = useState("#overview");
  const [overview, setOverview] = useState<any>(null);
  const [adminData, setAdminData] = useState<any>(null);
  const [sellerQueue, setSellerQueue] = useState<any[]>([]);
  const [productQueue, setProductQueue] = useState<any[]>([]);
  const [productReports, setProductReports] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [reviewNote, setReviewNote] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

  useEffect(() => {
    fetch(`${apiBase}/health/`, { cache: "no-store" })
      .then((res) => (res.ok ? (res.json() as Promise<ApiHealth>) : null))
      .then(setHealth)
      .catch(() => setHealth(null));
  }, [apiBase]);

  async function loadAdminData() {
    if (!user) return;
    setLoading(true);
    setError("");
    try {
      await Promise.all([
        apiFetch("/notifications/").then(async (res) => {
          if (res.ok) {
            const data = await res.json();
            setNotifications(data.results ?? data);
          }
        }),
        apiFetch("/management/overview/").then(async (res) => {
          if (res.ok) setOverview(await res.json());
        }),
        apiFetch("/management/admin-dashboard/").then(async (res) => {
          if (res.ok) setAdminData(await res.json());
        }),
        apiFetch("/management/seller-applications/").then(async (res) => {
          if (res.ok) {
            const data = await res.json();
            setSellerQueue(data.results ?? data);
          }
        }),
        apiFetch("/management/product-approvals/").then(async (res) => {
          if (res.ok) {
            const data = await res.json();
            setProductQueue(data.results ?? data);
          }
        }),
        apiFetch("/management/product-reports/").then(async (res) => {
          if (res.ok) setProductReports(await res.json());
        }),
      ]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load Admin operations data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAdminData();
  }, [user]);

  async function decideSeller(applicationId: number, decision: "approved" | "needs_info" | "rejected") {
    setError("");
    setMessage("");
    const response = await apiFetch(`/management/seller-applications/${applicationId}/review/`, {
      method: "POST",
      body: JSON.stringify({ decision, reason: reviewNote[`seller-${applicationId}`] ?? "" }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? "Seller review decision could not be recorded.");
      return;
    }
    setMessage(`Seller application #${applicationId} decision (${decision.replaceAll("_", " ")}) recorded independently for Admin.`);
    await loadAdminData();
  }

  async function downloadSellerDocument(applicationId: number, documentId: number, filename: string) {
    setError("");
    const response = await apiFetch(`/management/seller-applications/${applicationId}/documents/${documentId}/`);
    if (!response.ok) {
      setError("Verification document could not be downloaded.");
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function decideProduct(productId: string, decision: "approved" | "changes_requested" | "rejected") {
    setError("");
    setMessage("");
    const response = await apiFetch(`/management/products/${productId}/review/`, {
      method: "POST",
      body: JSON.stringify({ decision, reason: reviewNote[`product-${productId}`] ?? "" }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? "Product review decision could not be recorded.");
      return;
    }
    setMessage(`Product "${data.name}" decision (${decision.replaceAll("_", " ")}) recorded independently for Admin.`);
    await loadAdminData();
  }

  async function suspendProduct(productId: string) {
    setError("");
    setMessage("");
    const response = await apiFetch(`/management/products/${productId}/status/`, {
      method: "POST",
      body: JSON.stringify({ action: "suspend", reason: reviewNote[`mod-${productId}`] || "Admin moderation policy action" }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? "Product could not be suspended.");
      return;
    }
    setMessage(`Product "${data.name}" suspended.`);
    await loadAdminData();
  }

  async function resolveReport(reportId: string, decision: "resolved" | "dismissed", suspend = false) {
    setError("");
    setMessage("");
    const response = await apiFetch(`/management/product-reports/${reportId}/resolve/`, {
      method: "POST",
      body: JSON.stringify({
        status: decision,
        resolution_note: reviewNote[`report-${reportId}`] || "Reviewed by Admin moderation team",
        suspend_product: suspend,
      }),
    });
    if (!response.ok) {
      setError("Product report could not be updated.");
      return;
    }
    setMessage(`Report marked ${decision}${suspend ? " and product suspended" : ""}.`);
    await loadAdminData();
  }

  const openReportsCount = productReports.filter((r) => r.status === "open").length;
  const adminStats = adminData?.statistics;
  const ops = overview?.operations;

  const navItems: SidebarItem[] = [
    { label: "Operations Dashboard", href: "#overview", icon: "grid" },
    {
      label: "Seller Approvals",
      href: "#sellers",
      icon: "store",
      badge: sellerQueue.length ? String(sellerQueue.length) : undefined,
    },
    {
      label: "Product Approvals",
      href: "#products",
      icon: "box",
      badge: productQueue.length ? String(productQueue.length) : undefined,
    },
    {
      label: "Product Reports",
      href: "#reports",
      icon: "alert",
      badge: openReportsCount ? String(openReportsCount) : undefined,
    },
  ];

  const productStatusBars = Object.entries(ops?.products_by_status ?? {}).map(([label, value]) => ({
    label,
    value: Number(value),
    tone: (label === "published" ? "success" : label === "pending_approval" ? "gold" : "navy") as
      | "success"
      | "gold"
      | "navy",
  }));

  return (
    <PortalShell
      portalLabel="admin.shoplex.com"
      portalRole="admin portal"
      title="Admin Operations & Moderation Center"
      subtitle="Operational assistant console for dual seller/product approvals, product reports, and catalog moderation."
      breadcrumbs={[
        { label: "SHOPLEX", href: "/" },
        { label: "admin.shoplex.com", href: "/" },
        { label: navItems.find((i) => i.href === activeTab)?.label ?? "Operations Dashboard" },
      ]}
      navItems={navItems}
      activeHref={activeTab}
      onSelectNav={setActiveTab}
      userEmail={user?.email}
      userName={user ? `${user.first_name} ${user.last_name}`.trim() : undefined}
      notifications={notifications}
      onSignOut={() => void logout()}
      headerActions={
        <>
          <StatusPill tone={health ? "success" : "neutral"}>
            {health ? `API ${health.api_version}` : "API standby"}
          </StatusPill>
          <a className="topbar__link" href="http://localhost:8000/api/docs/" target="_blank" rel="noreferrer">
            Swagger ↗
          </a>
        </>
      }
    >
      {message && (
        <div style={{ marginBottom: 18 }}>
          <Notification title="Action completed" tone="success">
            {message}
          </Notification>
        </div>
      )}
      {error && (
        <div style={{ marginBottom: 18 }}>
          <Notification title="Action could not be completed" tone="danger">
            {error}
          </Notification>
        </div>
      )}

      {!user && (
        <Card className="surface" style={{ marginBottom: 24 }}>
          <CardHeader
            title="Sign in to Admin Operations & Moderation Center"
            subtitle="All administrative endpoints enforce strict server-side role and permission boundaries."
            action={
              <Button variant="primary" onClick={() => window.location.assign("/login")}>
                Sign in to Admin portal ↗
              </Button>
            }
          />
          <CardBody>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <p style={{ margin: "0 0 6px", fontSize: 13, color: "var(--ink)" }}>
                  <strong>Demo Account Ready:</strong> <code>admin@shoplex.local</code> · Password:{" "}
                  <code>Shoplex-Demo-2026!</code>
                </p>
                <p style={{ margin: 0, fontSize: 12, color: "var(--slate)" }}>
                  Admin has operational access to dual approvals and product moderation; financial ledgers and owner settings are strictly blocked by backend guards.
                </p>
              </div>
              <Badge tone="gold">Server RBAC Enforced</Badge>
            </div>
          </CardBody>
        </Card>
      )}

      {loading && <LoadingState label="Synchronizing Admin moderation queues…" />}

      <div className="lx-stat-grid">
        <StatCard
          tone="navy"
          label="Pending Seller Applications"
          value={adminStats ? adminStats.pending_seller_applications : sellerQueue.length}
          meta="Requires Admin + Owner approval"
          icon="store"
        />
        <StatCard
          tone="gold"
          label="Pending Product Approvals"
          value={adminStats ? adminStats.pending_product_approvals : productQueue.length}
          meta="Dual-review publication gate"
          icon="box"
        />
        <StatCard
          label="Approved & Rejected"
          value={adminStats ? `${adminStats.approved_products} / ${adminStats.rejected_products}` : "—"}
          meta={adminStats ? `${adminStats.suspended_products} suspended products` : "Catalog decisions"}
          icon="check"
        />
        <StatCard
          label="Product Reports"
          value={adminStats ? adminStats.open_product_reports : openReportsCount}
          meta="Open customer moderation flags"
          icon="alert"
        />
      </div>

      {activeTab === "#overview" && (
        <div className="lx-grid-2">
          <Card>
            <CardHeader
              title="Catalog Moderation Breakdown"
              subtitle="Product counts across approval and publication lifecycle states"
              action={<Badge tone="navy">Admin Operations</Badge>}
            />
            <CardBody>
              {productStatusBars.length ? (
                <BarChart items={productStatusBars} />
              ) : (
                <EmptyState title="Sign in as Admin to inspect moderation statistics" />
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Recent Approval Activities"
              subtitle="Independent Admin and Owner review decisions"
            />
            <CardBody>
              {adminData?.recent_approval_activities?.length ? (
                <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 10, fontSize: 12 }}>
                  {adminData.recent_approval_activities.slice(0, 6).map((act: any, idx: number) => (
                    <li
                      key={idx}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        paddingBottom: 8,
                        borderBottom: "1px solid var(--line)",
                      }}
                    >
                      <div>
                        <strong>{act.target}</strong>
                        <span style={{ display: "block", fontSize: 11, color: "var(--slate)" }}>
                          {act.type.replaceAll("_", " ")} · Cycle #{act.cycle} · {act.reviewer_role}
                        </span>
                      </div>
                      <StatusPill
                        tone={
                          act.decision === "approved"
                            ? "success"
                            : act.decision === "rejected"
                              ? "danger"
                              : "warning"
                        }
                      >
                        {act.decision.replaceAll("_", " ")}
                      </StatusPill>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState title="No recent approval decisions yet" />
              )}
            </CardBody>
          </Card>
        </div>
      )}

      {(activeTab === "#overview" || activeTab === "#sellers") && (
        <Card style={{ marginBottom: 24 }}>
          <CardHeader
            title="Seller Onboarding & Dual-Approval Queue"
            subtitle="Every seller application is submitted independently to Admin and Owner. Activation requires BOTH approvals."
            action={<StatusPill tone="warning">{sellerQueue.length} pending</StatusPill>}
          />
          <CardBody>
            {sellerQueue.length ? (
              <div style={{ display: "grid", gap: 14 }}>
                {sellerQueue.map((app) => (
                  <article
                    key={app.id}
                    style={{
                      padding: 18,
                      border: "1px solid var(--line)",
                      borderRadius: "var(--radius-sm)",
                      display: "grid",
                      gap: 12,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
                      <div>
                        <strong style={{ fontSize: 16 }}>{app.business_name}</strong>
                        <span style={{ marginLeft: 10, fontSize: 12, color: "var(--slate)" }}>
                          {app.business_type} · Cycle #{app.review_cycle} · Ref: {app.verification_reference || "N/A"}
                        </span>
                      </div>
                      <StatusPill tone={app.status === "pending" ? "warning" : "info"}>
                        {app.status.replaceAll("_", " ")}
                      </StatusPill>
                    </div>
                    <p style={{ margin: 0, fontSize: 12, color: "var(--slate)" }}>{app.business_address}</p>
                    {app.documents?.length > 0 && (
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--slate)" }}>Verification Documents:</span>
                        {app.documents.map((doc: any) => (
                          <Button
                            key={doc.id}
                            size="sm"
                            variant="secondary"
                            onClick={() => void downloadSellerDocument(app.id, doc.id, doc.original_name)}
                          >
                            Download {doc.original_name}
                          </Button>
                        ))}
                      </div>
                    )}
                    {app.approvals?.length > 0 && (
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        {app.approvals.map((a: any, idx: number) => (
                          <Badge key={idx} tone="indigo">
                            {a.reviewer_role} ({a.reviewer_name || "Reviewer"}): {a.decision}
                            {a.reason ? ` — "${a.reason}"` : ""}
                          </Badge>
                        ))}
                      </div>
                    )}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
                      <input
                        className="field__input"
                        style={{ maxWidth: 320, minHeight: 38 }}
                        placeholder="Rejection or required info reason…"
                        value={reviewNote[`seller-${app.id}`] ?? ""}
                        onChange={(e) => setReviewNote({ ...reviewNote, [`seller-${app.id}`]: e.target.value })}
                      />
                      <Button size="sm" onClick={() => void decideSeller(app.id, "approved")}>
                        Approve (Admin)
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => void decideSeller(app.id, "needs_info")}>
                        Request Info
                      </Button>
                      <Button size="sm" variant="danger" onClick={() => void decideSeller(app.id, "rejected")}>
                        Reject
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState title="No seller applications waiting for review">
                New merchant onboarding submissions appear here for independent Admin and Owner verification.
              </EmptyState>
            )}
          </CardBody>
        </Card>
      )}

      {(activeTab === "#overview" || activeTab === "#products") && (
        <Card style={{ marginBottom: 24 }}>
          <CardHeader
            title="Product Publication Dual-Approval Queue"
            subtitle="Submitted seller products require independent Admin AND Owner approval before appearing on the storefront."
            action={<StatusPill tone="info">{productQueue.length} awaiting review</StatusPill>}
          />
          <CardBody>
            {productQueue.length ? (
              <div style={{ display: "grid", gap: 14 }}>
                {productQueue.map((prod) => (
                  <article
                    key={prod.id}
                    style={{
                      padding: 18,
                      border: "1px solid var(--line)",
                      borderRadius: "var(--radius-sm)",
                      display: "grid",
                      gap: 10,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
                      <div>
                        <strong style={{ fontSize: 16 }}>{prod.name}</strong>
                        <span style={{ marginLeft: 10, fontSize: 12, color: "var(--slate)" }}>
                          by {prod.seller?.business_name} · {prod.category?.name} · {money(prod.price)}
                        </span>
                      </div>
                      <Badge tone="gold">Cycle v{prod.approval_version}</Badge>
                    </div>
                    <p style={{ margin: 0, fontSize: 12, color: "var(--slate)" }}>{prod.description}</p>
                    {prod.approval_history?.length > 0 && (
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        {prod.approval_history.map((h: any, idx: number) => (
                          <Badge key={idx} tone="slate">
                            {h.reviewer_role}: {h.decision} (v{h.version})
                            {h.reason ? ` — "${h.reason}"` : ""}
                          </Badge>
                        ))}
                      </div>
                    )}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
                      <input
                        className="field__input"
                        style={{ maxWidth: 320, minHeight: 38 }}
                        placeholder="Moderation note…"
                        value={reviewNote[`product-${prod.id}`] ?? ""}
                        onChange={(e) => setReviewNote({ ...reviewNote, [`product-${prod.id}`]: e.target.value })}
                      />
                      <Button size="sm" onClick={() => void decideProduct(prod.id, "approved")}>
                        Approve (Admin)
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => void decideProduct(prod.id, "changes_requested")}>
                        Request Changes
                      </Button>
                      <Button size="sm" variant="danger" onClick={() => void decideProduct(prod.id, "rejected")}>
                        Reject
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState title="Product moderation queue is clear">
                When sellers submit draft products for publication, they appear here for dual review.
              </EmptyState>
            )}
          </CardBody>
        </Card>
      )}

      {activeTab === "#products" && (
        <Card style={{ marginBottom: 24 }}>
          <CardHeader
            title="Catalog Moderation & Product Suspension"
            subtitle="Suspend inappropriate products immediately; restoration is reserved for the platform Owner."
          />
          <CardBody>
            {adminData?.moderation_products?.length ? (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Seller</th>
                      <th>Category</th>
                      <th>Price</th>
                      <th>Status</th>
                      <th>Moderation Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {adminData.moderation_products.map((prod: any) => (
                      <tr key={prod.id}>
                        <td>
                          <strong>{prod.name}</strong>
                          <span style={{ display: "block", fontSize: 11, color: "var(--slate)" }}>SKU: {prod.sku || "—"}</span>
                        </td>
                        <td>{prod.seller_name}</td>
                        <td>{prod.category_name}</td>
                        <td>{money(prod.price)}</td>
                        <td>
                          <StatusPill
                            tone={
                              prod.status === "published"
                                ? "success"
                                : prod.status === "suspended" || prod.status === "rejected"
                                  ? "danger"
                                  : "warning"
                            }
                          >
                            {prod.status.replaceAll("_", " ")}
                          </StatusPill>
                        </td>
                        <td>
                          {prod.status !== "suspended" ? (
                            <Button size="sm" variant="danger" onClick={() => void suspendProduct(prod.id)}>
                              Suspend
                            </Button>
                          ) : (
                            <span style={{ fontSize: 11, color: "var(--slate)" }}>Owner restore only</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState title="No products in catalog" />
            )}
          </CardBody>
        </Card>
      )}

      {(activeTab === "#reports" || activeTab === "#products") && (
        <Card style={{ marginBottom: 24 }}>
          <CardHeader
            title="Product-Related Reports & Compliance Queue"
            subtitle="Review customer-submitted product flags, record resolution notes, or suspend violating listings"
            action={<StatusPill tone={openReportsCount ? "danger" : "success"}>{openReportsCount} open</StatusPill>}
          />
          <CardBody>
            {productReports.length ? (
              <div style={{ display: "grid", gap: 12 }}>
                {productReports.map((rep) => (
                  <article
                    key={rep.id}
                    style={{
                      padding: 16,
                      border: "1px solid var(--line)",
                      borderRadius: "var(--radius-sm)",
                      display: "grid",
                      gap: 8,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <strong>{rep.product_name}</strong>
                        <span style={{ marginLeft: 10, fontSize: 12, color: "var(--slate)" }}>
                          Seller: {rep.seller_name} · Reported by: {rep.reporter_email}
                        </span>
                      </div>
                      <StatusPill
                        tone={rep.status === "open" ? "danger" : rep.status === "resolved" ? "success" : "neutral"}
                      >
                        {rep.status}
                      </StatusPill>
                    </div>
                    <p style={{ margin: 0, fontSize: 13 }}>
                      <strong>Reason:</strong> {rep.reason} {rep.details ? `— ${rep.details}` : ""}
                    </p>
                    {rep.status === "open" && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", marginTop: 4 }}>
                        <input
                          className="field__input"
                          style={{ maxWidth: 280, minHeight: 36 }}
                          placeholder="Resolution note…"
                          value={reviewNote[`report-${rep.id}`] ?? ""}
                          onChange={(e) => setReviewNote({ ...reviewNote, [`report-${rep.id}`]: e.target.value })}
                        />
                        <Button size="sm" onClick={() => void resolveReport(rep.id, "resolved", false)}>
                          Resolve
                        </Button>
                        <Button size="sm" variant="danger" onClick={() => void resolveReport(rep.id, "resolved", true)}>
                          Resolve &amp; Suspend Product
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => void resolveReport(rep.id, "dismissed", false)}>
                          Dismiss
                        </Button>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState title="No product reports filed">
                Flagged products appear here for Admin compliance review.
              </EmptyState>
            )}
          </CardBody>
        </Card>
      )}
    </PortalShell>
  );
}
