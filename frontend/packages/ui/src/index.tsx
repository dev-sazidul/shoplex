"use client";

import { useEffect, useId, useRef, useState } from "react";
import type {
  ButtonHTMLAttributes,
  HTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

export type ButtonVariant = "primary" | "secondary" | "quiet" | "gold" | "danger" | "cobalt";
export type ButtonSize = "sm" | "md" | "lg";

export type IconName =
  | "search"
  | "bag"
  | "heart"
  | "user"
  | "star"
  | "shield"
  | "truck"
  | "sparkles"
  | "store"
  | "grid"
  | "box"
  | "orders"
  | "chart"
  | "wallet"
  | "settings"
  | "bell"
  | "check"
  | "alert"
  | "arrow-up-right"
  | "chevron-right"
  | "close"
  | "eye"
  | "refresh"
  | "tag";

export function Icon({
  name,
  size = 18,
  className = "",
}: {
  name: IconName;
  size?: number;
  className?: string;
}) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.75,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className: `lx-icon ${className}`.trim(),
    "aria-hidden": true as const,
  };
  switch (name) {
    case "search":
      return (
        <svg {...common}>
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
      );
    case "bag":
      return (
        <svg {...common}>
          <path d="M6 7h12l1 13H5L6 7Z" />
          <path d="M9 7V5a3 3 0 0 1 6 0v2" />
        </svg>
      );
    case "heart":
      return (
        <svg {...common}>
          <path d="M12 20.5s-7-4.35-7-10a4.2 4.2 0 0 1 7-3.1 4.2 4.2 0 0 1 7 3.1c0 5.65-7 10-7 10Z" />
        </svg>
      );
    case "user":
      return (
        <svg {...common}>
          <circle cx="12" cy="8" r="4" />
          <path d="M5 20a7 7 0 0 1 14 0" />
        </svg>
      );
    case "star":
      return (
        <svg {...common} fill="currentColor">
          <path d="m12 2.5 2.85 5.78 6.38.93-4.61 4.5 1.09 6.35L12 17.06l-5.71 3 1.09-6.35-4.61-4.5 6.38-.93L12 2.5Z" />
        </svg>
      );
    case "shield":
      return (
        <svg {...common}>
          <path d="M12 3 5 6v6c0 4.5 3 7.9 7 9 4-1.1 7-4.5 7-9V6l-7-3Z" />
          <path d="m9.5 12 1.8 1.8 3.5-3.6" />
        </svg>
      );
    case "truck":
      return (
        <svg {...common}>
          <path d="M3 6h11v10H3z" />
          <path d="M14 9h4l3 3v4h-7z" />
          <circle cx="7.5" cy="17.5" r="1.8" />
          <circle cx="17.5" cy="17.5" r="1.8" />
        </svg>
      );
    case "sparkles":
      return (
        <svg {...common}>
          <path d="m12 3 1.8 4.7L18.5 9l-4.7 1.3L12 15l-1.8-4.7L5.5 9l4.7-1.3L12 3Z" />
          <path d="m18 15 .8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2Z" />
        </svg>
      );
    case "store":
      return (
        <svg {...common}>
          <path d="M4 7h16l-1.5 4.5a2.5 2.5 0 0 1-2.4 1.7H7.9a2.5 2.5 0 0 1-2.4-1.7L4 7Z" />
          <path d="M5 13v7h14v-7" />
          <path d="M9 20v-4h6v4" />
        </svg>
      );
    case "grid":
      return (
        <svg {...common}>
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" />
        </svg>
      );
    case "box":
      return (
        <svg {...common}>
          <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z" />
          <path d="m4 7.5 8 4.5 8-4.5" />
          <path d="M12 12v9" />
        </svg>
      );
    case "orders":
      return (
        <svg {...common}>
          <rect x="5" y="3" width="14" height="18" rx="2" />
          <path d="M9 8h6M9 12h6M9 16h4" />
        </svg>
      );
    case "chart":
      return (
        <svg {...common}>
          <path d="M4 19h16" />
          <path d="M7 15v-5M12 15V7M17 15v-8" />
        </svg>
      );
    case "wallet":
      return (
        <svg {...common}>
          <rect x="3" y="6" width="18" height="13" rx="2" />
          <path d="M15 12.5h5" />
          <path d="M3 9h18" />
        </svg>
      );
    case "settings":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="3" />
          <path d="M12 3v2M12 19v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M3 12h2M19 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      );
    case "bell":
      return (
        <svg {...common}>
          <path d="M6 9a6 6 0 1 1 12 0c0 5 2 6.5 2 6.5H4S6 14 6 9Z" />
          <path d="M10 19a2 2 0 0 0 4 0" />
        </svg>
      );
    case "check":
      return (
        <svg {...common}>
          <path d="m5 12.5 4.5 4.5L19 7.5" />
        </svg>
      );
    case "alert":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v4.5M12 16h.01" />
        </svg>
      );
    case "arrow-up-right":
      return (
        <svg {...common}>
          <path d="M7 17 17 7M9 7h8v8" />
        </svg>
      );
    case "chevron-right":
      return (
        <svg {...common}>
          <path d="m9 6 6 6-6 6" />
        </svg>
      );
    case "close":
      return (
        <svg {...common}>
          <path d="M6 6l12 12M18 6 6 18" />
        </svg>
      );
    case "eye":
      return (
        <svg {...common}>
          <path d="M2.5 12S6 6 12 6s9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
          <circle cx="12" cy="12" r="2.8" />
        </svg>
      );
    case "refresh":
      return (
        <svg {...common}>
          <path d="M20 11a8 8 0 1 0-2.3 5.7" />
          <path d="M20 4v7h-7" />
        </svg>
      );
    case "tag":
      return (
        <svg {...common}>
          <path d="M12 3H5a2 2 0 0 0-2 2v7l8.5 8.5a2 2 0 0 0 2.8 0l6.2-6.2a2 2 0 0 0 0-2.8L12 3Z" />
          <circle cx="7.5" cy="7.5" r="1" />
        </svg>
      );
  }
}

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
}) {
  return (
    <button
      type="button"
      className={`button button--${variant} button--${size} ${className}`.trim()}
      {...props}
    />
  );
}

export function TextInput({
  label,
  error,
  hint,
  id,
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  hint?: string;
}) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;
  return (
    <label className={`field ${className}`.trim()} htmlFor={inputId}>
      <span className="field__label">{label}</span>
      <input
        id={inputId}
        className={`field__input${error ? " field__input--error" : ""}`}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy}
        {...props}
      />
      {hint && !error && (
        <span className="field__hint" id={`${inputId}-hint`}>
          {hint}
        </span>
      )}
      {error && (
        <span className="field__error" id={`${inputId}-error`}>
          {error}
        </span>
      )}
    </label>
  );
}

export function SelectInput({
  label,
  error,
  options,
  id,
  className = "",
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  error?: string;
  options: Array<{ value: string; label: string }>;
}) {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  return (
    <label className={`field ${className}`.trim()} htmlFor={selectId}>
      <span className="field__label">{label}</span>
      <select
        id={selectId}
        className={`field__input field__select${error ? " field__input--error" : ""}`}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${selectId}-error` : undefined}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && (
        <span className="field__error" id={`${selectId}-error`}>
          {error}
        </span>
      )}
    </label>
  );
}

export function TextareaInput({
  label,
  error,
  id,
  className = "",
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  error?: string;
}) {
  const generatedId = useId();
  const textareaId = id ?? generatedId;
  return (
    <label className={`field ${className}`.trim()} htmlFor={textareaId}>
      <span className="field__label">{label}</span>
      <textarea
        id={textareaId}
        className={`field__input field__textarea${error ? " field__input--error" : ""}`}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${textareaId}-error` : undefined}
        {...props}
      />
      {error && (
        <span className="field__error" id={`${textareaId}-error`}>
          {error}
        </span>
      )}
    </label>
  );
}

export function Checkbox({
  label,
  id,
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const generatedId = useId();
  const checkboxId = id ?? generatedId;
  return (
    <label className={`checkbox-field ${className}`.trim()} htmlFor={checkboxId}>
      <input id={checkboxId} type="checkbox" className="checkbox-field__input" {...props} />
      <span className="checkbox-field__label">{label}</span>
    </label>
  );
}

export function Card({
  children,
  className = "",
  ...props
}: HTMLAttributes<HTMLElement> & { children: ReactNode; className?: string }) {
  return (
    <section className={`surface ${className}`.trim()} {...props}>
      {children}
    </section>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <header className="surface__header">
      <div>
        <h3 className="surface__title">{title}</h3>
        {subtitle && <p className="surface__subtitle">{subtitle}</p>}
      </div>
      {action && <div className="surface__action">{action}</div>}
    </header>
  );
}

export function CardBody({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`surface__body ${className}`.trim()}>{children}</div>;
}

export function CardFooter({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <footer className={`surface__footer ${className}`.trim()}>{children}</footer>;
}

export function StatusPill({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
}) {
  return <span className={`status-pill status-pill--${tone}`}>{children}</span>;
}

export function Badge({
  children,
  tone = "navy",
}: {
  children: ReactNode;
  tone?: "navy" | "indigo" | "gold" | "slate" | "cobalt";
}) {
  return <span className={`lx-badge lx-badge--${tone}`}>{children}</span>;
}

export function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span className="lx-tooltip" data-tooltip={label}>
      {children}
    </span>
  );
}

export function StatCard({
  label,
  value,
  meta,
  trend,
  icon,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  meta?: ReactNode;
  trend?: string;
  icon?: IconName;
  tone?: "default" | "navy" | "gold";
}) {
  return (
    <article className={`lx-stat lx-stat--${tone}`}>
      <div className="lx-stat__top">
        <span className="lx-stat__label">{label}</span>
        {icon && (
          <span className="lx-stat__icon">
            <Icon name={icon} size={16} />
          </span>
        )}
      </div>
      <div className="lx-stat__value">{value}</div>
      {(meta || trend) && (
        <div className="lx-stat__foot">
          {trend && <span className="lx-stat__trend">{trend}</span>}
          {meta && <span className="lx-stat__meta">{meta}</span>}
        </div>
      )}
    </article>
  );
}

export function AreaChart({
  data,
  height = 180,
  valuePrefix = "৳",
}: {
  data: Array<{ label: string; value: number; secondary?: number }>;
  height?: number;
  valuePrefix?: string;
}) {
  if (!data.length) return <EmptyState title="No trend data available" />;
  const width = 640;
  const padX = 24;
  const padY = 20;
  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const stepX = data.length > 1 ? (width - padX * 2) / (data.length - 1) : 0;
  const points = data.map((d, index) => {
    const x = padX + index * stepX;
    const y = height - padY - (d.value / maxVal) * (height - padY * 2);
    return { x, y, ...d };
  });
  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L${points[points.length - 1].x.toFixed(1)},${height - padY} L${points[0].x.toFixed(1)},${height - padY} Z`;

  return (
    <div className="lx-chart">
      <svg viewBox={`0 0 ${width} ${height}`} className="lx-chart__svg" role="img" aria-label="Performance trend chart">
        <defs>
          <linearGradient id="lxAreaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2563EB" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#2563EB" stopOpacity="0.0" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((ratio) => (
          <line
            key={ratio}
            x1={padX}
            x2={width - padX}
            y1={padY + (height - padY * 2) * ratio}
            y2={padY + (height - padY * 2) * ratio}
            stroke="#E5E2DC"
            strokeDasharray="3 3"
          />
        ))}
        <path d={areaPath} fill="url(#lxAreaGrad)" />
        <path d={linePath} fill="none" stroke="#2563EB" strokeWidth="2.25" strokeLinecap="round" />
        {points.map((point) => (
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} r="3.4" fill="#0F172A" stroke="#FFFFFF" strokeWidth="1.5">
              <title>{`${point.label}: ${valuePrefix}${point.value.toLocaleString()}`}</title>
            </circle>
          </g>
        ))}
      </svg>
      <div className="lx-chart__axis">
        <span>{data[0]?.label}</span>
        <span>{data[Math.floor(data.length / 2)]?.label}</span>
        <span>{data[data.length - 1]?.label}</span>
      </div>
    </div>
  );
}

export function BarChart({
  items,
}: {
  items: Array<{ label: string; value: number; tone?: "navy" | "cobalt" | "gold" | "success" }>;
}) {
  if (!items.length) return <EmptyState title="No distribution data" />;
  const max = Math.max(...items.map((item) => item.value), 1);
  return (
    <div className="lx-bars">
      {items.map((item) => {
        const pct = Math.max(4, Math.round((item.value / max) * 100));
        return (
          <div key={item.label} className="lx-bars__row">
            <div className="lx-bars__head">
              <span>{item.label.replaceAll("_", " ")}</span>
              <strong>{item.value.toLocaleString()}</strong>
            </div>
            <div className="lx-bars__track">
              <div className={`lx-bars__fill lx-bars__fill--${item.tone ?? "cobalt"}`} style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="state state--loading" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function Skeleton({
  width = "100%",
  height = "16px",
  className = "",
}: {
  width?: string;
  height?: string;
  className?: string;
}) {
  return <span className={`skeleton ${className}`.trim()} style={{ width, height }} aria-hidden="true" />;
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="state state--empty">
      <span className="state__mark" aria-hidden="true">
        —
      </span>
      <strong>{title}</strong>
      {children && <p>{children}</p>}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  children,
}: {
  title?: string;
  children?: ReactNode;
}) {
  return (
    <div className="state state--error" role="alert">
      <strong>{title}</strong>
      {children && <p>{children}</p>}
    </div>
  );
}

export function Notification({
  title,
  children,
  tone = "info",
}: {
  title: string;
  children: ReactNode;
  tone?: "info" | "success" | "warning" | "danger";
}) {
  return (
    <aside className={`notice notice--${tone}`} role="status">
      <strong>{title}</strong>
      <div>{children}</div>
    </aside>
  );
}

export function DataTable<T extends { id: string }>({
  columns,
  rows,
  emptyMessage = "No records yet",
  loading = false,
}: {
  columns: Array<{ key: keyof T; label: string; render?: (row: T) => ReactNode }>;
  rows: T[];
  emptyMessage?: string;
  loading?: boolean;
}) {
  if (loading) return <LoadingState label="Loading table data" />;
  if (!rows.length) return <EmptyState title={emptyMessage} />;
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={String(column.key)} scope="col">
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {columns.map((column) => (
                <td key={String(column.key)}>
                  {column.render ? column.render(row) : String(row[column.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Modal({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);
  return (
    <dialog
      ref={dialogRef}
      className="dialog"
      aria-labelledby="dialog-title"
      onClose={onClose}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="dialog__header">
        <h2 id="dialog-title">{title}</h2>
        <Button variant="quiet" size="sm" aria-label="Close dialog" onClick={onClose}>
          <Icon name="close" size={16} />
        </Button>
      </div>
      <div className="dialog__content">{children}</div>
    </dialog>
  );
}

export interface SidebarItem {
  label: string;
  href: string;
  badge?: string;
  icon?: IconName;
  onClick?: () => void;
}

export function Sidebar({
  items,
  active,
  onSelect,
}: {
  items: SidebarItem[];
  active?: string;
  onSelect?: (href: string) => void;
}) {
  return (
    <nav className="sidebar" aria-label="Portal navigation">
      <ul>
        {items.map((item) => {
          const isActive = active === item.href;
          return (
            <li key={item.href}>
              <a
                className={isActive ? "sidebar__link is-active" : "sidebar__link"}
                href={item.href}
                onClick={(event) => {
                  if (item.onClick) {
                    event.preventDefault();
                    item.onClick();
                  } else if (onSelect && item.href.startsWith("#")) {
                    event.preventDefault();
                    onSelect(item.href);
                  }
                }}
              >
                <span className="sidebar__label">
                  {item.icon && <Icon name={item.icon} size={16} />}
                  <span>{item.label}</span>
                </span>
                {item.badge && <Badge tone="gold">{item.badge}</Badge>}
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function Breadcrumbs({ items }: { items: Array<{ label: string; href?: string }> }) {
  return (
    <nav className="lx-breadcrumbs" aria-label="Breadcrumb">
      {items.map((item, index) => (
        <span key={`${item.label}-${index}`} className="lx-breadcrumbs__item">
          {index > 0 && <Icon name="chevron-right" size={12} />}
          {item.href ? <a href={item.href}>{item.label}</a> : <span aria-current="page">{item.label}</span>}
        </span>
      ))}
    </nav>
  );
}

export function TopNav({
  portalLabel,
  rightContent,
}: {
  portalLabel?: string;
  rightContent?: ReactNode;
}) {
  return (
    <header className="topbar">
      <div className="topbar__brand">
        <a className="wordmark" href="/" aria-label="SHOPLEX home">
          SHOP<span>LEX</span>
          <i>.</i>
        </a>
        {portalLabel && <Badge tone="navy">{portalLabel}</Badge>}
      </div>
      <div className="topbar__right">{rightContent}</div>
    </header>
  );
}

export function PortalShell({
  portalLabel,
  portalRole,
  title,
  subtitle,
  breadcrumbs,
  navItems,
  activeHref,
  onSelectNav,
  headerActions,
  userEmail,
  userName,
  notifications = [],
  onSignOut,
  children,
}: {
  portalLabel: string;
  portalRole?: string;
  title?: string;
  subtitle?: string;
  breadcrumbs?: Array<{ label: string; href?: string }>;
  navItems: SidebarItem[];
  activeHref?: string;
  onSelectNav?: (href: string) => void;
  headerActions?: ReactNode;
  userEmail?: string;
  userName?: string;
  notifications?: Array<{ id: string; title: string; body?: string; read_at?: string | null }>;
  onSignOut?: () => void;
  children: ReactNode;
}) {
  const [showNotif, setShowNotif] = useState(false);
  const unreadCount = notifications.filter((n) => !n.read_at).length;

  return (
    <div className="lx-dashboard">
      <aside className="lx-dashboard__sidebar">
        <div className="lx-dashboard__brand">
          <a className="wordmark wordmark--light" href="/">
            SHOP<span>LEX</span>
            <i>.</i>
          </a>
          <span className="lx-dashboard__portal-tag">{portalRole ?? portalLabel}</span>
        </div>
        <Sidebar items={navItems} active={activeHref} onSelect={onSelectNav} />
        <div className="lx-dashboard__sidebar-foot">
          <span>One Marketplace.</span>
          <small>Endless Opportunities.</small>
        </div>
      </aside>

      <div className="lx-dashboard__content">
        <header className="lx-dashboard__topbar">
          <div className="lx-dashboard__topbar-left">
            {breadcrumbs ? (
              <Breadcrumbs items={breadcrumbs} />
            ) : (
              <span className="lx-dashboard__domain">{portalLabel}</span>
            )}
          </div>
          <div className="lx-dashboard__topbar-right">
            {headerActions}
            <div className="lx-notif-wrap">
              <button
                type="button"
                className="lx-icon-btn"
                aria-label="Notifications"
                onClick={() => setShowNotif((prev) => !prev)}
              >
                <Icon name="bell" size={17} />
                {unreadCount > 0 && <span className="lx-notif-dot">{unreadCount}</span>}
              </button>
              {showNotif && (
                <div className="lx-popover" role="dialog" aria-label="Notifications">
                  <div className="lx-popover__head">
                    <strong>Notifications</strong>
                    <Badge tone="slate">{notifications.length}</Badge>
                  </div>
                  {notifications.length ? (
                    <ul className="lx-popover__list">
                      {notifications.slice(0, 5).map((item) => (
                        <li key={item.id}>
                          <strong>{item.title}</strong>
                          {item.body && <p>{item.body}</p>}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="lx-popover__empty">No new notifications.</p>
                  )}
                </div>
              )}
            </div>
            {userEmail ? (
              <div className="lx-profile-pill">
                <span className="lx-profile-pill__avatar">
                  {(userName || userEmail).slice(0, 1).toUpperCase()}
                </span>
                <div className="lx-profile-pill__info">
                  <strong>{userName || "Account"}</strong>
                  <small>{userEmail}</small>
                </div>
                {onSignOut && (
                  <Button variant="quiet" size="sm" onClick={onSignOut}>
                    Sign out
                  </Button>
                )}
              </div>
            ) : (
              <Button size="sm" onClick={() => window.location.assign("/login")}>
                Sign in
              </Button>
            )}
          </div>
        </header>

        <main className="lx-dashboard__main">
          {(title || subtitle) && (
            <div className="lx-page-header">
              <div>
                {title && <h1 className="lx-page-header__title">{title}</h1>}
                {subtitle && <p className="lx-page-header__subtitle">{subtitle}</p>}
              </div>
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}
