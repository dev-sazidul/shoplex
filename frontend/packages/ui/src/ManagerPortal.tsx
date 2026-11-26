"use client";

import { useEffect, useState } from "react";
import type { ApiHealth } from "@shoplex/types";
import {
  AreaChart,
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

const permissionLabels: Record<string, string> = {
  "manager.analytics.business": "Business Analytics",
  "manager.reports.orders": "Order & Sales Reports",
  "manager.reports.finance": "Financial & Revenue Reports",
  "manager.reports.sellers": "Seller Performance Reports",
  "manager.reports.products": "Product Compliance Reports",
  "manager.admins.monitor": "Assigned Admin Monitoring",
  "manager.shares.read": "Share Ownership Summary",
  "manager.shares.documents": "Ownership Legal Documents",
};

function money(amount: string | number | undefined | null) {
  const num = Number(amount ?? 0);
  return `৳${num.toLocaleString("en-BD", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function ManagerPortal() {
  const { user, apiFetch, logout } = useSession();
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [activeTab, setActiveTab] = useState("#overview");
  const [managerData, setManagerData] = useState<any>(null);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

  useEffect(() => {
    fetch(`${apiBase}/health/`, { cache: "no-store" })
      .then((res) => (res.ok ? (res.json() as Promise<ApiHealth>) : null))
      .then(setHealth)
      .catch(() => setHealth(null));
  }, [apiBase]);

  async function loadManagerData() {
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
        apiFetch("/manager/dashboard/").then(async (res) => {
          if (res.ok) setManagerData(await res.json());
        }),
      ]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load Manager dashboard data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadManagerData();
  }, [user]);

  const navItems: SidebarItem[] = [
    { label: "Partner Overview", href: "#overview", icon: "grid" },
    { label: "Authorized Reports", href: "#reports", icon: "chart" },
    { label: "Assigned Admins", href: "#team", icon: "user" },
    { label: "Share Ownership", href: "#shares", icon: "sparkles" },
  ];

  const orderStatusBars = Object.entries(managerData?.order_reports?.orders_by_status ?? {}).map(
    ([label, value]) => ({
      label,
      value: Number(value),
      tone: (label === "completed" ? "success" : label === "processing" ? "gold" : "cobalt") as
        | "success"
        | "gold"
        | "cobalt",
    })
  );

  const managerOrderTrend = (managerData?.order_reports?.daily_orders ?? []).map(
    (row: { date: string; orders: number }) => ({
      label: row.date.slice(5),
      value: row.orders,
    })
  );

  const managerRevenueTrend = (managerData?.revenue_analytics?.daily_revenue ?? []).map(
    (row: { date: string; revenue: string }) => ({
      label: row.date.slice(5),
      value: Number(row.revenue),
    })
  );

  return (
    <PortalShell
      portalLabel="manager.shoplex.com"
      portalRole="manager portal"
      title="Partner & Operations Management Portal"
      subtitle="Executive partner dashboard for assigned responsibilities, authorized analytics, team monitoring, and share ownership."
      breadcrumbs={[
        { label: "SHOPLEX", href: "/" },
        { label: "manager.shoplex.com", href: "/" },
        { label: navItems.find((i) => i.href === activeTab)?.label ?? "Partner Overview" },
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
            title="Sign in to Partner & Operations Management Portal"
            subtitle="All partner, team monitoring, and share endpoints enforce strict server-side Owner permission checks."
            action={
              <Button variant="primary" onClick={() => window.location.assign("/login")}>
                Sign in to Manager portal ↗
              </Button>
            }
          />
          <CardBody>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <p style={{ margin: "0 0 6px", fontSize: 13, color: "var(--ink)" }}>
                  <strong>Demo Account Ready:</strong> <code>manager@shoplex.local</code> · Password:{" "}
                  <code>Shoplex-Demo-2026!</code>
                </p>
                <p style={{ margin: 0, fontSize: 12, color: "var(--slate)" }}>
                  Sign in to view your assigned responsibilities, authorized reports, assigned Admin team activity, and personal business share ownership.
                </p>
              </div>
              <Badge tone="gold">Server RBAC Enforced</Badge>
            </div>
          </CardBody>
        </Card>
      )}

      {loading && <LoadingState label="Synchronizing Manager portal telemetry…" />}

      {managerData?.profile && (
        <Card style={{ marginBottom: 24 }}>
          <CardHeader
            title={`${managerData.profile.name} · ${managerData.profile.title}`}
            subtitle={`Business Unit: ${managerData.profile.business_unit} · Only Owner-authorized modules are visible`}
            action={<Badge tone="gold">Authorized Partner</Badge>}
          />
          <CardBody>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--slate)" }}>Assigned Responsibilities:</span>
              {(managerData.profile.responsibilities?.length
                ? managerData.profile.responsibilities
                : ["Regional Operations", "Admin Team Supervision"]
              ).map((item: string, idx: number) => (
                <Badge key={idx} tone="navy">
                  {item}
                </Badge>
              ))}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {Object.entries(managerData.permissions ?? {}).map(([key, granted]) => (
                <StatusPill key={key} tone={granted ? "success" : "neutral"}>
                  {permissionLabels[key] ?? key}: {granted ? "Granted" : "Restricted"}
                </StatusPill>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      <div className="lx-stat-grid">
        <StatCard
          tone="navy"
          label="Share Ownership Stake"
          value={
            managerData?.share_ownership
              ? `${managerData.share_ownership.total_ownership_percentage}%`
              : "Restricted"
          }
          meta={
            managerData?.share_ownership
              ? `${managerData.share_ownership.total_allocated_shares.toLocaleString()} allocated shares`
              : "Requires manager.shares.read"
          }
          icon="sparkles"
        />
        <StatCard
          tone="gold"
          label="Assigned Admins"
          value={managerData?.assigned_admins ? managerData.assigned_admins.length : "—"}
          meta={
            managerData?.team_activity
              ? `${managerData.team_activity.length} recent team decisions`
              : "Team supervision"
          }
          icon="user"
        />
        <StatCard
          label="Marketplace Orders"
          value={managerData?.business_overview ? managerData.business_overview.total_orders : "—"}
          meta={
            managerData?.business_overview
              ? `${managerData.business_overview.completed_orders} completed orders`
              : "Requires manager.analytics.business"
          }
          icon="orders"
        />
        <StatCard
          label="Active Stores & Catalog"
          value={
            managerData?.business_overview
              ? `${managerData.business_overview.active_sellers} / ${managerData.business_overview.published_products}`
              : "—"
          }
          meta="Verified sellers & published products"
          icon="store"
        />
      </div>

      {activeTab === "#overview" && (
        <div className="lx-grid-2">
          <Card>
            <CardHeader
              title="14-Day Order Velocity"
              subtitle="Authorized daily order volume across the marketplace"
              action={<Badge tone="cobalt">Order Reports</Badge>}
            />
            <CardBody>
              {managerOrderTrend.length ? (
                <AreaChart data={managerOrderTrend} valuePrefix="" />
              ) : (
                <EmptyState title="Order analytics require Owner authorization (manager.reports.orders)" />
              )}
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Fulfillment Pipeline" subtitle="Orders grouped by operational status" />
            <CardBody>
              {orderStatusBars.length ? (
                <BarChart items={orderStatusBars} />
              ) : (
                <EmptyState title="Sign in as Manager to view fulfillment distribution" />
              )}
            </CardBody>
          </Card>
        </div>
      )}

      {(activeTab === "#overview" || activeTab === "#reports") && (
        <div className="lx-grid-2">
          <Card>
            <CardHeader
              title="Authorized Revenue & Financial Analytics"
              subtitle="Controlled by Owner permission manager.reports.finance"
              action={
                <StatusPill tone={managerData?.revenue_analytics ? "success" : "warning"}>
                  {managerData?.revenue_analytics ? "Authorized" : "Owner Restricted"}
                </StatusPill>
              }
            />
            <CardBody>
              {managerData?.revenue_analytics ? (
                <div style={{ display: "grid", gap: 14 }}>
                  <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
                    <div>
                      <small style={{ color: "var(--slate)", fontSize: 11 }}>Gross Merchandise Value</small>
                      <div style={{ fontSize: 20, fontWeight: 700 }}>
                        {money(managerData.revenue_analytics.gross_merchandise_value)}
                      </div>
                    </div>
                    <div>
                      <small style={{ color: "var(--slate)", fontSize: 11 }}>Platform Commission</small>
                      <div style={{ fontSize: 20, fontWeight: 700 }}>
                        {money(managerData.revenue_analytics.platform_commission)}
                      </div>
                    </div>
                    <div>
                      <small style={{ color: "var(--slate)", fontSize: 11 }}>Average Order Value</small>
                      <div style={{ fontSize: 20, fontWeight: 700 }}>
                        {money(managerData.revenue_analytics.average_order_value)}
                      </div>
                    </div>
                  </div>
                  <AreaChart data={managerRevenueTrend} />
                </div>
              ) : (
                <EmptyState title="Financial analytics are currently restricted">
                  The platform Owner must explicitly grant manager.reports.finance to enable revenue visibility.
                </EmptyState>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Authorized Seller & Product Reports"
              subtitle="Scoped by manager.reports.sellers and manager.reports.products"
            />
            <CardBody>
              {managerData?.seller_reports ? (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Store</th>
                        <th>Published Products</th>
                        <th>Orders</th>
                      </tr>
                    </thead>
                    <tbody>
                      {managerData.seller_reports.map((s: any) => (
                        <tr key={s.id}>
                          <td><strong>{s.business_name}</strong></td>
                          <td>{s.published_products}</td>
                          <td>{s.orders_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="Seller performance reports require manager.reports.sellers">
                  Ask the platform Owner to grant seller or product report access if required for your role.
                </EmptyState>
              )}
            </CardBody>
          </Card>
        </div>
      )}

      {(activeTab === "#overview" || activeTab === "#team") && (
        <div className="lx-grid-2">
          <Card>
            <CardHeader
              title="Assigned Admin Accounts"
              subtitle="You can monitor only Admin accounts explicitly assigned to you by the Owner"
              action={<Badge tone="navy">{managerData?.assigned_admins?.length ?? 0} assigned</Badge>}
            />
            <CardBody>
              {managerData?.assigned_admins?.length ? (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Admin</th>
                        <th>Assigned Responsibilities</th>
                        <th>Assigned Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {managerData.assigned_admins.map((a: any) => (
                        <tr key={a.assignment_id}>
                          <td>
                            <strong>{a.name}</strong>
                            <span style={{ display: "block", fontSize: 11, color: "var(--slate)" }}>{a.email}</span>
                          </td>
                          <td>{a.responsibilities}</td>
                          <td>{new Date(a.assigned_at).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="No Admin accounts currently assigned to your team" />
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Assigned Team Moderation Activity"
              subtitle="Recent seller and product review decisions by your assigned Admins"
            />
            <CardBody>
              {managerData?.team_activity?.length ? (
                <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 10, fontSize: 12 }}>
                  {managerData.team_activity.map((act: any, idx: number) => (
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
                          {act.type.replaceAll("_", " ")} by {act.admin_email}
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
                        {act.decision}
                      </StatusPill>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState title="No recent moderation decisions from assigned Admins" />
              )}
            </CardBody>
          </Card>
        </div>
      )}

      {(activeTab === "#overview" || activeTab === "#shares") && (
        <Card style={{ marginBottom: 24 }}>
          <CardHeader
            title="Authorized Business Share Ownership & Legal Records"
            subtitle="Internal ownership record-management view scoped strictly to your partner account"
            action={
              <Badge tone="gold">
                {managerData?.share_ownership
                  ? `${managerData.share_ownership.total_ownership_percentage}% Allocated`
                  : "Restricted"}
              </Badge>
            }
          />
          <CardBody>
            {managerData?.share_ownership ? (
              <div style={{ display: "grid", gap: 18 }}>
                {managerData.share_ownership.allocations?.length ? (
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Share Plan</th>
                          <th>Allocated Shares</th>
                          <th>Ownership %</th>
                          <th>Company Valuation</th>
                          <th>Implied Value</th>
                          <th>Allocated Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {managerData.share_ownership.allocations.map((a: any) => (
                          <tr key={a.id}>
                            <td><strong>{a.plan_name}</strong></td>
                            <td>{a.allocated_shares.toLocaleString()}</td>
                            <td><Badge tone="gold">{a.ownership_percentage}%</Badge></td>
                            <td>{money(a.company_valuation)}</td>
                            <td><strong>{money(a.implied_value)}</strong></td>
                            <td>{new Date(a.allocated_at).toLocaleDateString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <EmptyState title="No active share allocations recorded for your account" />
                )}

                {managerData.share_ownership.documents?.length > 0 && (
                  <div>
                    <h4 style={{ margin: "0 0 10px", fontSize: 13 }}>Authorized Ownership Legal Documents</h4>
                    <div style={{ display: "grid", gap: 8 }}>
                      {managerData.share_ownership.documents.map((doc: any) => (
                        <div
                          key={doc.id}
                          style={{
                            padding: 12,
                            border: "1px solid var(--line)",
                            borderRadius: "var(--radius-sm)",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                          }}
                        >
                          <div>
                            <strong>{doc.title}</strong>
                            <span style={{ display: "block", fontSize: 11, color: "var(--slate)" }}>
                              {doc.plan_name} · {doc.document_type.replaceAll("_", " ")} · Ref: {doc.reference_number}
                            </span>
                          </div>
                          <Badge tone="navy">Verified Record</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <p style={{ margin: 0, fontSize: 11, color: "var(--slate)" }}>
                  Compliance notice: This internal record tracks authorized partner equity allocations. Actual legal ownership transfers and dividend distributions require executed legal documentation under applicable corporate law.
                </p>
              </div>
            ) : (
              <EmptyState title="Share ownership visibility requires manager.shares.read permission" />
            )}
          </CardBody>
        </Card>
      )}
    </PortalShell>
  );
}
