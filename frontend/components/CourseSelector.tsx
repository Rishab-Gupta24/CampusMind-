"use client";

import clsx from "clsx";
import { Check, ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { usePrefs } from "@/lib/prefs";

export function CourseSelector() {
  const { courses, course, section, select, loading } = usePrefs();
  const [open, setOpen] = useState(false);
  const [draftCourse, setDraftCourse] = useState<string | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const label = course ? `${course.code}${section ? ` · ${section.name}` : ""}` : loading ? "…" : "Choose course";
  const shown = courses.find((c) => c.id === draftCourse) ?? null;

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={() => {
          if (!open) setDraftCourse(course?.id ?? courses[0]?.id ?? null);
          setOpen((v) => !v);
        }}
        aria-expanded={open}
        aria-haspopup="dialog"
        className="flex h-11 items-center gap-1 rounded-chip px-3 text-[15px] whitespace-nowrap text-text tabular-nums hover:bg-surface-2/70"
      >
        {label}
        <ChevronDown aria-hidden size={16} strokeWidth={1.5} className="text-text-2" />
      </button>
      {open ? (
        <div
          role="dialog"
          aria-label="Choose course and section"
          className="glass glass-strong absolute right-0 z-50 mt-2 grid w-[min(92vw,420px)] grid-cols-2 gap-2 p-2"
        >
          <div>
            <p className="px-2 pt-1 pb-2 text-[13px] text-text-2">Course</p>
            <ul className="flex flex-col">
              {courses.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => setDraftCourse(c.id)}
                    className={clsx(
                      "flex min-h-11 w-full flex-col items-start justify-center gap-0.5 rounded-chip px-2 py-1.5 text-left",
                      draftCourse === c.id ? "bg-accent-soft" : "hover:bg-surface-2/70",
                    )}
                  >
                    <span className={clsx("text-[15px]", draftCourse === c.id && "font-semibold text-accent")}>
                      {c.code}
                    </span>
                    <span className="text-[13px] leading-tight text-text-2">{c.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="px-2 pt-1 pb-2 text-[13px] text-text-2">Section</p>
            <ul className="flex flex-col">
              {shown ? (
                <li>
                  <button
                    type="button"
                    onClick={() => {
                      select(shown.id, null);
                      setOpen(false);
                    }}
                    className="flex min-h-11 w-full items-center justify-between rounded-chip px-2 text-left text-[15px] hover:bg-surface-2/70"
                  >
                    Any section
                    {course?.id === shown.id && !section ? <Check size={16} className="text-accent" /> : null}
                  </button>
                </li>
              ) : null}
              {shown?.sections.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => {
                      select(shown.id, s.id);
                      setOpen(false);
                    }}
                    className="flex min-h-11 w-full items-center justify-between gap-2 rounded-chip px-2 py-1.5 text-left hover:bg-surface-2/70"
                  >
                    <span className="flex flex-col gap-0.5">
                      <span className="text-[15px]">{s.name}</span>
                      {s.instructor ? (
                        <span className="text-[13px] leading-tight text-text-2">{s.instructor.name}</span>
                      ) : null}
                    </span>
                    {section?.id === s.id ? <Check size={16} className="shrink-0 text-accent" /> : null}
                  </button>
                </li>
              ))}
            </ul>
            {course ? (
              <button
                type="button"
                onClick={() => {
                  select(null, null);
                  setOpen(false);
                }}
                className="mt-1 min-h-11 w-full rounded-chip px-2 text-left text-[13px] text-text-2 hover:bg-surface-2/70"
              >
                Clear course
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
