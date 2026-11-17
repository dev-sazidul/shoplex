"use client";

import { useEffect, useId, useRef } from "react";
import type { ReactNode, ButtonHTMLAttributes, InputHTMLAttributes } from "react";

export function Button({ variant = "primary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "quiet" }) {
  return <button type="button" className={`button button--${variant} ${className}`} {...props} />;
}

export function TextInput({ label, error, id, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string }) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <label className="field" htmlFor={inputId}>
      <span className="field__label">{label}</span>
      <input id={inputId} className={`field__input${error ? " field__input--error" : ""}`} aria-invalid={Boolean(error)} aria-describedby={error ? `${inputId}-error` : undefined} {...props} />
      {error && <span className="field__error" id={`${inputId}-error`}>{error}</span>}
    </label>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`surface ${className}`}>{children}</section>;
}

export function StatusPill({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "success" | "warning" | "danger" }) {
  return <span className={`status-pill status-pill--${tone}`}>{children}</span>;
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return <div className="state state--loading" role="status"><span className="spinner" aria-hidden="true" />{label}</div>;
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="state state--empty"><span className="state__mark" aria-hidden="true">—</span><strong>{title}</strong>{children && <p>{children}</p>}</div>;
}

export function ErrorState({ title = "Something went wrong", children }: { title?: string; children?: ReactNode }) {
  return <div className="state state--error" role="alert"><strong>{title}</strong>{children && <p>{children}</p>}</div>;
}

export function Notification({ title, children, tone = "info" }: { title: string; children: ReactNode; tone?: "info" | "success" | "warning" }) {
  return <aside className={`notice notice--${tone}`} role="status"><strong>{title}</strong><div>{children}</div></aside>;
}

export function DataTable<T extends { id: string }>({ columns, rows, emptyMessage = "No records yet" }: {
  columns: Array<{ key: keyof T; label: string; render?: (row: T) => ReactNode }>;
  rows: T[];
  emptyMessage?: string;
}) {
  if (!rows.length) return <EmptyState title={emptyMessage} />;
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead><tr>{columns.map((column) => <th key={String(column.key)} scope="col">{column.label}</th>)}</tr></thead>
        <tbody>{rows.map((row) => <tr key={row.id}>{columns.map((column) => <td key={String(column.key)}>{column.render ? column.render(row) : String(row[column.key] ?? "")}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

export function Modal({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);
  return <dialog ref={dialogRef} className="dialog" aria-labelledby="dialog-title" onClose={onClose} onCancel={(event) => { event.preventDefault(); onClose(); }}>
    <div className="dialog__header"><h2 id="dialog-title">{title}</h2><Button variant="quiet" aria-label="Close dialog" onClick={onClose}>Close</Button></div>
    <div className="dialog__content">{children}</div>
  </dialog>;
}

export function Sidebar({ items, active }: { items: Array<{ label: string; href: string }>; active?: string }) {
  return <nav className="sidebar" aria-label="Portal navigation"><ul>{items.map((item) => <li key={item.href}><a className={active === item.href ? "sidebar__link is-active" : "sidebar__link"} href={item.href}>{item.label}</a></li>)}</ul></nav>;
}
