"use client";

import { ArrowUp, Square } from "lucide-react";
import { useEffect, useId, useRef } from "react";

export function AskBox({
  value,
  onChange,
  onSubmit,
  onStop,
  busy,
  placeholder = "Ask about a rule, deadline or lecture",
  autoFocus = false,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop?: () => void;
  busy: boolean;
  placeholder?: string;
  autoFocus?: boolean;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const inputId = useId();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  useEffect(() => {
    if (autoFocus) ref.current?.focus();
  }, [autoFocus]);

  const canSend = value.trim().length >= 2 && !busy;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (canSend) onSubmit();
      }}
      className="flex items-end gap-2 rounded-card bg-surface-2 p-1.5 focus-within:outline-2 focus-within:outline-accent"
    >
      <label htmlFor={inputId} className="sr-only">
        Your question
      </label>
      <textarea
        id={inputId}
        aria-label="Your question"
        ref={ref}
        rows={1}
        value={value}
        maxLength={500}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            if (canSend) onSubmit();
          }
        }}
        className="min-h-10 flex-1 resize-none bg-transparent px-2.5 py-2 text-[17px] leading-6 text-text outline-none placeholder:text-text-2"
      />
      {busy && onStop ? (
        <button
          type="button"
          onClick={onStop}
          aria-label="Stop"
          className="flex size-10 shrink-0 items-center justify-center rounded-chip bg-surface text-text"
        >
          <Square size={14} strokeWidth={2} fill="currentColor" />
        </button>
      ) : (
        <button
          type="submit"
          aria-label="Ask"
          disabled={!canSend}
          className="flex size-10 shrink-0 items-center justify-center rounded-chip bg-accent text-white transition-opacity duration-150 disabled:opacity-40"
        >
          <ArrowUp size={18} strokeWidth={2} />
        </button>
      )}
    </form>
  );
}
