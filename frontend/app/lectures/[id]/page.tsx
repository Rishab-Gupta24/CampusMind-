"use client";

import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { AskThread } from "@/components/AskThread";
import { RoleBadge } from "@/components/Badge";
import { Formula, MathText } from "@/components/MathText";
import { FlaggedList, Transcript } from "@/components/Transcript";
import { EmptyNote, ErrorNote, LoadingDots, StatusText, Tabs } from "@/components/ui";
import { api, type LectureDetail } from "@/lib/api";
import { formatDate, formatDuration } from "@/lib/format";
import { usePrefs } from "@/lib/prefs";

type Tab = "summary" | "flagged" | "transcript" | "ask";

export default function LecturePage() {
  return (
    <Suspense fallback={<LoadingDots label="Loading lecture" />}>
      <Lecture />
    </Suspense>
  );
}

function Lecture() {
  const { id } = useParams<{ id: string }>();
  const params = useSearchParams();
  const { courses, section } = usePrefs();
  const [lecture, setLecture] = useState<LectureDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>(params.get("t") ? "transcript" : "summary");
  const [highlight, setHighlight] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const deepLinked = useRef(false);

  useEffect(() => {
    api
      .lecture(id)
      .then(setLecture)
      .catch((err: Error) => setError(err.message));
  }, [id]);

  useEffect(() => {
    if (lecture?.status !== "processing") return;
    const timer = setInterval(() => {
      api.lecture(id).then(setLecture).catch(() => undefined);
    }, 3000);
    return () => clearInterval(timer);
  }, [lecture?.status, id]);

  const seek = useCallback(
    (seconds: number, play = true) => {
      const audio = audioRef.current;
      if (audio) {
        audio.currentTime = seconds;
        if (play) audio.play().catch(() => undefined);
      }
      if (!lecture) return;
      const index = lecture.transcript.findIndex((l, i, all) => seconds < (all[i + 1]?.start_s ?? Infinity) && seconds >= l.start_s - 0.5);
      setHighlight(index >= 0 ? index : null);
    },
    [lecture],
  );

  useEffect(() => {
    if (!lecture || deepLinked.current) return;
    const t = params.get("t");
    if (t === null) return;
    deepLinked.current = true;
    const seconds = Number(t);
    const timer = setTimeout(() => seek(seconds, params.get("play") === "1"), 100);
    return () => clearTimeout(timer);
  }, [lecture, params, seek]);

  useEffect(() => {
    if (highlight === null) return;
    const timer = setTimeout(() => setHighlight(null), 1500);
    return () => clearTimeout(timer);
  }, [highlight]);

  if (error) return <ErrorNote>{error}</ErrorNote>;
  if (!lecture) return <LoadingDots label="Loading lecture" />;

  const course = courses.find((c) => c.id === lecture.course_id);
  const tabs = [
    { value: "summary" as const, label: "Summary" },
    { value: "flagged" as const, label: lecture.flagged.length ? `Flagged (${lecture.flagged.length})` : "Flagged" },
    { value: "transcript" as const, label: "Transcript" },
    { value: "ask" as const, label: "Ask this lecture" },
  ];

  return (
    <article className={lecture.audio_url && tab !== "ask" ? "pb-28" : ""}>
      <Link href="/lectures" className="-ml-2 inline-flex h-11 items-center gap-1 rounded-chip px-2 text-[15px] text-text-2 hover:text-text">
        <ChevronLeft aria-hidden size={16} strokeWidth={1.5} /> Lectures
      </Link>
      <h1 className="mt-1 text-[28px] leading-[1.2] font-semibold tracking-tight">{lecture.title}</h1>
      <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[15px] text-text-2 tabular-nums">
        <span>
          {course?.code}
          {lecture.section ? ` · ${lecture.section}` : ""}
        </span>
        {lecture.instructor ? (
          <span className="flex items-center gap-1.5">
            {lecture.instructor.name} <RoleBadge role={lecture.instructor.role} />
          </span>
        ) : null}
        {lecture.source_date ? <span>{formatDate(lecture.source_date)}</span> : null}
        {lecture.duration_s ? <span>{formatDuration(lecture.duration_s)}</span> : null}
        {lecture.status !== "ready" ? <StatusText status={lecture.status} stage={lecture.stage} /> : null}
      </p>

      {lecture.status === "failed" ? (
        <div className="mt-6">
          <ErrorNote>{lecture.error ?? "Processing failed. Try uploading again."}</ErrorNote>
        </div>
      ) : lecture.status === "processing" ? (
        <div className="mt-6">
          <EmptyNote>This lecture is still being processed. This page updates by itself.</EmptyNote>
        </div>
      ) : (
        <>
          <div className="mt-4">
            <Link
              href={`/practice?lecture=${lecture.id}&topic=${encodeURIComponent(lecture.title)}`}
              className="inline-flex h-10 items-center rounded-chip bg-surface-2 px-4 text-[15px] text-text hover:bg-border/60"
            >
              Practice this lecture
            </Link>
          </div>
          <div className="mt-5">
            <Tabs label="Lecture sections" tabs={tabs} value={tab} onChange={setTab} />
          </div>
          <div className="mt-5">
            {tab === "summary" ? (
              <div className="flex flex-col gap-5">
                <section className="rounded-card bg-surface p-5">
                  <h2 className="text-[13px] text-text-2">Summary</h2>
                  {lecture.summary ? (
                    <ul className="mt-2 flex flex-col gap-1.5 text-[17px] leading-relaxed">
                      {lecture.summary.split("\n").filter(Boolean).map((line, i) => (
                        <li key={i}>
                          <MathText text={line} />
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-[15px] text-text-2">No summary for this lecture yet.</p>
                  )}
                </section>
                {lecture.key_points.length ? (
                  <section className="rounded-card bg-surface p-5">
                    <h2 className="text-[13px] text-text-2">Key points</h2>
                    <ul className="mt-2 flex list-disc flex-col gap-1.5 pl-5 text-[17px] leading-relaxed">
                      {lecture.key_points.map((p, i) => (
                        <li key={i}>
                          <MathText text={p} />
                        </li>
                      ))}
                    </ul>
                  </section>
                ) : null}
                {lecture.formulas.length ? (
                  <section className="rounded-card bg-surface p-5">
                    <h2 className="text-[13px] text-text-2">Formulas</h2>
                    <div className="mt-2 flex flex-col gap-1 rounded-chip bg-surface-2 px-3 py-1">
                      {lecture.formulas.map((f, i) => (
                        <Formula key={i} tex={f} />
                      ))}
                    </div>
                  </section>
                ) : null}
              </div>
            ) : null}

            {tab === "flagged" ? (
              lecture.flagged.length ? (
                <FlaggedList
                  moments={lecture.flagged}
                  onOpen={(m) => {
                    setTab("transcript");
                    setTimeout(() => seek(m.start_s, false), 50);
                  }}
                />
              ) : (
                <EmptyNote>No moments in this lecture were flagged as important.</EmptyNote>
              )
            ) : null}

            {tab === "transcript" ? <Transcript lines={lecture.transcript} highlight={highlight} onSeek={seek} /> : null}

            {tab === "ask" ? (
              <AskThread
                courseId={lecture.course_id}
                sectionId={section?.id ?? null}
                lectureId={lecture.id}
                examples={["What are the key formulas?", "What did the instructor say will come in the exam?"]}
              />
            ) : null}
          </div>
        </>
      )}

      {lecture.audio_url ? (
        <div className={tab === "ask" ? "hidden" : "fixed inset-x-0 bottom-0 z-30 px-2 pb-2 md:px-4 md:pb-4"}>
          <div className="glass mx-auto max-w-[760px] p-2">
            <audio ref={audioRef} controls preload="metadata" src={lecture.audio_url} className="h-10 w-full">
              Your browser cannot play this recording.
            </audio>
          </div>
        </div>
      ) : null}
    </article>
  );
}
