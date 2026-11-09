"use client";

import { RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";

import { AnswerText } from "@/components/AnswerText";
import { SourceLine } from "@/components/Quiz";
import { SourcePanel } from "@/components/SourcePanel";
import { ErrorNote, LoadingDots, inputClass } from "@/components/ui";
import { api, type Flashcard, type SourceRef } from "@/lib/api";

const STORAGE_KEY = "campusmind.flashcards";

interface Deck {
  topic: string;
  cards: Flashcard[];
  queue: number[]; // card indexes still to learn, in order
  learned: number[];
}

function loadDeck(): Deck | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Deck) : null;
  } catch {
    return null;
  }
}

function saveDeck(deck: Deck | null): void {
  try {
    if (deck) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(deck));
    else window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Not saved on this device; the deck still works for this visit.
  }
}

export function FlashcardsPanel({
  initialTopic,
  courseId,
  sectionId,
  lectureId,
}: {
  initialTopic: string;
  courseId: string | null;
  sectionId: string | null;
  lectureId: string | null;
}) {
  const [topic, setTopic] = useState(initialTopic);
  const [deck, setDeck] = useState<Deck | null>(null);
  const [flipped, setFlipped] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<SourceRef | null>(null);

  useEffect(() => {
    // Resume the last deck on this device (read after mount: storage is browser-only).
    const saved = loadDeck();
    if (saved && saved.queue.length) {
      queueMicrotask(() => setDeck(saved));
    }
  }, []);

  const update = (next: Deck | null) => {
    setDeck(next);
    saveDeck(next);
    setFlipped(false);
  };

  const build = async () => {
    if (topic.trim().length < 2) {
      setError("Type a topic first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.flashcards({ topic: topic.trim(), count: 10, course_id: courseId, section_id: sectionId, lecture_id: lectureId });
      update({ topic: res.topic, cards: res.cards, queue: res.cards.map((_, i) => i), learned: [] });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const current = deck && deck.queue.length ? deck.cards[deck.queue[0]] : null;

  const answer = (gotIt: boolean) => {
    if (!deck) return;
    const [head, ...rest] = deck.queue;
    if (gotIt) {
      update({ ...deck, queue: rest, learned: [...deck.learned, head] });
    } else {
      // "Again": the card comes back after a few others (or at the end of a short deck).
      const at = Math.min(3, rest.length);
      update({ ...deck, queue: [...rest.slice(0, at), head, ...rest.slice(at)] });
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <form
        className="flex flex-wrap items-end gap-3 rounded-card bg-surface p-5"
        onSubmit={(e) => {
          e.preventDefault();
          build();
        }}
      >
        <label className="flex min-w-0 flex-1 flex-col gap-1.5 text-[13px] text-text-2">
          Topic or chapter
          <input
            className={inputClass}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. random variables"
            maxLength={200}
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="h-11 rounded-chip bg-accent px-4 text-[15px] font-semibold text-white hover:bg-accent/90 disabled:opacity-50"
        >
          {deck ? "New deck" : "Make flashcards"}
        </button>
      </form>

      {loading ? (
        <div className="flex items-center gap-3 text-[15px] text-text-2">
          <LoadingDots label="Making flashcards" /> Making flashcards from your sources…
        </div>
      ) : null}
      {error ? <ErrorNote>{error}</ErrorNote> : null}

      {deck && !loading ? (
        <section aria-label={`Flashcards: ${deck.topic}`} className="flex flex-col gap-3">
          <p className="text-[13px] text-text-2 tabular-nums">
            {deck.topic} · {deck.learned.length} of {deck.cards.length} learned
          </p>
          <div className="h-1.5 overflow-hidden rounded-full bg-surface-2">
            <div
              className="h-full bg-good transition-[width] duration-200"
              style={{ width: `${(deck.learned.length / deck.cards.length) * 100}%` }}
            />
          </div>

          {current ? (
            <>
              <button
                type="button"
                onClick={() => setFlipped((f) => !f)}
                aria-label={flipped ? "Show question" : "Show answer"}
                className="flex min-h-52 flex-col items-center justify-center gap-3 rounded-card bg-surface p-6 text-center transition-colors duration-150 hover:bg-surface-2/60"
              >
                <span className="text-[13px] text-text-2">{flipped ? "Answer" : "Question"} · tap to flip</span>
                <span className="text-[19px] leading-relaxed">
                  <AnswerText text={flipped ? current.back : current.front} sources={[]} onCite={() => undefined} />
                </span>
              </button>
              <SourceLine source={current.source} onOpen={setOpen} />
              {flipped ? (
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => answer(false)}
                    className="h-11 rounded-chip border border-border text-[15px] hover:bg-surface-2"
                  >
                    Again
                  </button>
                  <button
                    type="button"
                    onClick={() => answer(true)}
                    className="h-11 rounded-chip bg-accent text-[15px] font-semibold text-white hover:bg-accent/90"
                  >
                    Got it
                  </button>
                </div>
              ) : null}
            </>
          ) : (
            <div className="flex flex-col items-center gap-3 rounded-card bg-surface p-6 text-center">
              <p className="text-[17px]">All {deck.cards.length} cards learned.</p>
              <button
                type="button"
                onClick={() => update({ ...deck, queue: deck.cards.map((_, i) => i), learned: [] })}
                className="flex h-10 items-center gap-2 rounded-chip bg-surface-2 px-4 text-[15px] hover:bg-border/60"
              >
                <RotateCcw aria-hidden size={16} strokeWidth={1.5} /> Study again
              </button>
            </div>
          )}
        </section>
      ) : null}

      <SourcePanel source={open} onClose={() => setOpen(null)} />
    </div>
  );
}
