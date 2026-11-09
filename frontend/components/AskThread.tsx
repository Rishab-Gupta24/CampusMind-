"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { AnswerText } from "@/components/AnswerText";
import { AskBox } from "@/components/AskBox";
import { FeedbackButtons } from "@/components/FeedbackButtons";
import { SourceChip } from "@/components/SourceChip";
import { SourcePanel } from "@/components/SourcePanel";
import { LoadingDots, Segmented } from "@/components/ui";
import { ask, type Scope, type SourceRef } from "@/lib/api";

type TurnStatus = "waiting" | "streaming" | "done" | "not_found" | "error" | "stopped" | "quiz";

interface Turn {
  id: number;
  question: string;
  answer: string;
  sources: SourceRef[];
  status: TurnStatus;
  message: string;
  answerId: string | null;
}

/** Show citations as 1, 2, 3 in order of the sources, whatever passage number the model used. */
function renumber(answer: string, sources: SourceRef[]): { text: string; sources: SourceRef[] } {
  if (!sources.length) return { text: answer, sources };
  const map = new Map(sources.map((s, i) => [s.n, i + 1]));
  const text = answer.replace(/\[(\d+)\]/g, (m, d: string) => (map.has(Number(d)) ? `[${map.get(Number(d))}]` : m));
  return { text, sources: sources.map((s, i) => ({ ...s, n: i + 1 })) };
}

const SCOPES = [
  { value: "all" as const, label: "All" },
  { value: "docs" as const, label: "Campus docs" },
  { value: "lectures" as const, label: "Lectures" },
];

export function AskThread({
  courseId,
  sectionId,
  lectureId,
  title,
  examples = [],
  initialQuestion,
}: {
  courseId: string | null;
  sectionId: string | null;
  lectureId?: string;
  title?: string;
  examples?: string[];
  initialQuestion?: string;
}) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [scope, setScope] = useState<Scope>("all");
  const [open, setOpen] = useState<SourceRef | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);

  const busy = turns.some((t) => t.status === "waiting" || t.status === "streaming");

  useEffect(() => () => abortRef.current?.abort(), []);

  const update = useCallback((id: number, patch: Partial<Turn> | ((t: Turn) => Partial<Turn>)) => {
    setTurns((all) => all.map((t) => (t.id === id ? { ...t, ...(typeof patch === "function" ? patch(t) : patch) } : t)));
  }, []);

  const send = useCallback(
    async (question: string) => {
      const q = question.trim();
      if (q.length < 2 || busy) return;
      const id = nextId.current++;
      setTurns((all) => [
        ...all,
        { id, question: q, answer: "", sources: [], status: "waiting", message: "", answerId: null },
      ]);
      setDraft("");
      requestAnimationFrame(() => endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }));

      const controller = new AbortController();
      abortRef.current = controller;
      await ask(
        {
          question: q,
          scope: lectureId ? "lectures" : scope,
          course_id: courseId,
          section_id: sectionId,
          lecture_id: lectureId ?? null,
        },
        {
          onQuiz: (topic) => update(id, { status: "quiz", message: topic }),
          onToken: (text) => update(id, (t) => ({ answer: t.answer + text, status: "streaming" })),
          onSources: (sources) => update(id, { sources }),
          onNotFound: (message) => update(id, { status: "not_found", message, answer: "" }),
          onDone: (answerId, answer) =>
            update(id, (t) => ({ status: "done", answerId, answer: answer || t.answer })),
          onError: (message) => update(id, { status: "error", message }),
        },
        controller.signal,
      );
      update(id, (t) => (t.status === "waiting" || t.status === "streaming" ? { status: "stopped" } : {}));
    },
    [busy, courseId, sectionId, lectureId, scope, update],
  );

  const stop = () => abortRef.current?.abort();

  const asked = useRef(false);
  useEffect(() => {
    if (!initialQuestion || asked.current) return;
    asked.current = true;
    queueMicrotask(() => send(initialQuestion));
  }, [initialQuestion, send]);
  const empty = turns.length === 0;

  return (
    <div className={empty ? "" : "pb-36"}>
      {empty ? (
        <div className="pt-8 md:pt-16">
          {title ? <h1 className="text-[28px] leading-[1.2] font-semibold tracking-tight">{title}</h1> : null}
          <div className="mt-6">
            <AskBox value={draft} onChange={setDraft} onSubmit={() => send(draft)} busy={busy} autoFocus />
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            {lectureId ? <span /> : <Segmented label="Search in" options={SCOPES} value={scope} onChange={setScope} />}
          </div>
          {examples.length ? (
            <div className="mt-6">
              <p className="text-[13px] text-text-2">Try asking</p>
              <ul className="mt-2 flex flex-wrap gap-2">
                {examples.map((ex) => (
                  <li key={ex}>
                    <button
                      type="button"
                      onClick={() => send(ex)}
                      className="min-h-11 rounded-chip bg-surface px-3 py-2 text-left text-[15px] text-text hover:bg-surface-2"
                    >
                      {ex}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : (
        <ol className="flex flex-col gap-8 pt-4" aria-label="Questions and answers">
          {turns.map((t) => {
            const shown = renumber(t.answer, t.sources);
            return (
            <li key={t.id} className="flex flex-col gap-3">
              <p className="ml-auto max-w-[85%] rounded-card bg-surface-2 px-4 py-2.5 text-[17px]">{t.question}</p>
              <div
                aria-live="polite"
                aria-busy={t.status === "waiting" || t.status === "streaming"}
                className="rounded-card bg-surface px-4 py-4 md:px-5"
              >
                {t.status === "waiting" ? <LoadingDots label="Finding sources" /> : null}
                {t.status === "not_found" ? (
                  <div className="text-[17px] text-text-2">
                    <p>{t.message}</p>
                    <p className="mt-2 text-[15px]">Rephrase with the course code or the exact term from the rule.</p>
                  </div>
                ) : null}
                {t.status === "error" ? <p className="text-[17px] text-danger">{t.message}</p> : null}
                {t.status === "quiz" ? (
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-[17px]">
                      That sounds like practice. Make a quiz on <span className="font-semibold">{t.message}</span>, with
                      questions from your notes and past papers.
                    </p>
                    <Link
                      href={`/practice?topic=${encodeURIComponent(t.message)}`}
                      className="flex h-10 items-center rounded-chip bg-accent px-4 text-[15px] font-semibold text-white hover:bg-accent/90"
                    >
                      Start quiz
                    </Link>
                  </div>
                ) : null}
                {t.answer && t.status !== "not_found" ? (
                  <div className="text-[17px] leading-relaxed">
                    <AnswerText text={shown.text} sources={shown.sources} onCite={setOpen} />
                  </div>
                ) : null}
                {t.status === "stopped" && !t.answer ? <p className="text-[15px] text-text-2">Stopped.</p> : null}
                {shown.sources.length ? (
                  <div className="mt-4 flex flex-wrap gap-2" aria-label="Sources">
                    {shown.sources.map((s) => (
                      <SourceChip key={s.chunk_id} source={s} onOpen={setOpen} />
                    ))}
                  </div>
                ) : null}
                {t.status === "done" && t.answerId ? (
                  <div className="mt-2 -ml-2">
                    <FeedbackButtons answerId={t.answerId} />
                  </div>
                ) : null}
              </div>
            </li>
            );
          })}
          <div ref={endRef} />
        </ol>
      )}

      {!empty ? (
        <div className="fixed inset-x-0 bottom-0 z-30 px-2 pb-2 md:px-4 md:pb-4">
          <div className="glass mx-auto flex max-w-[760px] flex-col gap-2 p-2">
            <AskBox
              value={draft}
              onChange={setDraft}
              onSubmit={() => send(draft)}
              onStop={stop}
              busy={busy}
              placeholder="Ask a follow-up question"
            />
            {lectureId ? null : (
              <div className="px-1">
                <Segmented label="Search in" options={SCOPES} value={scope} onChange={setScope} />
              </div>
            )}
          </div>
        </div>
      ) : null}

      <SourcePanel source={open} onClose={() => setOpen(null)} />
    </div>
  );
}
