"use client";

import clsx from "clsx";
import { UploadCloud } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { StatusText, inputClass } from "@/components/ui";
import { api, upload, type Course, type DocumentItem, type SourceKind } from "@/lib/api";

const MAX_MB = 200;
const KINDS: { value: Exclude<SourceKind, "lecture">; label: string }[] = [
  { value: "campus", label: "Campus rule or circular (Official)" },
  { value: "handout", label: "Course handout (Official)" },
  { value: "material", label: "Course material: slides, notes, past papers" },
];

export function AddDocumentCard({
  courses,
  defaultCourseId,
  onDone,
}: {
  courses: Course[];
  defaultCourseId: string | null;
  onDone: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<Exclude<SourceKind, "lecture">>("campus");
  const [courseId, setCourseId] = useState(defaultCourseId ?? "");
  const [date, setDate] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const [doc, setDoc] = useState<DocumentItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!doc || doc.status !== "processing") return;
    const timer = setInterval(async () => {
      try {
        const next = await api.document(doc.id);
        setDoc(next);
        if (next.status !== "processing") onDone();
      } catch {
        // keep polling
      }
    }, 3000);
    return () => clearInterval(timer);
  }, [doc, onDone]);

  const pick = (f: File | undefined) => {
    setError(null);
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files can be added as documents.");
      return;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`This file is over ${MAX_MB} MB.`);
      return;
    }
    setFile(f);
    if (!title) setTitle(f.name.replace(/\.pdf$/i, "").replace(/[_-]+/g, " "));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title.trim()) {
      setError("Choose a PDF and give it a title.");
      return;
    }
    if (kind !== "campus" && !courseId) {
      setError("Course handouts and material need a course.");
      return;
    }
    setError(null);
    const form = new FormData();
    form.append("file", file);
    form.append("title", title.trim());
    form.append("kind", kind);
    if (courseId && kind !== "campus") form.append("course_id", courseId);
    if (date) form.append("source_date", date);
    try {
      setProgress(0);
      const res = await upload("/api/documents", form, setProgress);
      setDoc(await api.document(res.source_id));
      onDone();
    } catch (err) {
      setError((err as Error).message);
      setProgress(null);
    }
  };

  if (doc) {
    return (
      <section aria-live="polite" className="flex items-center justify-between gap-3 rounded-card bg-surface p-5">
        <div>
          <p className="text-[17px] font-semibold">{doc.title}</p>
          {doc.status === "failed" ? <p className="mt-1 text-[15px] text-danger">{doc.error}</p> : null}
          {doc.status === "ready" ? <p className="mt-1 text-[15px] text-text-2">{doc.pages} pages indexed.</p> : null}
        </div>
        <StatusText status={doc.status} />
      </section>
    );
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4 rounded-card bg-surface p-5">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          pick(e.dataTransfer.files[0]);
        }}
        className={clsx(
          "flex min-h-28 flex-col items-center justify-center gap-2 rounded-card border border-dashed border-border px-4 text-center",
        )}
      >
        <UploadCloud aria-hidden size={20} strokeWidth={1.5} className="text-text-2" />
        <span className="text-[15px] text-text">{file ? file.name : "Drop a PDF here or choose a file"}</span>
        <span className="text-[13px] text-text-2">Text PDFs only; scanned pages can&apos;t be read yet</span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="sr-only"
        aria-label="PDF document"
        onChange={(e) => pick(e.target.files?.[0])}
      />
      <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
        Title
        <input className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-[13px] text-text-2 sm:col-span-2">
          Type
          <select className={inputClass} value={kind} onChange={(e) => setKind(e.target.value as typeof kind)}>
            {KINDS.map((k) => (
              <option key={k.value} value={k.value}>
                {k.label}
              </option>
            ))}
          </select>
        </label>
        {kind !== "campus" ? (
          <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
            Course
            <select className={inputClass} value={courseId} onChange={(e) => setCourseId(e.target.value)}>
              <option value="">Choose course</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} · {c.title}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
          Date (optional)
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
          {progress !== null ? "Uploading…" : "Add document"}
        </button>
      </div>
    </form>
  );
}
