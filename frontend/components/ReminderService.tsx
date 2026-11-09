"use client";

import { useEffect } from "react";

import { api, type CalendarEvent } from "@/lib/api";
import { usePrefs } from "@/lib/prefs";
import { TYPE_LABEL, timeLeft } from "@/lib/urgency";

const SENT_KEY = "campusmind.reminders.sent";
export const ENABLED_KEY = "campusmind.reminders.on";
const HOUR = 3_600_000;
// Remind 1 day, 2 hours and 30 minutes before a deadline; 1 day and 1 hour before an exam or quiz.
const DEADLINE_STEPS = [24 * HOUR, 2 * HOUR, 0.5 * HOUR];
const EXAM_STEPS = [24 * HOUR, HOUR];

function readSent(): Set<string> {
  try {
    return new Set(JSON.parse(window.localStorage.getItem(SENT_KEY) ?? "[]") as string[]);
  } catch {
    return new Set();
  }
}

function writeSent(sent: Set<string>): void {
  try {
    window.localStorage.setItem(SENT_KEY, JSON.stringify([...sent].slice(-300)));
  } catch {
    // Without storage a reminder may repeat after a reload; acceptable.
  }
}

export function remindersEnabled(): boolean {
  try {
    return (
      typeof Notification !== "undefined" &&
      Notification.permission === "granted" &&
      window.localStorage.getItem(ENABLED_KEY) === "1"
    );
  } catch {
    return false;
  }
}

/** System notification through the service worker when installed (works on phones), else the page API. */
export function notify(title: string, body: string, tag: string): void {
  const options = { body, tag, icon: "/icons/icon-192.png", badge: "/icons/icon-192.png" };
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.getRegistration().then((reg) => {
      if (reg) {
        reg.showNotification(title, options).catch(() => undefined);
        return;
      }
      try {
        new Notification(title, options);
      } catch {
        // The subscribed calendar still reminds.
      }
    });
    return;
  }
  try {
    new Notification(title, options);
  } catch {
    // The subscribed calendar still reminds.
  }
}

function check(events: CalendarEvent[]): void {
  if (!remindersEnabled()) return;
  const now = Date.now();
  const sent = readSent();
  for (const e of events) {
    const left = new Date(e.due_at).getTime() - now;
    if (left <= 0) continue;
    const steps = e.type === "exam" || e.type === "quiz" ? EXAM_STEPS : e.type === "assignment" || e.type === "deadline" ? DEADLINE_STEPS : [];
    // The smallest step we're already inside is the one to announce (once).
    const step = [...steps].sort((a, b) => a - b).find((s) => left <= s);
    if (step === undefined) continue;
    const key = `${e.id}:${step}`;
    if (sent.has(key)) continue;
    sent.add(key);
    const title = `${TYPE_LABEL[e.type]}: ${e.title}`;
    const body = `${e.course_code ? `${e.course_code} · ` : ""}${timeLeft(left)}${e.location ? ` · ${e.location}` : ""}`;
    notify(title, body, key);
  }
  writeSent(sent);
}

/** While CampusMind is open (any tab), shows browser notifications for upcoming deadlines and exams. */
export function ReminderService() {
  const { course } = usePrefs();

  useEffect(() => {
    let events: CalendarEvent[] = [];
    let cancelled = false;
    const load = async () => {
      try {
        events = await api.events({ course_id: course?.id, start: new Date().toISOString() });
        if (!cancelled) check(events);
      } catch {
        // Backend offline: try again on the next tick.
      }
    };
    load();
    const tick = setInterval(() => check(events), 60_000);
    const refresh = setInterval(load, 10 * 60_000);
    return () => {
      cancelled = true;
      clearInterval(tick);
      clearInterval(refresh);
    };
  }, [course?.id]);

  return null;
}
