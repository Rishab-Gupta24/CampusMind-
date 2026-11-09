"use client";

import clsx from "clsx";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";

export function FeedbackButtons({ answerId }: { answerId: string }) {
  const [rating, setRating] = useState<1 | -1 | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(null), 2000);
    return () => clearTimeout(timer);
  }, [message]);

  const rate = async (value: 1 | -1) => {
    if (rating !== null) return;
    setRating(value);
    try {
      await api.feedback(answerId, value);
      setMessage("Thanks");
    } catch {
      setRating(null);
      setMessage("Couldn't save your rating");
    }
  };

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={() => rate(1)}
        aria-label="Helpful answer"
        aria-pressed={rating === 1}
        disabled={rating !== null}
        className={clsx(
          "flex size-11 items-center justify-center rounded-chip transition-colors duration-150",
          rating === 1 ? "text-good" : "text-text-2 hover:bg-surface-2 disabled:hover:bg-transparent",
        )}
      >
        <ThumbsUp size={16} strokeWidth={1.5} fill={rating === 1 ? "currentColor" : "none"} />
      </button>
      <button
        type="button"
        onClick={() => rate(-1)}
        aria-label="Not helpful"
        aria-pressed={rating === -1}
        disabled={rating !== null}
        className={clsx(
          "flex size-11 items-center justify-center rounded-chip transition-colors duration-150",
          rating === -1 ? "text-danger" : "text-text-2 hover:bg-surface-2 disabled:hover:bg-transparent",
        )}
      >
        <ThumbsDown size={16} strokeWidth={1.5} fill={rating === -1 ? "currentColor" : "none"} />
      </button>
      <span aria-live="polite" className="text-[13px] text-text-2">
        {message}
      </span>
    </div>
  );
}
