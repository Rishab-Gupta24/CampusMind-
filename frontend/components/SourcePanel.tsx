"use client";

import { ExternalLink, Play, ScrollText, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Badge } from "@/components/Badge";
import { allBadges } from "@/components/SourceChip";
import { api, type SourceRef } from "@/lib/api";
import { formatTime, ROLE_TITLE, sourceLabel } from "@/lib/format";

export function SourcePanel({ source, onClose }: { source: SourceRef | null; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const [pdf, setPdf] = useState<{ chunkId: string; url: string } | null>(null);

  useEffect(() => {
    if (!source) return;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [source, onClose]);

  useEffect(() => {
    if (!source || source.kind === "lecture") return;
    let cancelled = false;
    api
      .document(source.source_id)
      .then((doc) => {
        if (!cancelled && doc.file_url) {
          const url = source.page ? `${doc.file_url}#page=${source.page}` : doc.file_url;
          setPdf({ chunkId: source.chunk_id, url });
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [source]);

  if (!source) return null;
  const pdfUrl = pdf?.chunkId === source.chunk_id ? pdf.url : null;
  const isLecture = source.kind === "lecture";
  const t = Math.floor(source.start_s ?? 0);

  return (
    <>
      <button
        type="button"
        aria-label="Close source"
        onClick={onClose}
        className="fixed inset-0 z-40 cursor-default bg-black/10 md:bg-transparent"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`Source ${source.n}`}
        className="glass glass-strong fixed inset-x-2 bottom-2 z-50 flex max-h-[75dvh] flex-col p-5 md:inset-x-auto md:top-20 md:right-4 md:bottom-4 md:max-h-none md:w-[400px]"
      >
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-[13px] text-text-2">Source {source.n}</p>
            <h2 className="mt-1 text-[17px] leading-snug font-semibold tabular-nums">{sourceLabel(source)}</h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex size-11 shrink-0 items-center justify-center rounded-chip text-text-2 hover:bg-surface-2"
          >
            <X size={20} strokeWidth={1.5} />
          </button>
        </div>

        {allBadges(source).length ? (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {allBadges(source).map((b) => (
              <Badge key={b} name={b} />
            ))}
          </div>
        ) : null}

        {source.instructor ? (
          <p className="mt-3 text-[15px] text-text-2">
            {source.instructor.name} · {ROLE_TITLE[source.instructor.role]}
          </p>
        ) : null}
        {source.flag_reason ? (
          <p className="mt-2 rounded-card bg-flag-soft px-3 py-2 text-[15px] text-text">
            <span className="text-flag">Flagged:</span> {source.flag_reason}
          </p>
        ) : null}

        <div className="mt-4 min-h-0 flex-1 overflow-y-auto rounded-card bg-surface p-4">
          <p className="text-[15px] leading-relaxed whitespace-pre-line text-text">{source.excerpt}</p>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {isLecture ? (
            <>
              <Link
                href={`/lectures/${source.source_id}?t=${t}&play=1`}
                className="flex h-10 items-center gap-2 rounded-chip bg-accent px-4 text-[15px] font-semibold text-white hover:bg-accent/90"
              >
                <Play aria-hidden size={16} strokeWidth={1.75} /> Play from {formatTime(t)}
              </Link>
              <Link
                href={`/lectures/${source.source_id}?t=${t}`}
                className="flex h-10 items-center gap-2 rounded-chip bg-surface-2 px-4 text-[15px] text-text hover:bg-border/60"
              >
                <ScrollText aria-hidden size={16} strokeWidth={1.5} /> Open transcript
              </Link>
            </>
          ) : pdfUrl ? (
            <a
              href={pdfUrl}
              target="_blank"
              rel="noreferrer"
              className="flex h-10 items-center gap-2 rounded-chip bg-surface-2 px-4 text-[15px] text-text hover:bg-border/60"
            >
              <ExternalLink aria-hidden size={16} strokeWidth={1.5} />
              {source.page ? `Open PDF at page ${source.page}` : "Open PDF"}
            </a>
          ) : null}
        </div>
      </aside>
    </>
  );
}
