"use client";

import clsx from "clsx";
import { AudioLines, Check, FileText, RotateCcw, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { AnswerText } from "@/components/AnswerText";
import { SourcePanel } from "@/components/SourcePanel";
import { ErrorNote, LoadingDots, Segmented, inputClass } from "@/components/ui";
import { api, type QuizQuestion, type QuizSources, type SourceRef, type StudySource } from "@/lib/api";

type Result = "correct" | "wrong" | null;

const SOURCE_OPTIONS = [
  { value: "all" as const, label: "Everything" },
  { value: "past_papers" as const, label: "Past papers" },
  { value: "notes" as const, label: "Notes & lectures" },
];

const TYPE_LABEL = { mcq: "Multiple choice", fill: "Fill in the blank", short: "Short answer" };

const normalise = (s: string) =>
  s
    .toLowerCase()
    .replace(/[$\\{}\s]/g, "")
    .replace(/\.$/, "");

export function SourceLine({ source, onOpen }: { source: StudySource; onOpen: (s: SourceRef) => void }) {
  const Icon = source.kind === "lecture" ? AudioLines : FileText;
  return (
    <button
      type="button"
      onClick={() => onOpen(source)}
      className="inline-flex min-h-9 max-w-full items-center gap-1.5 rounded-chip bg-surface-2 px-2.5 py-1 text-left text-[13px] text-text-2 hover:text-text"
    >
      <Icon aria-hidden size={14} strokeWidth={1.5} className="shrink-0" />
      <span className="truncate">
        <span className="text-text-2">From </span>
        <span className="text-text">{source.label}</span>
        {source.where ? <span className="tabular-nums"> · {source.where}</span> : null}
      </span>
      {source.past_paper ? (
        <span className="ml-1 shrink-0 rounded-chip border border-border bg-surface px-1.5 text-[12px] text-text-2">Past paper</span>
      ) : null}
    </button>
  );
}

function QuestionCard({
  index,
  q,
  result,
  onResult,
  onOpen,
}: {
  index: number;
  q: QuizQuestion;
  result: Result;
  onResult: (r: Result) => void;
  onOpen: (s: SourceRef) => void;
}) {
  const [picked, setPicked] = useState<number | null>(null);
  const [typed, setTyped] = useState("");
  const [revealed, setRevealed] = useState(false);
  const done = result !== null || revealed;

  return (
    <li className="rounded-card bg-surface p-5">
      <div className="flex flex-wrap items-center justify-between gap-2 text-[13px] text-text-2">
        <span className="tabular-nums">
          {index + 1} · {TYPE_LABEL[q.type]}
        </span>
        {result === "correct" ? <span className="text-good">Correct</span> : null}
        {result === "wrong" ? <span className="text-danger">Not quite</span> : null}
      </div>
      <div className="mt-2 text-[17px] leading-relaxed">
        <AnswerText text={q.question} sources={[]} onCite={() => undefined} />
      </div>
      <div className="mt-3">
        <SourceLine source={q.source} onOpen={onOpen} />
      </div>

      {q.type === "mcq" ? (
        <ul className="mt-4 flex flex-col gap-2">
          {q.options.map((opt, i) => {
            const isAnswer = i === q.answer;
            const state = picked === null ? "idle" : isAnswer ? "right" : picked === i ? "wrong" : "idle";
            return (
              <li key={i}>
                <button
                  type="button"
                  disabled={picked !== null}
                  onClick={() => {
                    setPicked(i);
                    onResult(isAnswer ? "correct" : "wrong");
                  }}
                  className={clsx(
                    "flex min-h-11 w-full items-center gap-3 rounded-card border px-3 py-2 text-left text-[15px] transition-colors duration-150",
                    state === "right" && "border-good text-text",
                    state === "wrong" && "border-danger text-text",
                    state === "idle" && "border-border hover:bg-surface-2 disabled:hover:bg-transparent",
                  )}
                >
                  <span className="w-5 shrink-0 text-text-2 tabular-nums">{String.fromCharCode(65 + i)}</span>
                  <span className="flex-1">
                    <AnswerText text={opt} sources={[]} onCite={() => undefined} />
                  </span>
                  {state === "right" ? <Check aria-label="Correct answer" size={16} className="text-good" /> : null}
                  {state === "wrong" ? <X aria-label="Your answer" size={16} className="text-danger" /> : null}
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}

      {q.type === "fill" ? (
        <form
          className="mt-4 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!typed.trim() || result !== null) return;
            onResult(normalise(typed) === normalise(q.answer) ? "correct" : "wrong");
            setRevealed(true);
          }}
        >
          <input
            aria-label="Your answer"
            className={inputClass}
            value={typed}
            disabled={result !== null}
            onChange={(e) => setTyped(e.target.value)}
            placeholder="Type the missing word or value"
          />
          <button
            type="submit"
            disabled={result !== null || !typed.trim()}
            className="h-11 shrink-0 rounded-chip bg-accent px-4 text-[15px] font-semibold text-white disabled:opacity-40"
          >
            Check
          </button>
        </form>
      ) : null}

      {q.type === "short" && !revealed ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setRevealed(true)}
            className="h-10 rounded-chip bg-surface-2 px-4 text-[15px] text-text hover:bg-border/60"
          >
            {q.answer_available ? "Show answer" : "I've tried it"}
          </button>
        </div>
      ) : null}

      {(done || picked !== null) && (q.type !== "mcq" || picked !== null) ? (
        <div className="mt-4 rounded-card bg-surface-2 p-4 text-[15px] leading-relaxed">
          {q.type === "fill" ? (
            <p>
              <span className="text-text-2">Answer: </span>
              <AnswerText text={q.answer} sources={[]} onCite={() => undefined} />
            </p>
          ) : null}
          {q.type === "short" && q.answer_available ? <AnswerText text={q.answer} sources={[]} onCite={() => undefined} /> : null}
          {q.type === "short" && !q.answer_available ? (
            <p className="text-text-2">
              The sources have no official answer for this past-paper question. Check your working against your notes,
              or{" "}
              <Link href={`/?q=${encodeURIComponent(q.question.slice(0, 300))}`} className="text-accent underline underline-offset-2">
                ask CampusMind about the topic
              </Link>
              .
            </p>
          ) : null}
          {q.explanation ? (
            <div className="mt-2 text-text-2">
              <AnswerText text={q.explanation} sources={[]} onCite={() => undefined} />
            </div>
          ) : null}
          {q.type === "short" && result === null ? (
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => onResult("correct")}
                className="h-9 rounded-chip border border-border px-3 text-[13px] hover:bg-surface"
              >
                I got it
              </button>
              <button
                type="button"
                onClick={() => onResult("wrong")}
                className="h-9 rounded-chip border border-border px-3 text-[13px] hover:bg-surface"
              >
                I missed it
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

export function QuizPanel({
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
  const [count, setCount] = useState(5);
  const [sources, setSources] = useState<QuizSources>("all");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [results, setResults] = useState<Result[]>([]);
  const [round, setRound] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<SourceRef | null>(null);

  const start = async (exclude: string[] = []) => {
    if (topic.trim().length < 2) {
      setError("Type a topic or chapter first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.quiz({
        topic: topic.trim(),
        count,
        sources,
        course_id: courseId,
        section_id: sectionId,
        lecture_id: lectureId,
        exclude,
      });
      setQuestions(res.questions);
      setResults(res.questions.map(() => null));
      setRound((r) => r + 1);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const retryMissed = () => {
    const missed = questions.filter((_, i) => results[i] !== "correct");
    setQuestions(missed);
    setResults(missed.map(() => null));
    setRound((r) => r + 1);
  };

  const answered = results.filter((r) => r !== null).length;
  const correct = results.filter((r) => r === "correct").length;

  return (
    <div className="flex flex-col gap-5">
      <form
        className="flex flex-col gap-4 rounded-card bg-surface p-5"
        onSubmit={(e) => {
          e.preventDefault();
          start();
        }}
      >
        <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
          Topic or chapter
          <input
            className={inputClass}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Bayes' theorem, random variables, Chapter 3"
            maxLength={200}
          />
        </label>
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
            Questions
            <select className={clsx(inputClass, "w-24")} value={count} onChange={(e) => setCount(Number(e.target.value))}>
              {[5, 6, 7, 8, 9, 10].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <div className="flex flex-col gap-1.5 text-[13px] text-text-2">
            From
            <Segmented label="Question sources" options={SOURCE_OPTIONS} value={sources} onChange={setSources} />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="ml-auto flex h-10 items-center gap-2 rounded-chip bg-accent px-4 text-[15px] font-semibold text-white hover:bg-accent/90 disabled:opacity-50"
          >
            <Sparkles aria-hidden size={16} strokeWidth={1.75} />
            {questions.length ? "New quiz" : "Start quiz"}
          </button>
        </div>
      </form>

      {loading ? (
        <div className="flex items-center gap-3 text-[15px] text-text-2">
          <LoadingDots label="Writing questions" /> Writing questions from your sources. This takes 15–30 seconds.
        </div>
      ) : null}
      {error ? <ErrorNote>{error}</ErrorNote> : null}

      {questions.length && !loading ? (
        <>
          <ol className="flex flex-col gap-4" aria-label="Quiz questions">
            {questions.map((q, i) => (
              <QuestionCard
                key={`${round}-${i}`}
                index={i}
                q={q}
                result={results[i]}
                onResult={(r) => setResults((all) => all.map((x, j) => (j === i ? r : x)))}
                onOpen={setOpen}
              />
            ))}
          </ol>
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-card bg-surface p-4">
            <p className="text-[15px] tabular-nums">
              {answered === questions.length ? (
                <>
                  Score <span className="font-semibold">{correct}</span> of {questions.length}
                </>
              ) : (
                <span className="text-text-2">
                  {answered} of {questions.length} answered
                </span>
              )}
            </p>
            <div className="flex flex-wrap gap-2">
              {answered > 0 && correct < questions.length ? (
                <button
                  type="button"
                  onClick={retryMissed}
                  className="flex h-10 items-center gap-2 rounded-chip bg-surface-2 px-4 text-[15px] hover:bg-border/60"
                >
                  <RotateCcw aria-hidden size={16} strokeWidth={1.5} /> Retry missed
                </button>
              ) : null}
              <button
                type="button"
                onClick={() => start(questions.map((q) => q.question))}
                className="h-10 rounded-chip bg-accent px-4 text-[15px] font-semibold text-white hover:bg-accent/90"
              >
                More questions
              </button>
            </div>
          </div>
        </>
      ) : null}

      <SourcePanel source={open} onClose={() => setOpen(null)} />
    </div>
  );
}
