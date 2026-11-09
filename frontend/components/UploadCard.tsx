"use client";

import clsx from "clsx";
import { Check, UploadCloud } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { inputClass } from "@/components/ui";
import { api, upload, type Course, type LectureItem, type Stage } from "@/lib/api";

const STEPS: { stage: Stage | "ready"; label: string }[] = [
  { stage: "preparing", label: "Preparing" },
  { stage: "transcribing", label: "Transcribing" },
  { stage: "flagging", label: "Finding important moments" },
  { stage: "ready", label: "Ready" },
];
const STEP_INDEX: Record<string, number> = { preparing: 0, transcribing: 1, flagging: 2, indexing: 2, notes: 2, ready: 3 };
const MAX_MB = 200;
const ACCEPT = ".mp3,.m4a,.wav,.mp4,.webm,.ogg,.opus,.aac,.mov,audio/*,video/*";

const today = () => new Date().toISOString().slice(0, 10);

export function UploadCard({
  courses,
  defaultCourseId,
  defaultSectionId,
  onDone,
}: {
  courses: Course[];
  defaultCourseId: string | null;
  defaultSectionId: string | null;
  onDone: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [courseId, setCourseId] = useState(defaultCourseId ?? courses[0]?.id ?? "");
  const [sectionId, setSectionId] = useState(defaultSectionId ?? "");
  const [instructorId, setInstructorId] = useState("");
  const [date, setDate] = useState(today);
  const [progress, setProgress] = useState<number | null>(null);
  const [lecture, setLecture] = useState<LectureItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const course = courses.find((c) => c.id === courseId) ?? null;
  const sections = useMemo(() => course?.sections ?? [], [course]);
  const instructors = useMemo(() => {
    const seen = new Map<string, { id: string; name: string; role: string }>();
    for (const s of sections) {
      if (s.instructor?.id) seen.set(s.instructor.id, { id: s.instructor.id, name: s.instructor.name, role: s.instructor.role });
    }
    return [...seen.values()];
  }, [sections]);
  const section = sections.find((s) => s.id === sectionId) ?? null;
  const effectiveInstructor = instructorId || section?.instructor?.id || "";

  useEffect(() => {
    if (!lecture || lecture.status !== "processing") return;
    const timer = setInterval(async () => {
      try {
        const next = await api.lecture(lecture.id);
        setLecture(next);
        if (next.status !== "processing") onDone();
      } catch {
        // Keep polling; a single failed poll is not a failed upload.
      }
    }, 3000);
    return () => clearInterval(timer);
  }, [lecture, onDone]);

  const pick = (f: File | undefined) => {
    setError(null);
    if (!f) return;
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`This file is over ${MAX_MB} MB. Upload a shorter recording or audio only.`);
      return;
    }
    setFile(f);
    if (!title) setTitle(f.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " "));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !courseId || !sectionId || !effectiveInstructor || !title.trim() || !date) {
      setError("Fill in the file, title, course, section, instructor and date.");
      return;
    }
    setError(null);
    const form = new FormData();
    form.append("file", file);
    form.append("title", title.trim());
    form.append("course_id", courseId);
    form.append("section_id", sectionId);
    form.append("instructor_id", effectiveInstructor);
    form.append("source_date", date);
    try {
      setProgress(0);
      const res = await upload("/api/lectures", form, setProgress);
      setLecture(await api.lecture(res.source_id));
      onDone();
    } catch (err) {
      setError((err as Error).message);
      setProgress(null);
    }
  };

  if (lecture) {
    const current = lecture.status === "ready" ? 3 : STEP_INDEX[lecture.stage ?? "preparing"] ?? 0;
    return (
      <section aria-live="polite" className="rounded-card bg-surface p-5">
        <h2 className="text-[17px] font-semibold">{lecture.title}</h2>
        {lecture.status === "failed" ? (
          <p className="mt-3 text-[15px] text-danger">{lecture.error ?? "Processing failed. Try uploading again."}</p>
        ) : (
          <ol className="mt-4 flex flex-col gap-3">
            {STEPS.map((step, i) => (
              <li key={step.stage} className="flex items-center gap-3 text-[15px]">
                <span
                  className={clsx(
                    "flex size-6 items-center justify-center rounded-full border text-[13px]",
                    i < current || lecture.status === "ready"
                      ? "border-accent bg-accent text-white"
                      : i === current
                        ? "border-accent text-accent"
                        : "border-border text-text-2",
                  )}
                >
                  {i < current || lecture.status === "ready" ? <Check size={14} strokeWidth={2} /> : i + 1}
                </span>
                <span className={i <= current ? "text-text" : "text-text-2"}>
                  {step.label}
                  {i === current && lecture.status === "processing" ? "…" : ""}
                </span>
              </li>
            ))}
          </ol>
        )}
      </section>
    );
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4 rounded-card bg-surface p-5">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          pick(e.dataTransfer.files[0]);
        }}
        className={clsx(
          "flex min-h-32 cursor-pointer flex-col items-center justify-center gap-2 rounded-card border border-dashed px-4 text-center",
          dragging ? "border-accent bg-accent-soft" : "border-border",
        )}
      >
        <UploadCloud aria-hidden size={20} strokeWidth={1.5} className="text-text-2" />
        <span className="text-[15px] text-text">{file ? file.name : "Drop a recording here or choose a file"}</span>
        <span className="text-[13px] text-text-2">mp3, m4a, wav or mp4 · up to {MAX_MB} MB</span>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          aria-label="Lecture recording"
          onChange={(e) => pick(e.target.files?.[0])}
        />
      </div>

      <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
        Title
        <input className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
          Course
          <select
            className={inputClass}
            value={courseId}
            onChange={(e) => {
              setCourseId(e.target.value);
              setSectionId("");
              setInstructorId("");
            }}
          >
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.code} · {c.title}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
          Section
          <select
            className={inputClass}
            value={sectionId}
            onChange={(e) => {
              setSectionId(e.target.value);
              setInstructorId("");
            }}
          >
            <option value="">Choose section</option>
            {sections.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
          Instructor
          <select className={inputClass} value={effectiveInstructor} onChange={(e) => setInstructorId(e.target.value)}>
            <option value="">Choose instructor</option>
            {instructors.map((i) => (
              <option key={i.id} value={i.id}>
                {i.name} ({i.role === "ic" ? "IC" : i.role === "hod" ? "HOD" : "Instructor"})
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
          Date
          <input type="date" className={inputClass} value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
      </div>

      {progress !== null ? (
        <div className="h-1.5 overflow-hidden rounded-full bg-surface-2" aria-label="Upload progress">
          <div className="h-full bg-accent transition-[width] duration-200" style={{ width: `${Math.round(progress * 100)}%` }} />
        </div>
      ) : null}
      {error ? (
        <p role="alert" className="text-[15px] text-danger">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={progress !== null}
          className="h-10 rounded-chip bg-accent px-4 text-[15px] font-semibold text-white hover:bg-accent/90 disabled:opacity-50"
        >
          {progress !== null ? "Uploading…" : "Upload lecture"}
        </button>
      </div>
    </form>
  );
}
