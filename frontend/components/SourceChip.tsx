import { AudioLines, FileText } from "lucide-react";

import { Badge } from "@/components/Badge";
import type { BadgeName, SourceRef } from "@/lib/api";
import { sourceLabel } from "@/lib/format";

// design.md §7.2: max three badges, ordered Flagged, IC/HOD, Official, Your section.
const ORDER: BadgeName[] = ["Flagged", "IC", "HOD", "Official", "Your section"];

export function visibleBadges(badges: BadgeName[]): BadgeName[] {
  return [...badges].sort((a, b) => ORDER.indexOf(a) - ORDER.indexOf(b)).slice(0, 3);
}

export function SourceChip({ source, onOpen }: { source: SourceRef; onOpen: (s: SourceRef) => void }) {
  const Icon = source.kind === "lecture" ? AudioLines : FileText;
  const label = sourceLabel(source);
  const hidden = source.badges.length - visibleBadges(source.badges).length;
  return (
    <button
      type="button"
      onClick={() => onOpen(source)}
      aria-label={`Source ${source.n}: ${label}${source.badges.length ? `, ${source.badges.join(", ")}` : ""}`}
      className="flex min-h-11 max-w-full items-center gap-2 rounded-chip bg-surface-2 px-3 py-1.5 text-left text-[13px] transition-colors duration-150 ease-standard hover:bg-border/60"
    >
      <span className="tabular-nums text-accent">{source.n}</span>
      <Icon aria-hidden size={16} strokeWidth={1.5} className="shrink-0 text-text-2" />
      <span className="min-w-0 truncate tabular-nums text-text">{label}</span>
      {visibleBadges(source.badges).map((b) => (
        <Badge key={b} name={b} />
      ))}
      {hidden > 0 ? <span className="text-text-2">+{hidden}</span> : null}
    </button>
  );
}
