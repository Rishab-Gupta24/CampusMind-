"use client";

import { Fragment } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";

/** One line of text with inline `$...$` maths rendered by KaTeX, without a wrapping paragraph. */
export function MathText({ text }: { text: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{ p: ({ children }) => <Fragment>{children}</Fragment> }}
    >
      {text}
    </ReactMarkdown>
  );
}

/** A formula shown on its own line. Accepts LaTeX, or older plain-text formulas (KaTeX shows them as maths). */
export function Formula({ tex }: { tex: string }) {
  const body = tex.trim().replace(/^\$+|\$+$/g, "");
  return (
    <div className="answer-md overflow-x-auto">
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {`$$\n${body}\n$$`}
      </ReactMarkdown>
    </div>
  );
}
