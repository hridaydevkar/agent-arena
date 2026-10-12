import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  Database,
  FileSearch,
  Layers3,
  Loader2,
  Terminal,
  X,
} from "lucide-react";
import type { Agent } from "./types";

export function Mark({ small = false }: { small?: boolean }) {
  return (
    <span className={`brand-mark ${small ? "small" : ""}`}>
      <svg viewBox="0 0 32 32" fill="none">
        <path d="M6 24 16 7l10 17h-7l-3-6-3 6H6Z" fill="currentColor" />
        <path d="m16 7 4.1 7H12L16 7Z" fill="#e0efc5" />
      </svg>
    </span>
  );
}
export function AgentAvatar({
  agent,
  size = "",
}: {
  agent?: Partial<Agent>;
  size?: string;
}) {
  const name = agent?.name || "?";
  return (
    <span
      className={`agent-avatar ${size}`}
      style={
        { "--agent-color": agent?.color || "#6e7a84" } as React.CSSProperties
      }
    >
      <svg viewBox="0 0 32 32" fill="none">
        <path
          d={
            name.charCodeAt(0) % 3 === 0
              ? "M16 5 27 24H5L16 5Zm0 8-6 11m6-11 6 11M10 16h12"
              : name.charCodeAt(0) % 3 === 1
                ? "m16 5 11 6v10l-11 6-11-6V11l11-6Zm0 0v22M5 11l22 10M27 11 5 21"
                : "M8 7h16v18H8V7Zm-3 6h22M5 19h22M13 4v24M19 4v24"
          }
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}
export function CategoryIcon({
  name,
  size = 18,
}: {
  name: string;
  size?: number;
}) {
  return name === "Data analysis" ? (
    <Database size={size} />
  ) : name === "Research" ? (
    <FileSearch size={size} />
  ) : (
    <Layers3 size={size} />
  );
}
export function Badge({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action && <div className="heading-actions">{action}</div>}
    </div>
  );
}
export function Empty({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Terminal size={25} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
export function Loading({ text = "Loading workspace…" }: { text?: string }) {
  return (
    <div className="loading">
      <Loader2 size={24} className="spin" />
      <span>{text}</span>
    </div>
  );
}
export function Modal({
  children,
  title,
  subtitle,
  onClose,
  wide = false,
}: {
  children: ReactNode;
  title: string;
  subtitle?: string;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const original = document.activeElement as HTMLElement;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    ref.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeRef.current();
      if (e.key === "Tab") {
        const nodes = ref.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]),input:not([disabled]),select,textarea,a[href],[tabindex="0"]',
        );
        if (!nodes?.length) return;
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (
          e.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === ref.current)
        ) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.body.style.overflow = prev;
      document.removeEventListener("keydown", key);
      original?.focus();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className={`modal ${wide ? "wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        ref={ref}
        tabIndex={-1}
      >
        <div className="modal-head">
          <div>
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <button
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
export function CheckMark({ checked }: { checked: boolean }) {
  return (
    <span className={`checkbox ${checked ? "checked" : ""}`}>
      {checked && <Check size={12} />}
    </span>
  );
}
export function TextLink({
  children,
  onClick,
  external = false,
}: {
  children: ReactNode;
  onClick: () => void;
  external?: boolean;
}) {
  return (
    <button className="text-link" onClick={onClick}>
      {children}
      {external ? <ArrowUpRight size={15} /> : <ChevronRight size={15} />}
    </button>
  );
}
export function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre className="json-block">
      {typeof value === "string"
        ? value
        : (JSON.stringify(value, null, 2) ?? "null")}
    </pre>
  );
}
