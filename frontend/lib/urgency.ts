import type { CalendarEvent } from "@/lib/api";

export type Level = "exam" | "green" | "yellow" | "orange" | "red" | "past" | "neutral";

export interface Urgency {
  level: Level;
  color: string; // CSS variable
  label: string; // always shown next to the colour: colour is never the only signal
}

const HOUR = 3_600_000;
const DAY = 24 * HOUR;

const COLOR: Record<Level, string> = {
  exam: "var(--event-exam)",
  green: "var(--urgency-green)",
  yellow: "var(--urgency-yellow)",
  orange: "var(--urgency-orange)",
  red: "var(--urgency-red)",
  past: "var(--event-neutral)",
  neutral: "var(--event-neutral)",
};

export function timeLeft(ms: number): string {
  if (ms < 0) return "past";
  if (ms < HOUR) return `${Math.max(1, Math.round(ms / 60_000))} min left`;
  if (ms < DAY) return `${Math.round(ms / HOUR)} h left`;
  const days = Math.round(ms / DAY);
  return `${days} day${days === 1 ? "" : "s"} left`;
}

/**
 * Exams and quizzes are always red. Assignments and deadlines move green → yellow → orange as time runs
 * out (share of the time from opening to due), and turn bright red in the last 24 hours. Without an
 * opening date, fixed thresholds are used: more than 7 days green, more than 3 days yellow.
 */
export function urgency(event: Pick<CalendarEvent, "type" | "due_at" | "starts_at">, now = Date.now()): Urgency {
  const due = new Date(event.due_at).getTime();
  const left = due - now;
  const make = (level: Level, label: string): Urgency => ({ level, color: COLOR[level], label });

  if (left < 0) return make("past", event.type === "exam" || event.type === "quiz" ? "Done" : "Past due");
  if (event.type === "exam" || event.type === "quiz") return make("exam", `${event.type === "exam" ? "Exam" : "Quiz"} · ${timeLeft(left)}`);
  if (event.type !== "assignment" && event.type !== "deadline") return make("neutral", timeLeft(left));

  if (left < DAY) return make("red", `Due in ${timeLeft(left).replace(" left", "")}`);
  let share: number;
  if (event.starts_at) {
    const total = due - new Date(event.starts_at).getTime();
    share = total > 0 ? left / total : 0;
    if (share > 0.5) return make("green", timeLeft(left));
    if (share > 0.25) return make("yellow", timeLeft(left));
    return make("orange", timeLeft(left));
  }
  if (left > 7 * DAY) return make("green", timeLeft(left));
  if (left > 3 * DAY) return make("yellow", timeLeft(left));
  return make("orange", timeLeft(left));
}

export const TYPE_LABEL: Record<CalendarEvent["type"], string> = {
  exam: "Exam",
  quiz: "Quiz",
  assignment: "Assignment",
  lab: "Lab",
  deadline: "Deadline",
  class: "Class",
  other: "Event",
};
