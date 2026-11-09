"use client";

import clsx from "clsx";
import { Star } from "lucide-react";
import { useEffect, useRef } from "react";

import type { FlaggedMoment, TranscriptLine } from "@/lib/api";
import { formatTime } from "@/lib/format";

export function Transcript({
  lines,
  highlight,
  onSeek,
}: {
  lines: TranscriptLine[];
  highlight: number | null;
  onSeek: (seconds: number) => void;
}) {
  const refs = useRef<(HTMLLIElement | null)[]>([]);

  useEffect(() => {
    if (highlight === null) return;
    refs.current[highlight]?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [highlight]);

  return (
    <ol className="flex flex-col overflow-hidden rounded-card bg-surface py-2">
      {lines.map((line, i) => (
        <li
          key={`${line.start_s}-${i}`}
          ref={(el) => {
            refs.current[i] = el;
          }}
          className={clsx(
            "flex gap-3 border-l-2 px-4 py-1.5 transition-colors duration-[1500ms] ease-standard",
            line.flagged ? "border-flag bg-flag-soft" : "border-transparent",
            highlight === i && "bg-accent-soft duration-150",
          )}
        >
          <button
            type="button"
            onClick={() => onSeek(line.start_s)}
            aria-label={`Play from ${formatTime(line.start_s)}`}
            className="w-12 shrink-0 pt-0.5 text-left text-[13px] text-text-2 tabular-nums hover:text-accent"
          >
            {formatTime(line.start_s)}
          </button>
          <p className="flex-1 text-[17px] leading-relaxed">
            {line.flagged ? (
              <Star
                aria-label="Flagged by instructor"
                size={12}
                strokeWidth={1.75}
                className="mr-1.5 inline -translate-y-px text-flag"
              />
            ) : null}
            {line.text}
          </p>
        </li>
      ))}
    </ol>
  );
}

export function FlaggedList({
  moments,
  onOpen,
  showLecture = false,
}: {
  moments: FlaggedMoment[];
  onOpen: (moment: FlaggedMoment) => void;
  showLecture?: boolean;
}) {
  return (
    <ul className="flex flex-col divide-y divide-border overflow-hidden rounded-card bg-surface">
      {moments.map((m) => (
        <li key={`${m.source_id}-${m.start_s}`}>
          <button
            type="button"
            onClick={() => onOpen(m)}
            className="flex w-full gap-3 px-4 py-3.5 text-left transition-colors duration-150 hover:bg-surface-2"
          >
            <Star aria-hidden size={16} strokeWidth={1.75} className="mt-1 shrink-0 text-flag" />
            <span className="min-w-0 flex-1">
              <span className="block text-[17px] text-text">{m.reason}</span>
              <span className="mt-1 block text-[15px] text-text-2">“{m.quote}”</span>
              <span className="mt-1.5 block text-[13px] text-text-2 tabular-nums">
                {showLecture ? `${m.title} · ` : ""}
                {formatTime(m.start_s)}
              </span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
