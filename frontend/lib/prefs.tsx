"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, type Course, type Section } from "@/lib/api";

const STORAGE_KEY = "campusmind.course";

interface Saved {
  courseId: string | null;
  sectionId: string | null;
}

interface PrefsValue {
  courses: Course[];
  loading: boolean;
  error: string | null;
  course: Course | null;
  section: Section | null;
  select: (courseId: string | null, sectionId: string | null) => void;
}

const PrefsContext = createContext<PrefsValue | null>(null);

function readSaved(): Saved {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as Saved;
  } catch {
    // Private mode or blocked storage: start without a saved choice.
  }
  return { courseId: null, sectionId: null };
}

function writeSaved(saved: Saved): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
  } catch {
    // Not remembered on this device; the choice still works for this visit.
  }
}

export function PrefsProvider({ children }: { children: React.ReactNode }) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<Saved>({ courseId: null, sectionId: null });

  useEffect(() => {
    api
      .courses()
      .then((list) => {
        setCourses(list);
        setSaved(readSaved());
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const select = useCallback((courseId: string | null, sectionId: string | null) => {
    const next = { courseId, sectionId };
    setSaved(next);
    writeSaved(next);
  }, []);

  const value = useMemo<PrefsValue>(() => {
    const course = courses.find((c) => c.id === saved.courseId) ?? null;
    const section = course?.sections.find((s) => s.id === saved.sectionId) ?? null;
    return { courses, loading, error, course, section, select };
  }, [courses, loading, error, saved, select]);

  return <PrefsContext.Provider value={value}>{children}</PrefsContext.Provider>;
}

export function usePrefs(): PrefsValue {
  const value = useContext(PrefsContext);
  if (!value) throw new Error("usePrefs must be used inside PrefsProvider");
  return value;
}
