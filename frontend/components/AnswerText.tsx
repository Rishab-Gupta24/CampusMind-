"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import type { SourceRef } from "@/lib/api";

const CITE_PREFIX = "#cite-";

/** Turn `[n]` outside math into Markdown links the renderer shows as superscript citation buttons. */
function linkCitations(text: string): string {
  return text
    .split(/(\$\$[\s\S]*?\$\$|\$[^$\n]+\$)/g)
    .map((part, i) => (i % 2 === 1 ? part : part.replace(/\[(\d+)\](?!\()/g, `[$1](${CITE_PREFIX}$1)`)))
    .join("");
}

/** Answer Markdown: paragraphs, lists, tables, and LaTeX math, with `[n]` opening the matching source. */
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

  const components: Components = {
    a: ({ href, children }) => {
      if (href?.startsWith(CITE_PREFIX)) {
        const n = Number(href.slice(CITE_PREFIX.length));
        const source = byN.get(n);
        return (
          <sup className="ml-0.5">
            {source ? (
              <button
                type="button"
                onClick={() => onCite(source)}
                aria-label={`Source ${n}`}
                className="rounded px-0.5 text-[12px] font-semibold text-accent tabular-nums hover:bg-accent-soft"
              >
                {n}
              </button>
            ) : (
              <span className="text-[12px] text-accent tabular-nums">{n}</span>
            )}
          </sup>
        );
      }
      return (
        <a href={href} target="_blank" rel="noreferrer" className="text-accent underline underline-offset-2">
          {children}
        </a>
      );
    },
    p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
    ul: ({ children }) => <ul className="mb-3 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>,
    ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>,
    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
    h1: ({ children }) => <p className="mb-2 font-semibold">{children}</p>,
    h2: ({ children }) => <p className="mb-2 font-semibold">{children}</p>,
    h3: ({ children }) => <p className="mb-2 font-semibold">{children}</p>,
    table: ({ children }) => (
      <div className="mb-3 overflow-x-auto rounded-chip border border-border [contain:inline-size] last:mb-0">
        <table className="w-full border-collapse text-left text-[15px]">{children}</table>
      </div>
    ),
    thead: ({ children }) => <thead className="bg-surface-2 text-[13px] text-text-2">{children}</thead>,
    th: ({ children }) => <th className="px-3 py-2 font-normal whitespace-nowrap">{children}</th>,
    td: ({ children }) => <td className="border-t border-border px-3 py-2 align-top tabular-nums">{children}</td>,
    code: ({ children }) => <code className="rounded bg-surface-2 px-1 py-0.5 font-mono text-[15px]">{children}</code>,
    pre: ({ children }) => <pre className="mb-3 overflow-x-auto rounded-chip bg-surface-2 p-3">{children}</pre>,
  };

  return (
    <div className="answer-md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, [remarkMath, { singleDollarTextMath: true }]]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: "ignore" }]]}
        components={components}
      >
        {linkCitations(text)}
      </ReactMarkdown>
    </div>
  );
}
