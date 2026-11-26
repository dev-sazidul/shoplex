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
  SelectInput,
  StatCard,
  StatusPill,
  TextInput,
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

const adminStaffPermissionLabels: Record<string, string> = {
  "admin.products.create": "1. Product Creation",
  "admin.products.edit": "2. Product Editing",
  "admin.products.delete": "3. Product Deletion",
  "admin.products.publish": "4. Product Publishing",
  "admin.products.approve": "5. Product Approval",
  "admin.sellers.manage": "6. Seller Management",
  "admin.customers.manage": "7. Customer Management",
  "admin.orders.manage": "8. Order Management",
  "admin.suppliers.manage": "9. Supplier Management",
  "admin.suppliers.import": "10. Supplier Product Importing",
  "admin.coupons.manage": "11. Coupon & Promotion Management",
  "admin.shipping.manage": "12. Shipping Management",
  "admin.support.manage": "13. Customer Support",
  "admin.reports.analytics": "14. Reports & Analytics",
  "admin.refunds.process": "15. Refund Processing",
  "admin.finance.reports": "16. Selected Financial Report Access",
};

function money(amount: string | number | undefined | null) {
  const num = Number(amount ?? 0);
  return `৳${num.toLocaleString("en-BD", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function OwnerPortal() {
  const { user, apiFetch, logout } = useSession();
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [activeTab, setActiveTab] = useState("#overview");
  const [adminData, setAdminData] = useState<any>(null);
  const [ownerData, setOwnerData] = useState<any>(null);
  const [sellerQueue, setSellerQueue] = useState<any[]>([]);
  const [productQueue, setProductQueue] = useState<any[]>([]);
  const [productReports, setProductReports] = useState<any[]>([]);
  const [allSellers, setAllSellers] = useState<any[]>([]);
  const [payoutQueue, setPayoutQueue] = useState<any[]>([]);
  const [ledgerData, setLedgerData] = useState<any>(null);
  const [reconciliation, setReconciliation] = useState<any>(null);
  const [commissions, setCommissions] = useState<any[]>([]);
  const [shippingRules, setShippingRules] = useState<any[]>([]);
  const [platformSettings, setPlatformSettings] = useState<any>(null);
  const [securityData, setSecurityData] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [managerGov, setManagerGov] = useState<any>(null);
  const [adminAssignData, setAdminAssignData] = useState<any>(null);
  const [adminStaffData, setAdminStaffData] = useState<any>(null);
  const [platformProducts, setPlatformProducts] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [sharePlans, setSharePlans] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [reviewNote, setReviewNote] = useState<Record<string, string>>({});

  // Admin Staff & Platform Product forms
  const [admEmail, setAdmEmail] = useState("");
  const [admFirst, setAdmFirst] = useState("");
  const [admLast, setAdmLast] = useState("");
  const [admPassword, setAdmPassword] = useState("");
  const [pltName, setPltName] = useState("");
  const [pltDesc, setPltDesc] = useState("");
  const [pltCategory, setPltCategory] = useState("");
  const [pltPrice, setPltPrice] = useState("");
  const [pltStock, setPltStock] = useState("25");
  const [pltSource, setPltSource] = useState<"owner_platform" | "supplier">("owner_platform");
  const [pltSupplier, setPltSupplier] = useState("");

  // Financial & taxonomy forms
  const [newCommission, setNewCommission] = useState("10.00");
  const [newShipCountry, setNewShipCountry] = useState("BD");
  const [newShipAmount, setNewShipAmount] = useState("60.00");
  const [expenseType, setExpenseType] = useState("operational_expense");
  const [expenseAmount, setExpenseAmount] = useState("");
  const [expenseDesc, setExpenseDesc] = useState("");
  const [catName, setCatName] = useState("");
  const [catDesc, setCatDesc] = useState("");
  const [brandName, setBrandName] = useState("");
  const [brandDesc, setBrandDesc] = useState("");
  const [mfaDeviceName, setMfaDeviceName] = useState("Owner Authenticator");
  const [securityPassword, setSecurityPassword] = useState("");
  const [auditFilter, setAuditFilter] = useState("");

  // Manager & Admin assignment forms
  const [mgrEmail, setMgrEmail] = useState("");
  const [mgrFirst, setMgrFirst] = useState("");
  const [mgrLast, setMgrLast] = useState("");
  const [mgrTitle, setMgrTitle] = useState("Regional Operations Manager");
  const [mgrUnit, setMgrUnit] = useState("Dhaka Division");
  const [mgrResp, setMgrResp] = useState("Catalog Oversight, SLA Compliance");
  const [mgrPassword, setMgrPassword] = useState("");
  const [assignAdminId, setAssignAdminId] = useState("");
  const [assignManagerId, setAssignManagerId] = useState("");
  const [assignResp, setAssignResp] = useState("Seller & Product Dual Approvals");

  // Business Share forms
  const [planName, setPlanName] = useState("SHOPLEX Partner Equity Plan");
  const [planShares, setPlanShares] = useState("100000");
  const [planMaxPct, setPlanMaxPct] = useState("35.00");
  const [planValuation, setPlanValuation] = useState("100000000.00");
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [allocEmail, setAllocEmail] = useState("manager@shoplex.local");
  const [allocPct, setAllocPct] = useState("5.00");
  const [allocRef, setAllocRef] = useState("DEED-2026-101");
  const [offerEmail, setOfferEmail] = useState("manager@shoplex.local");
  const [offerPct, setOfferPct] = useState("2.50");
  const [offerNote, setOfferNote] = useState("Annual leadership performance grant");
  const [transferAllocId, setTransferAllocId] = useState("");
  const [transferToEmail, setTransferToEmail] = useState("");
  const [transferPct, setTransferPct] = useState("1.00");
  const [transferRef, setTransferRef] = useState("TRANSFER-2026-201");
  const [docTitle, setDocTitle] = useState("");
  const [docHolderEmail, setDocHolderEmail] = useState("manager@shoplex.local");
  const [docType, setDocType] = useState("certificate");
  const [docRef, setDocRef] = useState("CERT-2026-001");

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

  async function loadOwnerData() {
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
        apiFetch("/owner/dashboard/").then(async (res) => {
          if (res.ok) setOwnerData(await res.json());
        }),
        apiFetch("/owner/sellers/").then(async (res) => {
          if (res.ok) setAllSellers(await res.json());
        }),
        apiFetch("/owner/payouts/").then(async (res) => {
          if (res.ok) setPayoutQueue(await res.json());
        }),
        apiFetch("/owner/finance/ledger/").then(async (res) => {
          if (res.ok) setLedgerData(await res.json());
        }),
        apiFetch("/owner/payments/reconciliation/").then(async (res) => {
          if (res.ok) setReconciliation(await res.json());
        }),
        apiFetch("/management/commission-rules/").then(async (res) => {
          if (res.ok) {
            const data = await res.json();
            setCommissions(data.results ?? data);
          }
        }),
        apiFetch("/management/shipping-rules/").then(async (res) => {
          if (res.ok) {
            const data = await res.json();
            setShippingRules(data.results ?? data);
          }
        }),
        apiFetch("/owner/settings/").then(async (res) => {
          if (res.ok) setPlatformSettings(await res.json());
        }),
        apiFetch("/owner/security/").then(async (res) => {
          if (res.ok) setSecurityData(await res.json());
        }),
        apiFetch("/owner/audit-logs/").then(async (res) => {
          if (res.ok) setAuditLogs(await res.json());
        }),
        apiFetch("/owner/managers/").then(async (res) => {
          if (res.ok) setManagerGov(await res.json());
        }),
        apiFetch("/owner/admin-assignments/").then(async (res) => {
          if (res.ok) setAdminAssignData(await res.json());
        }),
        apiFetch("/owner/admins/").then(async (res) => {
          if (res.ok) setAdminStaffData(await res.json());
        }),
        apiFetch("/admin-staff/products/").then(async (res) => {
          if (res.ok) {
            const data = await res.json();
            setPlatformProducts(data.products ?? []);
          }
        }),
        apiFetch("/categories/").then(async (res) => {
          if (res.ok) {
            const data = await res.json();
            const list = data.results ?? data;
            setCategories(list);
            if (list[0]?.slug && !pltCategory) setPltCategory(list[0].slug);
          }
        }),
        apiFetch("/owner/shares/plans/").then(async (res) => {
          if (res.ok) {
            const plans = await res.json();
            setSharePlans(plans);
            if (plans[0] && !selectedPlanId) setSelectedPlanId(plans[0].id);
          }
        }),
      ]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load Owner Executive Control Center data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadOwnerData();
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
    setMessage(`Seller application #${applicationId} decision (${decision.replaceAll("_", " ")}) recorded independently for Owner.`);
    await loadOwnerData();
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
    setMessage(`Product "${data.name}" decision (${decision.replaceAll("_", " ")}) recorded independently for Owner.`);
    await loadOwnerData();
  }

  async function changeProductStatus(productId: string, action: "suspend" | "restore") {
    setError("");
    setMessage("");
    const response = await apiFetch(`/management/products/${productId}/status/`, {
      method: "POST",
      body: JSON.stringify({ action, reason: reviewNote[`mod-${productId}`] || "Owner governance action" }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? "Product status could not be updated.");
      return;
    }
    setMessage(`Product "${data.name}" is now ${data.status}.`);
    await loadOwnerData();
  }

  async function resolveReport(reportId: string, decision: "resolved" | "dismissed", suspendProduct = false) {
    setError("");
    setMessage("");
    const response = await apiFetch(`/management/product-reports/${reportId}/resolve/`, {
      method: "POST",
      body: JSON.stringify({
        status: decision,
        resolution_note: reviewNote[`report-${reportId}`] || "Reviewed by Owner",
        suspend_product: suspendProduct,
      }),
    });
    if (!response.ok) {
      setError("Product report could not be updated.");
      return;
    }
    setMessage(`Report marked ${decision}${suspendProduct ? " and product suspended" : ""}.`);
    await loadOwnerData();
  }

  async function changeSellerStatus(sellerId: number, action: "suspend" | "reactivate") {
    setError("");
    setMessage("");
    const response = await apiFetch(`/owner/sellers/${sellerId}/status/`, {
      method: "POST",
      body: JSON.stringify({ action, reason: reviewNote[`seller-status-${sellerId}`] || "Executive governance action" }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? "Seller status could not be changed.");
      return;
    }
    setMessage(`Seller "${data.business_name}" ${action}d.`);
    await loadOwnerData();
  }

  async function decidePayout(payoutId: string, decision: "approved" | "paid" | "rejected") {
    setError("");
    setMessage("");
    const response = await apiFetch(`/owner/payouts/${payoutId}/decision/`, {
      method: "POST",
      body: JSON.stringify({ decision, reason: reviewNote[`payout-${payoutId}`] || `Marked ${decision} by Owner` }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? "Payout decision could not be recorded.");
      return;
    }
    setMessage(`Payout for ${data.seller_name} (${data.amount}) marked as ${data.status}.`);
    await loadOwnerData();
  }

  async function recordLedgerEntry(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const response = await apiFetch("/owner/finance/ledger/", {
      method: "POST",
      body: JSON.stringify({
        transaction_type: expenseType,
        amount: expenseAmount,
        description: expenseDesc,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? "Ledger entry could not be recorded.");
      return;
    }
    setExpenseAmount("");
    setExpenseDesc("");
    setMessage(`Immutable ledger entry ${data.reference_id} (${data.amount}) posted.`);
    await loadOwnerData();
  }

  async function createCommissionRule(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const response = await apiFetch("/management/commission-rules/", {
      method: "POST",
      body: JSON.stringify({ percentage: newCommission, is_active: true }),
    });
    if (!response.ok) {
      setError("Commission rule could not be saved.");
      return;
    }
    setMessage("Commission rule created.");
    await loadOwnerData();
  }

  async function createShippingRule(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const response = await apiFetch("/management/shipping-rules/", {
      method: "POST",
      body: JSON.stringify({ country_code: newShipCountry.toUpperCase(), amount: newShipAmount, is_active: true }),
    });
    if (!response.ok) {
      setError("Shipping rule could not be saved.");
      return;
    }
    setMessage(`Shipping rule for ${newShipCountry.toUpperCase()} saved.`);
    await loadOwnerData();
  }

  async function saveCategory(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await apiFetch("/owner/categories/", {
      method: "POST",
      body: JSON.stringify({ name: catName, description: catDesc }),
    });
    if (!response.ok) {
      setError("Category could not be saved.");
      return;
    }
    setCatName("");
    setCatDesc("");
    setMessage("Category saved.");
    await loadOwnerData();
  }

  async function saveBrand(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await apiFetch("/owner/brands/", {
      method: "POST",
      body: JSON.stringify({ name: brandName, description: brandDesc }),
    });
    if (!response.ok) {
      setError("Brand could not be saved.");
      return;
    }
    setBrandName("");
    setBrandDesc("");
    setMessage("Brand saved.");
    await loadOwnerData();
  }

  async function savePlatformSettings(updatedSection: Record<string, unknown>) {
    setError("");
    setMessage("");
    const response = await apiFetch("/owner/settings/", {
      method: "PUT",
      body: JSON.stringify({ settings: updatedSection }),
    });
    if (!response.ok) {
      setError("Platform settings could not be updated.");
      return;
    }
    setPlatformSettings(await response.json());
    setMessage("Platform settings updated and recorded in the audit log.");
  }

  async function runOwnerSecurityAction(action: "enroll_mfa" | "reauthenticate") {
    setError("");
    setMessage("");
    const response = await apiFetch("/owner/security/", {
      method: "POST",
      body: JSON.stringify({ action, name: mfaDeviceName, password: securityPassword }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? "Security verification failed.");
      return;
    }
    setSecurityPassword("");
    setMessage(
      action === "enroll_mfa"
        ? `Mandatory Owner MFA device "${mfaDeviceName}" enrolled and verified.`
        : "Owner password reauthentication confirmed."
    );
    await loadOwnerData();
  }

  async function createManager(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const response = await apiFetch("/owner/managers/", {
      method: "POST",
      body: JSON.stringify({
        email: mgrEmail,
        first_name: mgrFirst,
        last_name: mgrLast,
        title: mgrTitle,
        business_unit: mgrUnit,
        responsibilities: mgrResp,
        password: mgrPassword,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? Object.values(data).flat().join(" ") ?? "Manager could not be created.");
      return;
    }
    setMgrEmail("");
    setMgrFirst("");
    setMgrLast("");
    setMgrPassword("");
    setMessage(`Manager account ${data.email} created and invitation recorded.`);
    await loadOwnerData();
  }

  async function updateManagerStatus(managerId: number, action: "activate" | "suspend" | "remove") {
    setError("");
    setMessage("");
    const response = await apiFetch(`/owner/managers/${managerId}/status/`, {
      method: "POST",
      body: JSON.stringify({ action, reason: `Owner ${action} action` }),
    });
    if (!response.ok) {
      setError("Manager status could not be changed.");
      return;
    }
    setMessage(`Manager #${managerId} ${action}d (sessions invalidated if access removed).`);
    await loadOwnerData();
  }

  async function toggleManagerPermission(managerId: number, permission: string, isGranted: boolean) {
    setError("");
    setMessage("");
    const response = await apiFetch(`/owner/managers/${managerId}/permissions/`, {
      method: "POST",
      body: JSON.stringify({ permission, is_granted: isGranted }),
    });
    if (!response.ok) {
      setError("Permission could not be updated.");
      return;
    }
    setMessage(`Permission "${permissionLabels[permission] ?? permission}" ${isGranted ? "granted" : "revoked"} immediately.`);
    await loadOwnerData();
  }

  async function createAdminStaff(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const response = await apiFetch("/owner/admins/", {
      method: "POST",
      body: JSON.stringify({
        email: admEmail,
        first_name: admFirst,
        last_name: admLast,
        password: admPassword,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? Object.values(data).flat().join(" ") ?? "Admin staff account could not be created.");
      return;
    }
    setAdmEmail("");
    setAdmFirst("");
    setAdmLast("");
    setAdmPassword("");
    setMessage(`Admin staff account ${data.email} created with 0 permissions granted by default.`);
    await loadOwnerData();
  }

  async function updateAdminStaffStatus(adminId: string, action: "activate" | "suspend" | "remove") {
    setError("");
    setMessage("");
    const response = await apiFetch(`/owner/admins/${adminId}/status/`, {
      method: "POST",
      body: JSON.stringify({ action, reason: `Owner ${action} action` }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? "Admin staff status could not be updated.");
      return;
    }
    setMessage(`Admin staff ${data.email} ${action}d (active sessions revoked if suspended or removed).`);
    await loadOwnerData();
  }

  async function toggleAdminStaffPermission(adminId: string, permission: string, isGranted: boolean) {
    setError("");
    setMessage("");
    const response = await apiFetch(`/owner/admins/${adminId}/permissions/`, {
      method: "POST",
      body: JSON.stringify({ permission, is_granted: isGranted }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? "Admin permission could not be updated.");
      return;
    }
    setMessage(
      `Admin permission "${adminStaffPermissionLabels[permission] ?? permission}" ${isGranted ? "granted" : "revoked"} immediately.`
    );
    await loadOwnerData();
  }

  async function createPlatformProduct(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const response = await apiFetch("/admin-staff/products/", {
      method: "POST",
      body: JSON.stringify({
        name: pltName,
        description: pltDesc,
        category: pltCategory,
        price: pltPrice,
        stock_quantity: Number(pltStock || 0),
        product_source: pltSource,
        supplier_name: pltSource === "supplier" ? pltSupplier : "",
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? Object.values(data).flat().join(" ") ?? "Platform product could not be created.");
      return;
    }
    setPltName("");
    setPltDesc("");
    setPltPrice("");
    setPltSupplier("");
    setMessage(`Platform-owned SHOPLEX product "${data.name}" created (owner: ${data.product_owner}, status: ${data.status}).`);
    await loadOwnerData();
  }

  async function publishPlatformProduct(productId: string) {
    setError("");
    setMessage("");
    const response = await apiFetch(`/admin-staff/products/${productId}/publish/`, {
      method: "POST",
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? "Platform product could not be published.");
      return;
    }
    setMessage(`Platform product "${data.name}" published directly by Owner.`);
    await loadOwnerData();
  }

  async function submitAdminAssignment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const response = await apiFetch("/owner/admin-assignments/", {
      method: "POST",
      body: JSON.stringify({
        action: "reassign",
        admin_id: assignAdminId,
        manager_id: Number(assignManagerId),
        responsibilities: assignResp,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? Object.values(data).flat().join(" ") ?? "Admin assignment failed.");
      return;
    }
    setAdminAssignData(data);
    setMessage("Admin assigned to Manager and recorded in assignment history.");
    await loadOwnerData();
  }

  async function removeAdminAssignment(adminId: string, managerId: number) {
    setError("");
    setMessage("");
    const response = await apiFetch("/owner/admin-assignments/", {
      method: "POST",
      body: JSON.stringify({ action: "remove", admin_id: adminId, manager_id: managerId }),
    });
    if (response.ok) {
      setAdminAssignData(await response.json());
      setMessage("Admin assignment removed.");
      await loadOwnerData();
    }
  }

  async function createSharePlan(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const response = await apiFetch("/owner/shares/plans/", {
      method: "POST",
      body: JSON.stringify({
        name: planName,
        total_authorized_shares: Number(planShares),
        max_allocated_percentage: planMaxPct,
        company_valuation: planValuation,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? Object.values(data).flat().join(" ") ?? "Share plan could not be saved.");
      return;
    }
    setSelectedPlanId(data.id);
    setMessage(`Share plan "${data.name}" saved at valuation ${data.company_valuation} BDT.`);
    await loadOwnerData();
  }

  async function createShareOffer(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const response = await apiFetch("/owner/shares/offers/", {
      method: "POST",
      body: JSON.stringify({
        plan_id: selectedPlanId,
        partner_email: offerEmail,
        offered_percentage: offerPct,
        terms_note: offerNote,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? Object.values(data).flat().join(" ") ?? "Share offer failed.");
      return;
    }
    setMessage(`Share offer of ${offerPct}% recorded for ${offerEmail}.`);
    await loadOwnerData();
  }

  async function createShareAllocation(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const response = await apiFetch("/owner/shares/allocations/", {
      method: "POST",
      body: JSON.stringify({
        plan_id: selectedPlanId,
        holder_email: allocEmail,
        ownership_percentage: allocPct,
        legal_reference: allocRef,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? Object.values(data).flat().join(" ") ?? "Share allocation failed.");
      return;
    }
    setMessage(`Allocated ${allocPct}% business ownership to ${allocEmail} (${allocRef}).`);
    await loadOwnerData();
  }

  async function createShareTransfer(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const response = await apiFetch("/owner/shares/transfers/", {
      method: "POST",
      body: JSON.stringify({
        allocation_id: transferAllocId,
        to_holder_email: transferToEmail,
        percentage: transferPct,
        legal_reference: transferRef,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? Object.values(data).flat().join(" ") ?? "Share transfer failed.");
      return;
    }
    setMessage(`Transferred ${transferPct}% to ${transferToEmail} (${transferRef}).`);
    await loadOwnerData();
  }

  async function createShareDocument(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const response = await apiFetch("/owner/shares/documents/", {
      method: "POST",
      body: JSON.stringify({
        plan_id: selectedPlanId,
        holder_email: docHolderEmail,
        title: docTitle,
        document_type: docType,
        reference_number: docRef,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail ?? Object.values(data).flat().join(" ") ?? "Document could not be recorded.");
      return;
    }
    setDocTitle("");
    setMessage(`Ownership document "${docRef}" recorded.`);
    await loadOwnerData();
  }

  const openReportsCount = productReports.filter((r) => r.status === "open").length;
  const pendingPayoutsCount = payoutQueue.filter((p) => p.status === "pending" || p.status === "approved").length;
  const ownerBiz = ownerData?.business_metrics;
  const ownerFin = ownerData?.financial_metrics;
  const activeSharePlan = sharePlans.find((p) => p.id === selectedPlanId) ?? sharePlans[0];

  const navItems: SidebarItem[] = [
    { label: "Executive Dashboard", href: "#overview", icon: "chart" },
    {
      label: "Seller Management",
      href: "#sellers",
      icon: "store",
      badge: sellerQueue.length ? String(sellerQueue.length) : undefined,
    },
    {
      label: "Product & Taxonomy",
      href: "#products",
      icon: "box",
      badge: productQueue.length ? String(productQueue.length) : undefined,
    },
    {
      label: "Finance & Ledger",
      href: "#finance",
      icon: "wallet",
      badge: pendingPayoutsCount ? String(pendingPayoutsCount) : undefined,
    },
    {
      label: "Admin Staff & Permissions",
      href: "#admins",
      icon: "shield",
      badge: adminStaffData?.admins?.length ? String(adminStaffData.admins.length) : undefined,
    },
    { label: "Managers & Admins", href: "#managers", icon: "user" },
    { label: "Business Shares", href: "#shares", icon: "sparkles" },
    { label: "Platform Settings", href: "#settings", icon: "settings" },
    { label: "Security & Audit", href: "#security", icon: "shield" },
  ];

  const dailySalesChart = (ownerData?.charts?.daily_sales ?? []).map(
    (row: { date: string; sales?: string; orders: number }) => ({
      label: row.date.slice(5),
      value: Number(row.sales ?? 0),
      secondary: row.orders,
    })
  );

  const monthlyRevenueBars = (ownerData?.charts?.monthly_revenue ?? []).map(
    (row: { month: string; revenue: string }) => ({
      label: row.month,
      value: Math.round(Number(row.revenue)),
      tone: "cobalt" as const,
    })
  );

  const yearlyRevenueBars = (ownerData?.charts?.yearly_revenue ?? []).map(
    (row: { year: string; revenue: string }) => ({
      label: row.year,
      value: Math.round(Number(row.revenue)),
      tone: "gold" as const,
    })
  );

  const orderStatusBars = Object.entries(ownerData?.charts?.orders_by_status ?? {}).map(([label, value]) => ({
    label,
    value: Number(value),
    tone: (label === "completed" ? "success" : label === "processing" ? "gold" : "cobalt") as
      | "success"
      | "gold"
      | "cobalt",
  }));

  return (
    <PortalShell
      portalLabel="owner.shoplex.com"
      portalRole="owner control"
      title="Owner Executive Control Center"
      subtitle="Highest-authority executive governance, immutable financial ledger, manager/admin delegation, share management, and security."
      breadcrumbs={[
        { label: "SHOPLEX", href: "/" },
        { label: "owner.shoplex.com", href: "/" },
        { label: navItems.find((i) => i.href === activeTab)?.label ?? "Executive Dashboard" },
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
            title="Sign in to Owner Executive Control Center"
            subtitle="All executive, financial ledger, manager delegation, and share endpoints require explicit Owner authorization."
            action={
              <Button variant="primary" onClick={() => window.location.assign("/login")}>
                Sign in to Owner portal ↗
              </Button>
            }
          />
          <CardBody>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <p style={{ margin: "0 0 6px", fontSize: 13, color: "var(--ink)" }}>
                  <strong>Demo Account Ready:</strong> <code>owner@shoplex.local</code> · Password:{" "}
                  <code>Shoplex-Demo-2026!</code>
                </p>
                <p style={{ margin: 0, fontSize: 12, color: "var(--slate)" }}>
                  Sign in to access live executive analytics, immutable financial ledgers, manager &amp; admin delegation, and business share management.
                </p>
              </div>
              <Badge tone="gold">Owner RBAC Enforced</Badge>
            </div>
          </CardBody>
        </Card>
      )}

      {loading && <LoadingState label="Synchronizing Owner Executive Control Center…" />}

      {activeTab === "#overview" && (
        <>
          <div className="lx-stat-grid">
            <StatCard
              tone="navy"
              label="Gross Sales (GMV)"
              value={ownerFin ? money(ownerFin.gross_sales) : "৳—"}
              meta={ownerBiz ? `${ownerBiz.total_orders} orders (${ownerBiz.completed_orders} completed)` : "Live ledger"}
              icon="wallet"
            />
            <StatCard
              tone="gold"
              label="Platform Commission Revenue"
              value={ownerFin ? money(ownerFin.platform_commission_revenue) : "৳—"}
              meta={ownerFin ? `Net profit: ${money(ownerFin.net_platform_profit)}` : "Server-calculated"}
              icon="chart"
            />
            <StatCard
              label="Seller Liabilities & Payouts"
              value={ownerFin ? money(ownerFin.seller_outstanding_liabilities) : "৳—"}
              meta={
                ownerFin
                  ? `${ownerFin.pending_payouts_count} pending · ${ownerFin.completed_payouts_count} paid`
                  : "Settlement obligations"
              }
              icon="store"
            />
            <StatCard
              label="Refunds & Expenses"
              value={ownerFin ? money(Number(ownerFin.total_refunds) + Number(ownerFin.operational_expenses)) : "৳—"}
              meta={
                ownerFin
                  ? `Refunds ${money(ownerFin.total_refunds)} · OpEx ${money(ownerFin.operational_expenses)}`
                  : "Deductions"
              }
              icon="refresh"
            />
          </div>

          <div className="lx-stat-grid">
            <StatCard
              label="Total Customers"
              value={ownerBiz ? ownerBiz.total_customers : "—"}
              meta="Verified shopper accounts"
              icon="user"
            />
            <StatCard
              label="Active / Total Sellers"
              value={ownerBiz ? `${ownerBiz.active_sellers} / ${ownerBiz.total_sellers}` : "—"}
              meta={ownerBiz ? `${ownerBiz.pending_applications} pending applications` : "Merchant network"}
              icon="store"
            />
            <StatCard
              label="Total / Pending Products"
              value={ownerBiz ? `${ownerBiz.total_products} (${ownerBiz.pending_products} pending)` : "—"}
              meta={ownerBiz ? `${ownerBiz.published_products} published listings` : "Catalog"}
              icon="box"
            />
            <StatCard
              label="Completed / Cancelled Orders"
              value={ownerBiz ? `${ownerBiz.completed_orders} / ${ownerBiz.cancelled_orders}` : "—"}
              meta={ownerBiz ? `${ownerBiz.total_orders} total orders placed` : "Order lifecycle"}
              icon="orders"
            />
          </div>

          <div className="lx-grid-2">
            <Card>
              <CardHeader
                title="14-Day Daily Sales Velocity"
                subtitle="Accurate server-calculated checkout volume across verified sellers (BDT)"
                action={<Badge tone="cobalt">Daily Sales</Badge>}
              />
              <CardBody>
                {dailySalesChart.length ? (
                  <AreaChart data={dailySalesChart} />
                ) : (
                  <EmptyState title="Sign in as Owner to inspect daily sales chart" />
                )}
              </CardBody>
            </Card>

            <Card>
              <CardHeader
                title="Monthly & Yearly Revenue Comparison"
                subtitle="Aggregated revenue trajectory and order status breakdown"
              />
              <CardBody>
                {monthlyRevenueBars.length ? (
                  <div style={{ display: "grid", gap: 18 }}>
                    <BarChart items={monthlyRevenueBars} />
                    {yearlyRevenueBars.length > 0 && <BarChart items={yearlyRevenueBars} />}
                    {orderStatusBars.length > 0 && <BarChart items={orderStatusBars} />}
                  </div>
                ) : (
                  <EmptyState title="Sign in as Owner to view revenue comparisons" />
                )}
              </CardBody>
            </Card>
          </div>

          {ownerData && (
            <div className="lx-grid-2">
              <Card>
                <CardHeader title="Seller Performance Leaderboard" subtitle="Gross sales, platform commission, and net earnings by store" />
                <CardBody>
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Store</th>
                          <th>Orders</th>
                          <th>Gross Sales</th>
                          <th>Commission</th>
                          <th>Net Earnings</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ownerData.seller_performance.map((s: any) => (
                          <tr key={s.id}>
                            <td>
                              <strong>{s.business_name}</strong>
                              <span style={{ display: "block", fontSize: 11, color: "var(--slate)" }}>{s.email}</span>
                            </td>
                            <td>{s.orders_count}</td>
                            <td>{money(s.gross_sales)}</td>
                            <td>{money(s.commission_generated)}</td>
                            <td>{money(s.net_earnings)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardBody>
              </Card>

              <Card>
                <CardHeader title="Top Product Performance" subtitle="Best-performing listings by revenue and units sold" />
                <CardBody>
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Product</th>
                          <th>Units</th>
                          <th>Revenue</th>
                          <th>Stock</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ownerData.product_performance.slice(0, 6).map((p: any) => (
                          <tr key={p.id}>
                            <td>
                              <strong>{p.name}</strong>
                              <span style={{ display: "block", fontSize: 11, color: "var(--slate)" }}>{p.seller_name}</span>
                            </td>
                            <td>{p.units_sold}</td>
                            <td>{money(p.revenue)}</td>
                            <td>{p.stock_quantity}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardBody>
              </Card>
            </div>
          )}
        </>
      )}

      {activeTab === "#managers" && (
        <>
          <div className="lx-grid-2">
            <Card>
              <CardHeader
                title="Create & Invite Partner Manager"
                subtitle="Only the platform Owner can create manager accounts and configure responsibilities"
              />
              <CardBody>
                <form onSubmit={createManager} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <TextInput
                    label="Manager Email"
                    type="email"
                    required
                    value={mgrEmail}
                    onChange={(e) => setMgrEmail(e.target.value)}
                    placeholder="partner@shoplex.com"
                  />
                  <TextInput
                    label="Temporary Password (optional)"
                    type="password"
                    value={mgrPassword}
                    onChange={(e) => setMgrPassword(e.target.value)}
                    placeholder="Auto-generated if blank"
                  />
                  <TextInput
                    label="First Name"
                    required
                    value={mgrFirst}
                    onChange={(e) => setMgrFirst(e.target.value)}
                    placeholder="Tariq"
                  />
                  <TextInput
                    label="Last Name"
                    value={mgrLast}
                    onChange={(e) => setMgrLast(e.target.value)}
                    placeholder="Hasan"
                  />
                  <TextInput
                    label="Title"
                    required
                    value={mgrTitle}
                    onChange={(e) => setMgrTitle(e.target.value)}
                  />
                  <TextInput
                    label="Business Unit"
                    required
                    value={mgrUnit}
                    onChange={(e) => setMgrUnit(e.target.value)}
                  />
                  <div style={{ gridColumn: "1 / -1" }}>
                    <TextInput
                      label="Assigned Responsibilities (comma-separated)"
                      value={mgrResp}
                      onChange={(e) => setMgrResp(e.target.value)}
                    />
                  </div>
                  <div style={{ gridColumn: "1 / -1" }}>
                    <Button type="submit">Create &amp; Invite Manager</Button>
                  </div>
                </form>
              </CardBody>
            </Card>

            <Card>
              <CardHeader
                title="Assign Admin to Manager"
                subtitle="Delegate Admin accounts to specific Managers and track assignment history"
              />
              <CardBody>
                <form onSubmit={submitAdminAssignment} style={{ display: "grid", gap: 12, marginBottom: 16 }}>
                  <SelectInput
                    label="Select Admin Account"
                    value={assignAdminId}
                    onChange={(e) => setAssignAdminId(e.target.value)}
                    options={[
                      { value: "", label: "Choose Admin…" },
                      ...(adminAssignData?.admins ?? []).map((a: any) => ({
                        value: a.id,
                        label: `${a.name} (${a.email})`,
                      })),
                    ]}
                  />
                  <SelectInput
                    label="Assign to Manager"
                    value={assignManagerId}
                    onChange={(e) => setAssignManagerId(e.target.value)}
                    options={[
                      { value: "", label: "Choose Manager…" },
                      ...(managerGov?.managers ?? [])
                        .filter((m: any) => m.is_active)
                        .map((m: any) => ({
                          value: String(m.id),
                          label: `${m.first_name} ${m.last_name} (${m.email})`,
                        })),
                    ]}
                  />
                  <TextInput
                    label="Delegated Scope"
                    value={assignResp}
                    onChange={(e) => setAssignResp(e.target.value)}
                  />
                  <Button type="submit" disabled={!assignAdminId || !assignManagerId}>
                    Assign / Reassign Admin
                  </Button>
                </form>

                {adminAssignData?.active_assignments?.length > 0 && (
                  <div style={{ display: "grid", gap: 8 }}>
                    <strong style={{ fontSize: 12 }}>Active Admin Assignments</strong>
                    {adminAssignData.active_assignments.map((a: any) => (
                      <div
                        key={a.id}
                        style={{
                          padding: 10,
                          border: "1px solid var(--line)",
                          borderRadius: "var(--radius-sm)",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          fontSize: 12,
                        }}
                      >
                        <div>
                          <strong>{a.admin_email}</strong> → <span>{a.manager_email}</span>
                          <small style={{ display: "block", color: "var(--slate)" }}>{a.responsibilities}</small>
                        </div>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => void removeAdminAssignment(a.admin_id, a.manager_id)}
                        >
                          Remove
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardBody>
            </Card>
          </div>

          <Card style={{ marginBottom: 24 }}>
            <CardHeader
              title="Manager Directory & Granular Permission Matrix"
              subtitle="Grant or revoke sensitive permissions per Manager. Revoking access takes effect immediately."
            />
            <CardBody>
              {managerGov?.managers?.length ? (
                <div style={{ display: "grid", gap: 16 }}>
                  {managerGov.managers.map((mgr: any) => (
                    <article
                      key={mgr.id}
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
                          <strong style={{ fontSize: 16 }}>
                            {mgr.first_name} {mgr.last_name}
                          </strong>{" "}
                          <span style={{ fontSize: 12, color: "var(--slate)" }}>
                            ({mgr.email}) · {mgr.title} · {mgr.business_unit}
                          </span>
                          <div style={{ marginTop: 4, display: "flex", gap: 8, alignItems: "center" }}>
                            <Badge tone="gold">Equity Stake: {mgr.ownership_percentage}%</Badge>
                            <Badge tone="navy">{mgr.assigned_admins?.length ?? 0} Assigned Admins</Badge>
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                          <StatusPill tone={mgr.is_active ? "success" : "danger"}>
                            {mgr.is_active ? "Active" : "Suspended / Removed"}
                          </StatusPill>
                          {mgr.is_active ? (
                            <>
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => void updateManagerStatus(mgr.id, "suspend")}
                              >
                                Suspend
                              </Button>
                              <Button
                                size="sm"
                                variant="danger"
                                onClick={() => void updateManagerStatus(mgr.id, "remove")}
                              >
                                Remove Role
                              </Button>
                            </>
                          ) : (
                            <Button size="sm" onClick={() => void updateManagerStatus(mgr.id, "activate")}>
                              Activate
                            </Button>
                          )}
                        </div>
                      </div>

                      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                        {Object.entries(mgr.permissions ?? {}).map(([permKey, granted]) => (
                          <button
                            key={permKey}
                            type="button"
                            onClick={() => void toggleManagerPermission(mgr.id, permKey, !granted)}
                            style={{
                              padding: "6px 12px",
                              borderRadius: 999,
                              border: granted ? "1px solid var(--cobalt)" : "1px solid var(--line)",
                              background: granted ? "rgba(37,99,235,0.1)" : "#fff",
                              color: granted ? "var(--cobalt)" : "var(--slate)",
                              fontSize: 11,
                              fontWeight: 600,
                              cursor: "pointer",
                            }}
                          >
                            {granted ? "✓ " : "+ "}
                            {permissionLabels[permKey] ?? permKey}
                          </button>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState title="No manager accounts configured yet" />
              )}
            </CardBody>
          </Card>
        </>
      )}

      {activeTab === "#shares" && (
        <>
          {activeSharePlan && (
            <div className="lx-stat-grid">
              <StatCard
                tone="navy"
                label="Company Valuation"
                value={money(activeSharePlan.company_valuation)}
                meta={`${activeSharePlan.total_authorized_shares.toLocaleString()} authorized shares`}
                icon="wallet"
              />
              <StatCard
                tone="gold"
                label="Allocated Partner Equity"
                value={`${activeSharePlan.allocated_percentage}%`}
                meta={`${activeSharePlan.allocated_shares.toLocaleString()} shares allocated`}
                icon="sparkles"
              />
              <StatCard
                label="Available in Partner Pool"
                value={`${activeSharePlan.remaining_percentage}%`}
                meta={`Ceiling: ${activeSharePlan.max_allocated_percentage}% max partner pool`}
                icon="chart"
              />
              <StatCard
                label="Owner Retained Equity"
                value={`${activeSharePlan.owner_retained_percentage}%`}
                meta="Controlling majority stake"
                icon="shield"
              />
            </div>
          )}

          <div className="lx-grid-2">
            <Card>
              <CardHeader
                title="Create / Update Business Share Plan & Valuation"
                subtitle="Define authorized share pool, valuation, and maximum partner allocation ceiling"
              />
              <CardBody>
                <form onSubmit={createSharePlan} style={{ display: "grid", gap: 12 }}>
                  <TextInput
                    label="Share Plan Name"
                    required
                    value={planName}
                    onChange={(e) => setPlanName(e.target.value)}
                  />
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    <TextInput
                      label="Total Authorized Shares"
                      type="number"
                      min="100"
                      required
                      value={planShares}
                      onChange={(e) => setPlanShares(e.target.value)}
                    />
                    <TextInput
                      label="Max Partner Pool (%)"
                      type="number"
                      step="0.01"
                      min="0.01"
                      max="100"
                      required
                      value={planMaxPct}
                      onChange={(e) => setPlanMaxPct(e.target.value)}
                    />
                  </div>
                  <TextInput
                    label="Recorded Business Valuation (BDT)"
                    type="number"
                    step="0.01"
                    min="1"
                    required
                    value={planValuation}
                    onChange={(e) => setPlanValuation(e.target.value)}
                  />
                  <Button type="submit">Save Share Plan &amp; Valuation</Button>
                </form>
              </CardBody>
            </Card>

            <Card>
              <CardHeader
                title="Allocate or Offer Shares to Partner"
                subtitle="Validates that total allocated percentages never exceed the permitted ceiling"
              />
              <CardBody>
                {sharePlans.length > 0 ? (
                  <div style={{ display: "grid", gap: 16 }}>
                    <form onSubmit={createShareAllocation} style={{ display: "grid", gap: 10 }}>
                      <strong style={{ fontSize: 12 }}>Direct Share Allocation</strong>
                      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 0.8fr 1fr", gap: 10 }}>
                        <TextInput
                          label="Partner Email"
                          type="email"
                          required
                          value={allocEmail}
                          onChange={(e) => setAllocEmail(e.target.value)}
                        />
                        <TextInput
                          label="Ownership (%)"
                          type="number"
                          step="0.01"
                          min="0.01"
                          max="100"
                          required
                          value={allocPct}
                          onChange={(e) => setAllocPct(e.target.value)}
                        />
                        <TextInput
                          label="Legal Reference"
                          required
                          value={allocRef}
                          onChange={(e) => setAllocRef(e.target.value)}
                        />
                      </div>
                      <Button type="submit" size="sm">
                        Allocate Shares
                      </Button>
                    </form>

                    <form onSubmit={createShareOffer} style={{ display: "grid", gap: 10, paddingTop: 12, borderTop: "1px solid var(--line)" }}>
                      <strong style={{ fontSize: 12 }}>Record Share Offer</strong>
                      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.7fr 1.2fr", gap: 10 }}>
                        <TextInput
                          label="Partner Email"
                          type="email"
                          required
                          value={offerEmail}
                          onChange={(e) => setOfferEmail(e.target.value)}
                        />
                        <TextInput
                          label="Offered (%)"
                          type="number"
                          step="0.01"
                          min="0.01"
                          required
                          value={offerPct}
                          onChange={(e) => setOfferPct(e.target.value)}
                        />
                        <TextInput
                          label="Terms Note"
                          value={offerNote}
                          onChange={(e) => setOfferNote(e.target.value)}
                        />
                      </div>
                      <Button type="submit" variant="secondary" size="sm">
                        Record Share Offer
                      </Button>
                    </form>
                  </div>
                ) : (
                  <EmptyState title="Create a share plan first to allocate or offer partner equity" />
                )}
              </CardBody>
            </Card>
          </div>

          {activeSharePlan && (
            <>
              <div className="lx-grid-2">
                <Card>
                  <CardHeader
                    title="Record Permitted Legal Share Transfer"
                    subtitle="Atomic transfer between holders with append-only transaction and history logging"
                  />
                  <CardBody>
                    <form onSubmit={createShareTransfer} style={{ display: "grid", gap: 10 }}>
                      <SelectInput
                        label="Source Allocation"
                        value={transferAllocId}
                        onChange={(e) => setTransferAllocId(e.target.value)}
                        options={[
                          { value: "", label: "Select source holder…" },
                          ...(activeSharePlan.allocations ?? []).map((a: any) => ({
                            value: a.id,
                            label: `${a.holder_email} (${a.ownership_percentage}%)`,
                          })),
                        ]}
                      />
                      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 0.7fr 1fr", gap: 10 }}>
                        <TextInput
                          label="Recipient Email"
                          type="email"
                          required
                          value={transferToEmail}
                          onChange={(e) => setTransferToEmail(e.target.value)}
                        />
                        <TextInput
                          label="Transfer (%)"
                          type="number"
                          step="0.01"
                          min="0.01"
                          required
                          value={transferPct}
                          onChange={(e) => setTransferPct(e.target.value)}
                        />
                        <TextInput
                          label="Transfer Deed Ref"
                          required
                          value={transferRef}
                          onChange={(e) => setTransferRef(e.target.value)}
                        />
                      </div>
                      <Button type="submit" size="sm" disabled={!transferAllocId}>
                        Execute Legal Share Transfer
                      </Button>
                    </form>
                  </CardBody>
                </Card>

                <Card>
                  <CardHeader
                    title="Record Ownership Legal Document"
                    subtitle="Attach certificates, shareholder agreements, or transfer deeds"
                  />
                  <CardBody>
                    <form onSubmit={createShareDocument} style={{ display: "grid", gap: 10 }}>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                        <TextInput
                          label="Document Title"
                          required
                          value={docTitle}
                          onChange={(e) => setDocTitle(e.target.value)}
                          placeholder="Partner Equity Certificate"
                        />
                        <TextInput
                          label="Holder Email"
                          type="email"
                          value={docHolderEmail}
                          onChange={(e) => setDocHolderEmail(e.target.value)}
                        />
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                        <SelectInput
                          label="Document Type"
                          value={docType}
                          onChange={(e) => setDocType(e.target.value)}
                          options={[
                            { value: "certificate", label: "Share Certificate" },
                            { value: "agreement", label: "Shareholder Agreement" },
                            { value: "transfer_deed", label: "Transfer Deed" },
                            { value: "valuation_report", label: "Valuation Report" },
                          ]}
                        />
                        <TextInput
                          label="Reference Number"
                          required
                          value={docRef}
                          onChange={(e) => setDocRef(e.target.value)}
                        />
                      </div>
                      <Button type="submit" size="sm">
                        Save Ownership Document
                      </Button>
                    </form>
                  </CardBody>
                </Card>
              </div>

              <Card style={{ marginBottom: 24 }}>
                <CardHeader
                  title={`Ownership Cap Table & Append-Only Share Ledger (${activeSharePlan.name})`}
                  subtitle="Internal corporate ownership registry — not a public stock-trading platform"
                />
                <CardBody>
                  <div style={{ display: "grid", gap: 20 }}>
                    {activeSharePlan.allocations?.length ? (
                      <div className="table-wrap">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Partner / Holder</th>
                              <th>Shares</th>
                              <th>Ownership %</th>
                              <th>Implied Value</th>
                              <th>Status</th>
                              <th>Allocated At</th>
                            </tr>
                          </thead>
                          <tbody>
                            {activeSharePlan.allocations.map((a: any) => (
                              <tr key={a.id}>
                                <td>
                                  <strong>{a.holder_name}</strong>
                                  <span style={{ display: "block", fontSize: 11, color: "var(--slate)" }}>{a.holder_email}</span>
                                </td>
                                <td>{a.allocated_shares.toLocaleString()}</td>
                                <td><Badge tone="gold">{a.ownership_percentage}%</Badge></td>
                                <td><strong>{money(a.implied_value)}</strong></td>
                                <td><StatusPill tone="success">{a.status}</StatusPill></td>
                                <td>{new Date(a.allocated_at).toLocaleDateString()}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <EmptyState title="No partner share allocations recorded yet" />
                    )}

                    {activeSharePlan.transactions?.length > 0 && (
                      <div className="table-wrap">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Transaction Type</th>
                              <th>From</th>
                              <th>To</th>
                              <th>Shares</th>
                              <th>Delta %</th>
                              <th>Legal Reference</th>
                              <th>Date</th>
                            </tr>
                          </thead>
                          <tbody>
                            {activeSharePlan.transactions.map((tx: any) => (
                              <tr key={tx.id}>
                                <td><Badge tone="navy">{tx.transaction_type}</Badge></td>
                                <td>{tx.from_holder_email || "Treasury"}</td>
                                <td>{tx.to_holder_email || "Treasury"}</td>
                                <td>{tx.shares_count.toLocaleString()}</td>
                                <td>{tx.percentage_delta}%</td>
                                <td style={{ fontFamily: "monospace", fontSize: 11 }}>{tx.legal_reference}</td>
                                <td>{new Date(tx.created_at).toLocaleString()}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </CardBody>
              </Card>
            </>
          )}
        </>
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
                        Approve (Owner)
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

      {activeTab === "#sellers" && (
        <Card style={{ marginBottom: 24 }}>
          <CardHeader
            title="All Marketplace Sellers & Account Governance"
            subtitle="Inspect individual seller earnings, performance, and suspend or reactivate accounts"
          />
          <CardBody>
            {allSellers.length ? (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Merchant</th>
                      <th>Products</th>
                      <th>Orders</th>
                      <th>Gross Sales</th>
                      <th>Commission</th>
                      <th>Net Earnings</th>
                      <th>Status</th>
                      <th>Governance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allSellers.map((seller) => (
                      <tr key={seller.id}>
                        <td>
                          <strong>{seller.business_name}</strong>
                          <span style={{ display: "block", fontSize: 11, color: "var(--slate)" }}>{seller.email}</span>
                        </td>
                        <td>{seller.published_products} / {seller.product_count}</td>
                        <td>{seller.orders_count}</td>
                        <td>{money(seller.gross_sales)}</td>
                        <td>{money(seller.commission_total)}</td>
                        <td>{money(seller.net_earnings)}</td>
                        <td>
                          <StatusPill tone={seller.is_active ? "success" : "danger"}>
                            {seller.is_active ? "Active" : "Suspended"}
                          </StatusPill>
                        </td>
                        <td>
                          {seller.is_active ? (
                            <Button
                              size="sm"
                              variant="danger"
                              onClick={() => void changeSellerStatus(seller.id, "suspend")}
                            >
                              Suspend
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="primary"
                              onClick={() => void changeSellerStatus(seller.id, "reactivate")}
                            >
                              Reactivate
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState title="No seller profiles registered yet" />
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
                        Approve (Owner)
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
        <>
          <Card style={{ marginBottom: 24 }}>
            <CardHeader
              title="Catalog Moderation & Product Suspension / Restoration"
              subtitle="Owner can suspend inappropriate products or restore previously suspended listings."
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
                              <Button
                                size="sm"
                                variant="danger"
                                onClick={() => void changeProductStatus(prod.id, "suspend")}
                              >
                                Suspend
                              </Button>
                            ) : (
                              <Button
                                size="sm"
                                variant="primary"
                                onClick={() => void changeProductStatus(prod.id, "restore")}
                              >
                                Restore
                              </Button>
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

          <div className="lx-grid-2">
            <Card>
              <CardHeader title="Manage Categories" subtitle="Create or update marketplace departments" />
              <CardBody>
                <form onSubmit={saveCategory} style={{ display: "grid", gap: 12 }}>
                  <TextInput
                    label="Category Name"
                    required
                    value={catName}
                    onChange={(e) => setCatName(e.target.value)}
                    placeholder="e.g. Fine Jewelry"
                  />
                  <TextInput
                    label="Description"
                    value={catDesc}
                    onChange={(e) => setCatDesc(e.target.value)}
                    placeholder="Department overview"
                  />
                  <Button type="submit">Save Category</Button>
                </form>
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Manage Brands" subtitle="Register verified brand labels" />
              <CardBody>
                <form onSubmit={saveBrand} style={{ display: "grid", gap: 12 }}>
                  <TextInput
                    label="Brand Name"
                    required
                    value={brandName}
                    onChange={(e) => setBrandName(e.target.value)}
                    placeholder="e.g. Meridian Horology"
                  />
                  <TextInput
                    label="Description"
                    value={brandDesc}
                    onChange={(e) => setBrandDesc(e.target.value)}
                    placeholder="Brand heritage & note"
                  />
                  <Button type="submit">Save Brand</Button>
                </form>
              </CardBody>
            </Card>
          </div>

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
                  Flagged products appear here for compliance review.
                </EmptyState>
              )}
            </CardBody>
          </Card>
        </>
      )}

      {activeTab === "#finance" && (
        <>
          <div className="lx-stat-grid">
            <StatCard
              tone="navy"
              label="Gross Sales"
              value={ownerFin ? money(ownerFin.gross_sales) : "৳—"}
              meta={ownerFin ? `Net Revenue: ${money(ownerFin.net_revenue)}` : "Total checkout volume"}
              icon="wallet"
            />
            <StatCard
              tone="gold"
              label="Platform Commissions"
              value={ownerFin ? money(ownerFin.platform_commission_revenue) : "৳—"}
              meta={ownerFin ? `Net Profit: ${money(ownerFin.net_platform_profit)}` : "Marketplace take"}
              icon="chart"
            />
            <StatCard
              label="Seller Liabilities"
              value={ownerFin ? money(ownerFin.seller_outstanding_liabilities) : "৳—"}
              meta={ownerFin ? `Settled payouts: ${money(ownerFin.completed_payouts_amount)}` : "Payable balance"}
              icon="store"
            />
            <StatCard
              label="Refunds, OpEx & Fees"
              value={
                ownerFin
                  ? money(
                      Number(ownerFin.total_refunds) +
                        Number(ownerFin.operational_expenses) +
                        Number(ownerFin.payment_fees)
                    )
                  : "৳—"
              }
              meta={
                ownerFin
                  ? `OpEx ${money(ownerFin.operational_expenses)} · Fees ${money(ownerFin.payment_fees)}`
                  : "Deductions"
              }
              icon="refresh"
            />
          </div>

          <div className="lx-grid-2">
            <Card>
              <CardHeader
                title="Seller Payout Settlement Queue"
                subtitle="Approve, settle (posts immutable ledger entry), or reject merchant payout requests"
                action={<StatusPill tone="warning">{pendingPayoutsCount} active</StatusPill>}
              />
              <CardBody>
                {payoutQueue.length ? (
                  <div style={{ display: "grid", gap: 12 }}>
                    {payoutQueue.map((p) => (
                      <article
                        key={p.id}
                        style={{
                          padding: 14,
                          border: "1px solid var(--line)",
                          borderRadius: "var(--radius-sm)",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          flexWrap: "wrap",
                          gap: 10,
                        }}
                      >
                        <div>
                          <strong>{p.seller_name}</strong> · <span style={{ fontWeight: 700 }}>{money(p.amount)}</span>
                          <span style={{ display: "block", fontSize: 11, color: "var(--slate)" }}>
                            {p.seller_email} · Requested {new Date(p.requested_at).toLocaleDateString()}
                          </span>
                        </div>
                        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                          <StatusPill
                            tone={
                              p.status === "paid"
                                ? "success"
                                : p.status === "rejected"
                                  ? "danger"
                                  : "warning"
                            }
                          >
                            {p.status}
                          </StatusPill>
                          {(p.status === "pending" || p.status === "approved") && (
                            <>
                              {p.status === "pending" && (
                                <Button size="sm" variant="secondary" onClick={() => void decidePayout(p.id, "approved")}>
                                  Approve
                                </Button>
                              )}
                              <Button size="sm" onClick={() => void decidePayout(p.id, "paid")}>
                                Settle Paid
                              </Button>
                              <Button size="sm" variant="danger" onClick={() => void decidePayout(p.id, "rejected")}>
                                Reject
                              </Button>
                            </>
                          )}
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <EmptyState title="No seller payout requests yet" />
                )}
              </CardBody>
            </Card>

            <Card>
              <CardHeader
                title="Append Operational Expense or Payment Fee"
                subtitle="Posts a new transaction to the immutable financial ledger"
              />
              <CardBody>
                <form onSubmit={recordLedgerEntry} style={{ display: "grid", gap: 12 }}>
                  <SelectInput
                    label="Transaction Type"
                    value={expenseType}
                    onChange={(e) => setExpenseType(e.target.value)}
                    options={[
                      { value: "operational_expense", label: "Operational Expense" },
                      { value: "payment_fee", label: "Payment Processing Fee" },
                      { value: "refund_deduction", label: "Refund Deduction" },
                    ]}
                  />
                  <TextInput
                    label="Amount (BDT)"
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    value={expenseAmount}
                    onChange={(e) => setExpenseAmount(e.target.value)}
                    placeholder="0.00"
                  />
                  <TextInput
                    label="Reference Note / Description"
                    required
                    value={expenseDesc}
                    onChange={(e) => setExpenseDesc(e.target.value)}
                    placeholder="e.g. Cloud hosting & CDN settlement"
                  />
                  <Button type="submit">Post to Immutable Ledger</Button>
                </form>
              </CardBody>
            </Card>
          </div>

          {reconciliation && (
            <Card style={{ marginBottom: 24 }}>
              <CardHeader
                title="Payment & Ledger Reconciliation Audit"
                subtitle="Cross-checks completed suborder earnings, seller ledger credits, settled payouts, and webhook callbacks"
                action={
                  <StatusPill tone={reconciliation.reconciled ? "success" : "danger"}>
                    {reconciliation.reconciled
                      ? "Reconciled · ৳0.00 Discrepancy"
                      : `Discrepancy: ${money(reconciliation.discrepancy_amount)}`}
                  </StatusPill>
                }
              />
              <CardBody>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 24, fontSize: 12 }}>
                  <div>
                    <span style={{ color: "var(--slate)", display: "block" }}>Completed Suborder Net</span>
                    <strong>{money(reconciliation.completed_suborder_net_earnings)}</strong>
                  </div>
                  <div>
                    <span style={{ color: "var(--slate)", display: "block" }}>Seller Ledger Credits</span>
                    <strong>{money(reconciliation.recorded_seller_sale_credits)}</strong>
                  </div>
                  <div>
                    <span style={{ color: "var(--slate)", display: "block" }}>Seller Refund Debits</span>
                    <strong>{money(reconciliation.recorded_seller_refund_debits)}</strong>
                  </div>
                  <div>
                    <span style={{ color: "var(--slate)", display: "block" }}>Settled Payouts (DB / Ledger)</span>
                    <strong>
                      {money(reconciliation.settled_seller_payouts)} / {money(reconciliation.ledger_settled_payouts)}
                    </strong>
                  </div>
                  <div>
                    <span style={{ color: "var(--slate)", display: "block" }}>Verified Webhook Events</span>
                    <strong>{reconciliation.webhook_events_processed}</strong>
                  </div>
                </div>
              </CardBody>
            </Card>
          )}

          <Card style={{ marginBottom: 24 }}>
            <CardHeader
              title="Immutable Append-Only Financial Ledger"
              subtitle="Every transaction is permanently recorded with a UUID, reference ID, currency, and timestamp."
              action={<Badge tone="navy">{ledgerData?.entries?.length ?? 0} entries</Badge>}
            />
            <CardBody>
              {ledgerData?.entries?.length ? (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Transaction ID</th>
                        <th>Type</th>
                        <th>Amount</th>
                        <th>Reference</th>
                        <th>Status</th>
                        <th>Description</th>
                        <th>Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ledgerData.entries.map((entry: any) => (
                        <tr key={entry.id}>
                          <td style={{ fontFamily: "monospace", fontSize: 11 }}>{entry.id.slice(0, 13)}…</td>
                          <td>
                            <Badge tone={entry.transaction_type === "platform_commission" ? "gold" : "indigo"}>
                              {entry.transaction_type.replaceAll("_", " ")}
                            </Badge>
                          </td>
                          <td>
                            <strong>{money(entry.amount)}</strong> {entry.currency}
                          </td>
                          <td style={{ fontFamily: "monospace", fontSize: 11 }}>{entry.reference_id}</td>
                          <td>
                            <StatusPill tone={entry.status === "settled" ? "success" : "info"}>
                              {entry.status}
                            </StatusPill>
                          </td>
                          <td>{entry.description || "—"}</td>
                          <td>{new Date(entry.created_at).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="No ledger entries recorded yet" />
              )}
            </CardBody>
          </Card>
        </>
      )}

      {activeTab === "#settings" && (
        <>
          <div className="lx-grid-2">
            <Card>
              <CardHeader
                title="Platform Commission Rules"
                subtitle="Precedence: Product override → Seller+Category → Seller → Category → Global"
              />
              <CardBody>
                <form onSubmit={createCommissionRule} style={{ display: "flex", gap: 10, alignItems: "flex-end", marginBottom: 16 }}>
                  <TextInput
                    label="Global Commission (%)"
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    value={newCommission}
                    onChange={(e) => setNewCommission(e.target.value)}
                  />
                  <Button type="submit" size="md">
                    Add Rule
                  </Button>
                </form>
                {commissions.length ? (
                  <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 8, fontSize: 12 }}>
                    {commissions.map((rule: any) => (
                      <li
                        key={rule.id}
                        style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--line)" }}
                      >
                        <span>{rule.name || "Global Commission Rule"}</span>
                        <strong>{rule.percentage}%</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p style={{ margin: 0, fontSize: 12, color: "var(--slate)" }}>
                    Using environment fallback commission (10.00%).
                  </p>
                )}
              </CardBody>
            </Card>

            <Card>
              <CardHeader
                title="Country Shipping Configuration"
                subtitle="Server-enforced per-seller shipping fee during checkout"
              />
              <CardBody>
                <form onSubmit={createShippingRule} style={{ display: "flex", gap: 10, alignItems: "flex-end", marginBottom: 16 }}>
                  <TextInput
                    label="Country (ISO-2)"
                    maxLength={2}
                    value={newShipCountry}
                    onChange={(e) => setNewShipCountry(e.target.value)}
                  />
                  <TextInput
                    label="Fee (BDT)"
                    type="number"
                    step="0.01"
                    min="0"
                    value={newShipAmount}
                    onChange={(e) => setNewShipAmount(e.target.value)}
                  />
                  <Button type="submit" size="md">
                    Save Fee
                  </Button>
                </form>
                {shippingRules.length ? (
                  <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 8, fontSize: 12 }}>
                    {shippingRules.map((rule: any) => (
                      <li
                        key={rule.id}
                        style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--line)" }}
                      >
                        <span>Country: {rule.country_code}</span>
                        <strong>{money(rule.amount)}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p style={{ margin: 0, fontSize: 12, color: "var(--slate)" }}>No custom shipping rules configured.</p>
                )}
              </CardBody>
            </Card>
          </div>

          {platformSettings && (
            <Card style={{ marginBottom: 24 }}>
              <CardHeader
                title="Enterprise Platform Configuration"
                subtitle="Website info, branding, tax settings, refund policies, payment gateways, email, SEO, and maintenance mode"
              />
              <CardBody>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
                  {Object.entries(platformSettings).map(([sectionKey, sectionVal]: [string, any]) => (
                    <div
                      key={sectionKey}
                      style={{
                        padding: 16,
                        border: "1px solid var(--line)",
                        borderRadius: "var(--radius-sm)",
                        background: "var(--ivory)",
                      }}
                    >
                      <strong style={{ display: "block", fontSize: 13, textTransform: "capitalize", marginBottom: 8 }}>
                        {sectionKey.replaceAll("_", " ")}
                      </strong>
                      <pre style={{ margin: 0, fontSize: 11, color: "var(--slate)", whiteSpace: "pre-wrap" }}>
                        {JSON.stringify(sectionVal, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: 16, display: "flex", gap: 10 }}>
                  <Button
                    onClick={() =>
                      void savePlatformSettings({
                        maintenance_mode: {
                          enabled: !platformSettings.maintenance_mode?.enabled,
                          message: "SHOPLEX is undergoing scheduled maintenance.",
                        },
                      })
                    }
                  >
                    Toggle Maintenance Mode ({platformSettings.maintenance_mode?.enabled ? "ON" : "OFF"})
                  </Button>
                </div>
              </CardBody>
            </Card>
          )}
        </>
      )}

      {activeTab === "#security" && (
        <>
          <div className="lx-grid-2">
            <Card>
              <CardHeader
                title="Owner Mandatory MFA & Reauthentication"
                subtitle="Sensitive Owner actions require password reauthentication and TOTP MFA verification"
                action={
                  <StatusPill tone={securityData?.mfa_enrolled ? "success" : "warning"}>
                    {securityData?.mfa_enrolled ? "MFA Verified" : "Enrollment Required"}
                  </StatusPill>
                }
              />
              <CardBody>
                <div style={{ display: "grid", gap: 12 }}>
                  <TextInput
                    label="Authenticator Device Name"
                    value={mfaDeviceName}
                    onChange={(e) => setMfaDeviceName(e.target.value)}
                  />
                  <TextInput
                    label="Confirm Owner Password"
                    type="password"
                    value={securityPassword}
                    onChange={(e) => setSecurityPassword(e.target.value)}
                    placeholder="Enter current password to authorize"
                  />
                  <div style={{ display: "flex", gap: 10 }}>
                    <Button onClick={() => void runOwnerSecurityAction("enroll_mfa")}>
                      Enroll / Rotate MFA Device
                    </Button>
                    <Button variant="secondary" onClick={() => void runOwnerSecurityAction("reauthenticate")}>
                      Verify Reauthentication
                    </Button>
                  </div>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardHeader
                title="Login Alerts & Suspicious Sign-In Detection"
                subtitle="Automated alerts generated on Owner authentication events"
              />
              <CardBody>
                {securityData?.login_alerts?.length ? (
                  <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 10, fontSize: 12 }}>
                    {securityData.login_alerts.slice(0, 6).map((alert: any) => (
                      <li key={alert.id} style={{ paddingBottom: 8, borderBottom: "1px solid var(--line)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                          <strong>{alert.title}</strong>
                          <small style={{ color: "var(--slate)" }}>{new Date(alert.created_at).toLocaleString()}</small>
                        </div>
                        <p style={{ margin: "4px 0 0", color: "var(--slate)" }}>{alert.body}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState title="No security alerts recorded" />
                )}
              </CardBody>
            </Card>
          </div>

          <Card style={{ marginBottom: 24 }}>
            <CardHeader
              title="Immutable Platform Audit History"
              subtitle="Append-only security and governance log across all five portals"
              action={
                <input
                  className="field__input"
                  style={{ minHeight: 34, maxWidth: 220, fontSize: 12 }}
                  placeholder="Filter by action…"
                  value={auditFilter}
                  onChange={(e) => setAuditFilter(e.target.value)}
                />
              }
            />
            <CardBody>
              {auditLogs.length ? (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Action</th>
                        <th>Actor</th>
                        <th>Resource</th>
                        <th>IP Address</th>
                        <th>Metadata</th>
                        <th>Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs
                        .filter((log) => !auditFilter || log.action.toLowerCase().includes(auditFilter.toLowerCase()))
                        .slice(0, 40)
                        .map((log) => (
                          <tr key={log.id}>
                            <td>
                              <Badge tone="navy">{log.action}</Badge>
                            </td>
                            <td>{log.actor_email}</td>
                            <td>
                              {log.resource_type} {log.resource_id ? `#${String(log.resource_id).slice(0, 8)}` : ""}
                            </td>
                            <td style={{ fontFamily: "monospace", fontSize: 11 }}>{log.ip_address || "local"}</td>
                            <td style={{ fontSize: 11, color: "var(--slate)" }}>
                              {Object.keys(log.metadata ?? {}).length ? JSON.stringify(log.metadata) : "—"}
                            </td>
                            <td>{new Date(log.created_at).toLocaleString()}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="No audit events found" />
              )}
            </CardBody>
          </Card>
        </>
      )}

      {activeTab === "#admins" && (
        <>
          <div style={{ marginBottom: 20 }}>
            <Notification title="Final Owner & Admin Role Structure Enforced" tone="info">
              Admins are SHOPLEX Owner employees/staff — never independent sellers, product owners, or revenue-sharing partners. All 16 permissions default to OFF and take effect immediately on every backend API when granted or revoked by Owner.
            </Notification>
          </div>

          <div className="lx-grid-2" style={{ marginBottom: 24 }}>
            <Card>
              <CardHeader
                title="Create Admin Staff Account"
                subtitle="New Admin accounts start with 0/16 permissions until explicitly authorized below."
              />
              <CardBody>
                <form onSubmit={createAdminStaff} style={{ display: "grid", gap: 12 }}>
                  <TextInput
                    label="Admin Email"
                    type="email"
                    required
                    value={admEmail}
                    onChange={(e) => setAdmEmail(e.target.value)}
                    placeholder="staff.admin@shoplex.local"
                  />
                  <div className="lx-grid-2">
                    <TextInput
                      label="First Name"
                      value={admFirst}
                      onChange={(e) => setAdmFirst(e.target.value)}
                      placeholder="First name"
                    />
                    <TextInput
                      label="Last Name"
                      value={admLast}
                      onChange={(e) => setAdmLast(e.target.value)}
                      placeholder="Last name"
                    />
                  </div>
                  <TextInput
                    label="Initial Password (optional)"
                    type="password"
                    value={admPassword}
                    onChange={(e) => setAdmPassword(e.target.value)}
                    placeholder="Min 12 chars or leave blank to auto-generate"
                  />
                  <Button type="submit">Create Admin Staff</Button>
                </form>
              </CardBody>
            </Card>

            <Card>
              <CardHeader
                title="Upload Platform-Owned SHOPLEX Product"
                subtitle="Owner can directly upload & publish SHOPLEX Official products (100% platform revenue)."
              />
              <CardBody>
                <form onSubmit={createPlatformProduct} style={{ display: "grid", gap: 12 }}>
                  <TextInput
                    label="Product Name"
                    required
                    value={pltName}
                    onChange={(e) => setPltName(e.target.value)}
                    placeholder="e.g. SHOPLEX Executive Leather Briefcase"
                  />
                  <TextInput
                    label="Description"
                    required
                    value={pltDesc}
                    onChange={(e) => setPltDesc(e.target.value)}
                    placeholder="Full product description"
                  />
                  <div className="lx-grid-2">
                    <SelectInput
                      label="Category"
                      value={pltCategory}
                      onChange={(e) => setPltCategory(e.target.value)}
                      options={
                        categories.length
                          ? categories.map((c: any) => ({ value: c.slug, label: c.name }))
                          : [{ value: "electronics", label: "Electronics" }]
                      }
                    />
                    <SelectInput
                      label="Product Source"
                      value={pltSource}
                      onChange={(e) => setPltSource(e.target.value as "owner_platform" | "supplier")}
                      options={[
                        { value: "owner_platform", label: "Owner / Platform Inventory" },
                        { value: "supplier", label: "Supplier Sourced" },
                      ]}
                    />
                  </div>
                  {pltSource === "supplier" && (
                    <TextInput
                      label="Supplier Name"
                      value={pltSupplier}
                      onChange={(e) => setPltSupplier(e.target.value)}
                      placeholder="e.g. Global Supply Co."
                    />
                  )}
                  <div className="lx-grid-2">
                    <TextInput
                      label="Price (BDT)"
                      type="number"
                      step="0.01"
                      min="1"
                      required
                      value={pltPrice}
                      onChange={(e) => setPltPrice(e.target.value)}
                      placeholder="2490.00"
                    />
                    <TextInput
                      label="Stock Quantity"
                      type="number"
                      min="0"
                      required
                      value={pltStock}
                      onChange={(e) => setPltStock(e.target.value)}
                    />
                  </div>
                  <Button type="submit">Publish SHOPLEX Product</Button>
                </form>
              </CardBody>
            </Card>
          </div>

          <Card style={{ marginBottom: 24 }}>
            <CardHeader
              title="Admin Staff Directory & 16-Permission Engine"
              subtitle="Toggle individual permissions per Admin account. Revocations take effect immediately on the backend and Admin sidebar."
              action={<Badge tone="navy">{adminStaffData?.admins?.length ?? 0} Admin staff</Badge>}
            />
            <CardBody>
              {adminStaffData?.admins?.length ? (
                <div style={{ display: "grid", gap: 18 }}>
                  {adminStaffData.admins.map((adm: any) => (
                    <article
                      key={adm.id}
                      style={{
                        padding: 18,
                        border: "1px solid var(--line)",
                        borderRadius: "var(--radius-sm)",
                        display: "grid",
                        gap: 14,
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
                        <div>
                          <strong style={{ fontSize: 15 }}>
                            {`${adm.first_name ?? ""} ${adm.last_name ?? ""}`.trim() || adm.email}
                          </strong>
                          <span style={{ marginLeft: 10, fontSize: 12, color: "var(--slate)" }}>
                            {adm.email} · {adm.granted_count}/16 permissions active
                          </span>
                        </div>
                        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                          <StatusPill tone={adm.is_active ? "success" : "danger"}>
                            {adm.status}
                          </StatusPill>
                          {adm.is_active ? (
                            <Button size="sm" variant="secondary" onClick={() => void updateAdminStaffStatus(adm.id, "suspend")}>
                              Suspend
                            </Button>
                          ) : (
                            <Button size="sm" variant="primary" onClick={() => void updateAdminStaffStatus(adm.id, "activate")}>
                              Activate
                            </Button>
                          )}
                          <Button size="sm" variant="danger" onClick={() => void updateAdminStaffStatus(adm.id, "remove")}>
                            Remove Admin
                          </Button>
                        </div>
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                        {Object.entries(adminStaffPermissionLabels).map(([permKey, permLabel]) => {
                          const granted = Boolean(adm.permissions?.[permKey]);
                          return (
                            <Button
                              key={permKey}
                              size="sm"
                              variant={granted ? "primary" : "secondary"}
                              onClick={() => void toggleAdminStaffPermission(adm.id, permKey, !granted)}
                            >
                              {granted ? "✓ " : "+ "}
                              {permLabel}
                            </Button>
                          );
                        })}
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState title="No Admin staff accounts yet">
                  Create an Admin staff account above and assign only the permissions required for their role.
                </EmptyState>
              )}
            </CardBody>
          </Card>

          <Card style={{ marginBottom: 24 }}>
            <CardHeader
              title="Platform-Owned SHOPLEX Products"
              subtitle="All products uploaded by Owner or authorized Admin staff are owned by SHOPLEX Official with creator & source tracked separately."
              action={<Badge tone="gold">{platformProducts.length} platform items</Badge>}
            />
            <CardBody>
              {platformProducts.length ? (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Product</th>
                        <th>Product Owner</th>
                        <th>Created By</th>
                        <th>Source</th>
                        <th>Price</th>
                        <th>Stock</th>
                        <th>Status</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {platformProducts.map((p: any) => (
                        <tr key={p.id}>
                          <td>
                            <strong>{p.name}</strong>
                            <span style={{ display: "block", fontSize: 11, color: "var(--slate)" }}>
                              {p.category_name} · SKU: {p.sku}
                            </span>
                          </td>
                          <td>
                            <Badge tone="gold">{p.product_owner}</Badge>
                          </td>
                          <td style={{ fontSize: 12 }}>{p.created_by_email || "Owner"}</td>
                          <td style={{ fontSize: 12 }}>
                            {p.product_source === "supplier"
                              ? `Supplier${p.supplier_name ? ` (${p.supplier_name})` : ""}`
                              : "Owner / Platform"}
                          </td>
                          <td>{money(p.price)}</td>
                          <td>{p.stock_quantity}</td>
                          <td>
                            <StatusPill tone={p.status === "published" ? "success" : "warning"}>
                              {p.status.replaceAll("_", " ")}
                            </StatusPill>
                          </td>
                          <td>
                            {p.status !== "published" ? (
                              <Button size="sm" onClick={() => void publishPlatformProduct(p.id)}>
                                Publish
                              </Button>
                            ) : (
                              <span style={{ fontSize: 12, color: "var(--slate)" }}>Live</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="No platform-owned products yet">
                  Upload a SHOPLEX Official product above or grant an Admin staff member product creation permission.
                </EmptyState>
              )}
            </CardBody>
          </Card>
        </>
      )}
    </PortalShell>
  );
}
