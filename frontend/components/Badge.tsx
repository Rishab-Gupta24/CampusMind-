import clsx from "clsx";
import { Star } from "lucide-react";

import type { BadgeName, Role } from "@/lib/api";
import { ROLE_LABEL, ROLE_TITLE } from "@/lib/format";

const TOOLTIP: Record<BadgeName, string> = {
  Official: "From an official course handout or campus regulation",
  IC: "Said by the Instructor-in-Charge",
  HOD: "Said by the Head of Department",
  Flagged: "Flagged by the instructor as important",
  "Your section": "From your own section",
  Scanned: "Read from a scan or handwriting by OCR. Check the original page for exact wording.",
};

export function Badge({ name, title }: { name: BadgeName; title?: string }) {
  const tip = title ?? TOOLTIP[name];
  return (
    <span
      title={tip}
      aria-label={tip}
      className={clsx(
        "inline-flex h-[22px] shrink-0 items-center gap-1 rounded-chip px-2 text-[13px] leading-none whitespace-nowrap",
        name === "Flagged" && "bg-flag-soft text-flag",
        name === "Your section" && "bg-accent-soft text-accent",
        name !== "Flagged" && name !== "Your section" && "border border-border bg-surface text-text-2",
      )}
    >
      {name === "Flagged" ? <Star aria-hidden size={12} strokeWidth={1.75} /> : null}
      {name}
    </span>
  );
}

export function RoleBadge({ role }: { role: Role }) {
  return (
    <span
      title={ROLE_TITLE[role]}
      className="inline-flex h-[22px] items-center rounded-chip border border-border bg-surface px-2 text-[13px] leading-none text-text-2"
    >
      {ROLE_LABEL[role]}
    </span>
  );
}

export function KindBadge({ kind }: { kind: string }) {
  const label: Record<string, string> = {
    campus: "Campus rule",
    handout: "Course handout",
    material: "Course material",
    lecture: "Lecture",
  };
  return (
    <span className="inline-flex h-[22px] items-center rounded-chip border border-border bg-surface px-2 text-[13px] leading-none whitespace-nowrap text-text-2">
      {label[kind] ?? kind}
    </span>
  );
}
