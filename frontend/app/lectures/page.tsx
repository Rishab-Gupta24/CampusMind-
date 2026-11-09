"use client";

import { AudioLines, Plus, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RoleBadge } from "@/components/Badge";
import { PageTitle } from "@/components/PageTitle";
import { UploadCard } from "@/components/UploadCard";
import { EmptyNote, ErrorNote, LoadingDots, StatusText } from "@/components/ui";
import { api, type LectureItem } from "@/lib/api";
import { formatDate, formatDuration } from "@/lib/format";
import { usePrefs } from "@/lib/prefs";

export default function LecturesPage() {
  const { courses, course, section } = usePrefs();
  const [lectures, setLectures] = useState<LectureItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const load = useCallback(() => {
    api
      .lectures(course?.id)
      .then((list) => {
        setLectures(list);
        setError(null);
      })
      .catch((err: Error) => setError(err.message));
  }, [course?.id]);

  useEffect(load, [load]);

  useEffect(() => {
    if (!lectures?.some((l) => l.status === "processing")) return;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [lectures, load]);

  const courseCode = (id: string | null) => courses.find((c) => c.id === id)?.code ?? "";

  return (
    <section>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <PageTitle subtitle={course ? `Lectures for ${course.code}` : "All lectures"}>Lectures</PageTitle>
        <button
          type="button"
          onClick={() => setUploading((v) => !v)}
          className="flex h-10 items-center gap-2 rounded-chip bg-accent px-4 text-[15px] font-semibold text-white hover:bg-accent/90"
        >
          {uploading ? <X aria-hidden size={16} strokeWidth={2} /> : <Plus aria-hidden size={16} strokeWidth={2} />}
          {uploading ? "Close" : "Upload lecture"}
        </button>
      </div>

      {uploading && courses.length ? (
        <div className="mb-6">
          <UploadCard
            courses={courses}
            defaultCourseId={course?.id ?? null}
            defaultSectionId={section?.id ?? null}
            onDone={load}
          />
        </div>
      ) : null}

      {error ? <ErrorNote>{error}</ErrorNote> : null}
      {!lectures && !error ? <LoadingDots label="Loading lectures" /> : null}
      {lectures && lectures.length === 0 ? (
        <EmptyNote>No lectures yet. Upload a recording to get a transcript, notes and flagged moments.</EmptyNote>
      ) : null}
      {lectures && lectures.length > 0 ? (
        <ul className="flex flex-col divide-y divide-border overflow-hidden rounded-card bg-surface">
          {lectures.map((l) => (
            <li key={l.id}>
              <Link
                href={`/lectures/${l.id}`}
                className="flex items-start gap-3 px-4 py-3.5 transition-colors duration-150 hover:bg-surface-2"
              >
                <AudioLines aria-hidden size={20} strokeWidth={1.5} className="mt-0.5 shrink-0 text-text-2" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[17px] text-text">{l.title}</p>
                  <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-text-2 tabular-nums">
                    <span>
                      {courseCode(l.course_id)}
                      {l.section ? ` · ${l.section}` : ""}
                    </span>
                    {l.instructor ? (
                      <span className="flex items-center gap-1.5">
                        {l.instructor.name} <RoleBadge role={l.instructor.role} />
                      </span>
                    ) : null}
                    {l.source_date ? <span>{formatDate(l.source_date)}</span> : null}
                    {l.duration_s ? <span>{formatDuration(l.duration_s)}</span> : null}
                  </p>
                </div>
                <StatusText status={l.status} stage={l.stage} />
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
