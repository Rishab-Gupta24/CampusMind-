"use client";

import clsx from "clsx";
import { useId, useRef } from "react";

export function LoadingDots({ label = "Loading" }: { label?: string }) {
  return (
    <span role="status" aria-label={label} className="inline-flex items-center gap-1 py-2">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="size-1.5 animate-pulse rounded-full bg-text-2"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </span>
  );
}

export interface Option<T extends string> {
  value: T;
  label: string;
}

/** Segmented control (design.md §8): track surface-2, selected pill surface with 1 px border. */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-chip bg-surface-2 p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={clsx(
            "h-9 rounded-[8px] border px-3 text-[13px] transition-colors duration-150 ease-standard",
            value === o.value
              ? "border-border bg-surface font-semibold text-text"
              : "border-transparent text-text-2 hover:text-text",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Accessible tabs with arrow-key navigation. */
export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
  label,
}: {
  tabs: Option<T>[];
  value: T;
  onChange: (value: T) => void;
  label: string;
}) {
  const id = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (e: React.KeyboardEvent, index: number) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const next = (index + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    onChange(tabs[next].value);
    refs.current[next]?.focus();
  };
  return (
    <div role="tablist" aria-label={label} className="flex gap-1 overflow-x-auto border-b border-border [scrollbar-width:none]">
      {tabs.map((t, i) => (
        <button
          key={t.value}
          ref={(el) => {
            refs.current[i] = el;
          }}
          id={`${id}-${t.value}`}
          type="button"
          role="tab"
          aria-selected={value === t.value}
          tabIndex={value === t.value ? 0 : -1}
          onClick={() => onChange(t.value)}
          onKeyDown={(e) => onKey(e, i)}
          className={clsx(
            "-mb-px h-11 shrink-0 border-b-2 px-3 text-[15px] whitespace-nowrap transition-colors duration-150",
            value === t.value ? "border-accent font-semibold text-text" : "border-transparent text-text-2 hover:text-text",
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function ErrorNote({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="rounded-card border border-border bg-surface px-4 py-3 text-[15px] text-danger">
      {children}
    </p>
  );
}

export function EmptyNote({ children }: { children: React.ReactNode }) {
  return <p className="rounded-card bg-surface px-4 py-6 text-center text-[15px] text-text-2">{children}</p>;
}

export function StatusText({ status, stage }: { status: string; stage?: string | null }) {
  const stageLabel: Record<string, string> = {
    preparing: "Preparing…",
    transcribing: "Transcribing…",
    flagging: "Finding important moments…",
    indexing: "Indexing…",
    notes: "Writing notes…",
  };
  if (status === "ready") return <span className="text-[13px] text-good">Ready</span>;
  if (status === "failed") return <span className="text-[13px] text-danger">Failed</span>;
  return <span className="text-[13px] text-text-2">{(stage && stageLabel[stage]) || "Processing…"}</span>;
}

export const inputClass =
  "h-11 w-full rounded-card bg-surface-2 px-3 text-[15px] text-text outline-none focus-visible:outline-2 focus-visible:outline-accent";
