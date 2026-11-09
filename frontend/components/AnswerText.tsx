import { Fragment } from "react";

import type { SourceRef } from "@/lib/api";

const CITATION = /\[(\d+)\]/g;

/** Answer text with `[n]` rendered as small accent superscripts that open the matching source. */
export function AnswerText({
  text,
  sources,
  onCite,
}: {
  text: string;
  sources: SourceRef[];
  onCite: (source: SourceRef) => void;
}) {
  const byN = new Map(sources.map((s) => [s.n, s]));
  const paragraphs = text.split(/\n{2,}/).filter((p) => p.trim());
  return (
    <>
      {paragraphs.map((para, i) => {
        const parts: React.ReactNode[] = [];
        let last = 0;
        for (const match of para.matchAll(CITATION)) {
          const index = match.index ?? 0;
          if (index > last) parts.push(para.slice(last, index));
          const n = Number(match[1]);
          const source = byN.get(n);
          parts.push(
            source ? (
              <sup key={`${index}-${n}`} className="ml-0.5">
                <button
                  type="button"
                  onClick={() => onCite(source)}
                  aria-label={`Source ${n}`}
                  className="rounded px-0.5 text-[12px] font-semibold text-accent tabular-nums hover:bg-accent-soft"
                >
                  {n}
                </button>
              </sup>
            ) : (
              <sup key={`${index}-${n}`} className="ml-0.5 text-[12px] text-accent tabular-nums">
                {n}
              </sup>
            ),
          );
          last = index + match[0].length;
        }
        if (last < para.length) parts.push(para.slice(last));
        return (
          <p key={i} className="mb-3 last:mb-0">
            {parts.map((part, j) => (
              <Fragment key={j}>{part}</Fragment>
            ))}
          </p>
        );
      })}
    </>
  );
}
