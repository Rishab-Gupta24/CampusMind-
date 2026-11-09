import type { Role, SourceRef } from "@/lib/api";

export function formatTime(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = h ? String(m).padStart(2, "0") : String(m);
  return `${h ? `${h}:` : ""}${mm}:${String(s).padStart(2, "0")}`;
}

export function formatDuration(seconds: number | null): string {
  if (!seconds) return "";
  const minutes = Math.round(seconds / 60);
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

export function formatDate(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export const ROLE_LABEL: Record<Role, string> = { ic: "IC", hod: "HOD", instructor: "Instructor" };
export const ROLE_TITLE: Record<Role, string> = {
  ic: "Instructor-in-Charge",
  hod: "Head of Department",
  instructor: "Section instructor",
};

/** "Academic Regulations · p. 12" or "MATH F113 Lecture 4 · 12:40". */
export function sourceLabel(s: Pick<SourceRef, "title" | "page" | "start_s">): string {
  if (s.start_s !== null && s.start_s !== undefined) return `${s.title} · ${formatTime(s.start_s)}`;
  if (s.page !== null && s.page !== undefined) return `${s.title} · p. ${s.page}`;
  return s.title;
}
