"use client";

import type { PortalRole } from "@shoplex/types";
import { AdminPortal } from "./AdminPortal";
import { CustomerStorefront } from "./CustomerStorefront";
import { ManagerPortal } from "./ManagerPortal";
import { OwnerPortal } from "./OwnerPortal";
import { SellerPortalHome } from "./SellerPortal";

export function PortalHome({ role }: { role: PortalRole }) {
  switch (role) {
    case "admin":
      return <AdminPortal />;
    case "manager":
      return <ManagerPortal />;
    case "owner":
      return <OwnerPortal />;
    case "seller":
      return <SellerPortalHome />;
    case "customer":
      return <CustomerStorefront />;
  }
}
