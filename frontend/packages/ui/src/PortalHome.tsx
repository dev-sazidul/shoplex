"use client";

import { useEffect, useState } from "react";
import type { ApiHealth, PortalRole } from "@shoplex/types";
import { Button, Card, ErrorState, LoadingState, StatusPill } from "./index";

const portalNames: Record<PortalRole, string> = {
  customer: "Customer marketplace",
  seller: "Seller workspace",
  admin: "Operations portal",
  manager: "Management portal",
  owner: "Owner console",
};

const portalDomains: Record<PortalRole, string> = {
  customer: "shoplex.com",
  seller: "seller.shoplex.com",
  admin: "admin.shoplex.com",
  manager: "manager.shoplex.com",
  owner: "owner.shoplex.com",
};

export function PortalHome({ role }: { role: PortalRole }) {
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
    fetch(`${apiBase}/health/`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("API unavailable");
        return response.json() as Promise<ApiHealth>;
      })
      .then(setHealth)
      .catch(() => setFailed(true));
  }, []);

  return (
    <main className="portal-page">
      <header className="topbar">
        <a className="wordmark" href="/" aria-label="SHOPLEX home">SHOP<span>LEX</span><i>.</i></a>
        <div className="topbar__right">
          <StatusPill tone={health ? "success" : failed ? "danger" : "neutral"}>
            {health ? "API connected" : failed ? "API unavailable" : "Connecting"}
          </StatusPill>
          <a className="topbar__link" href="http://localhost:8000/api/docs/" target="_blank" rel="noreferrer">API docs <span aria-hidden="true">↗</span></a>
        </div>
      </header>

      <section className="portal-hero">
        <div className="portal-hero__copy">
          <p className="eyebrow">{portalDomains[role]} <span aria-hidden="true">/</span> {role} access</p>
          <h1>{portalNames[role]}<span className="hero-period">.</span></h1>
          <p className="hero-lede">A considered foundation for a more connected marketplace. One Marketplace. Endless Opportunities.</p>
          <div className="hero-actions">
            <Button onClick={() => window.location.assign("/login")}>Sign in <span aria-hidden="true">↗</span></Button>
            <a className="text-link" href="http://localhost:8000/api/docs/" target="_blank" rel="noreferrer">Explore the API</a>
          </div>
        </div>
        <div className="brand-art" aria-hidden="true">
          <div className="brand-art__frame"><span>SHOPLEX</span><b>01</b><i /></div>
          <div className="brand-art__caption"><span>One platform</span><span>Five perspectives</span></div>
        </div>
      </section>

      <section className="foundation-strip" aria-label="Platform foundation">
        <Card className="foundation-card">
          <div className="foundation-card__head"><span className="foundation-card__index">01</span><span>Identity</span></div>
          <h2>One secure account layer</h2>
          <p>Central authentication, verified email, rotating tokens, and revocable sessions.</p>
        </Card>
        <Card className="foundation-card">
          <div className="foundation-card__head"><span className="foundation-card__index">02</span><span>Access</span></div>
          <h2>Permissions with boundaries</h2>
          <p>Server-enforced roles and user-level grants shared by all five portals.</p>
        </Card>
        <Card className="foundation-card foundation-card--status">
          <div className="foundation-card__head"><span className="foundation-card__index">03</span><span>Services</span></div>
          <h2>Central API status</h2>
          {health ? <p><StatusPill tone="success">{health.service} {health.api_version}</StatusPill></p> : failed ? <ErrorState title="Connection failed"><span>Start the Django API at localhost:8000 to see its live status.</span></ErrorState> : <LoadingState label="Checking backend" />}
        </Card>
      </section>

      <footer className="site-footer"><span>SHOPLEX <i>®</i></span><span>One Marketplace. Endless Opportunities.</span><span>Foundation / 2026</span></footer>
    </main>
  );
}
