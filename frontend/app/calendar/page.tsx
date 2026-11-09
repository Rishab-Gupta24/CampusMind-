"use client";

import clsx from "clsx";
import { Bell, BellOff, CalendarPlus, Check, ChevronLeft, ChevronRight, Copy, Plus, Trash2, X } from "lucide-react";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";

import { PageTitle } from "@/components/PageTitle";
import { ENABLED_KEY, notify, remindersEnabled } from "@/components/ReminderService";
import { EmptyNote, ErrorNote, LoadingDots, inputClass } from "@/components/ui";
import { api, type CalendarEvent, type EventType } from "@/lib/api";
import { usePrefs } from "@/lib/prefs";
import { TYPE_LABEL, urgency } from "@/lib/urgency";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const TYPES: EventType[] = ["assignment", "deadline", "exam", "quiz", "lab", "other"];

const dayKey = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;

function formatWhen(e: CalendarEvent): string {
  const d = new Date(e.due_at);
  const date = d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
  if (e.all_day) return date;
  return `${date} · ${d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
}

function Dot({ color }: { color: string }) {
  return <span aria-hidden className="inline-block size-2.5 shrink-0 rounded-full" style={{ background: color }} />;
}

function EventRow({ e, onDelete }: { e: CalendarEvent; onDelete: (id: string) => void }) {
  const u = urgency(e);
  return (
    <li className="flex items-start gap-3 px-4 py-3">
      <span className="mt-1.5">
        <Dot color={u.color} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[17px] text-text">{e.title}</p>
        <p className="mt-0.5 flex flex-wrap gap-x-2 text-[13px] text-text-2 tabular-nums">
          <span>{TYPE_LABEL[e.type]}</span>
          {e.course_code ? <span>{e.course_code}</span> : null}
          <span>{formatWhen(e)}</span>
          {e.location ? <span>{e.location}</span> : null}
          {e.source_title ? (
            <span>
              From {e.source_title}
              {e.page ? `, p. ${e.page}` : ""}
            </span>
          ) : null}
        </p>
      </div>
      <span className="shrink-0 rounded-chip px-2 py-0.5 text-[13px] font-semibold tabular-nums" style={{ color: u.color, background: `color-mix(in srgb, ${u.color} 14%, transparent)` }}>
        {u.label}
      </span>
      <button
        type="button"
        onClick={() => onDelete(e.id)}
        aria-label={`Delete ${e.title}`}
        className="-mr-2 flex size-9 shrink-0 items-center justify-center rounded-chip text-text-2 hover:bg-surface-2 hover:text-danger"
      >
        <Trash2 size={15} strokeWidth={1.5} />
      </button>
    </li>
  );
}

function AddEventForm({ courseId, onDone }: { courseId: string | null; onDone: () => void }) {
  const { courses } = usePrefs();
  const [title, setTitle] = useState("");
  const [type, setType] = useState<EventType>("assignment");
  const [course, setCourse] = useState(courseId ?? "");
  const [due, setDue] = useState("");
  const [opens, setOpens] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !due) {
      setError("Add a title and a due date.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.createEvent({
        title: title.trim(),
        type,
        due_at: due,
        starts_at: opens || null,
        course_id: course || null,
        location: location.trim() || null,
      });
      onDone();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="grid gap-4 rounded-card bg-surface p-5 sm:grid-cols-2">
      <label className="flex flex-col gap-1.5 text-[13px] text-text-2 sm:col-span-2">
        Title
        <input className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} placeholder="e.g. Assignment 3" />
      </label>
      <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
        Type
        <select className={inputClass} value={type} onChange={(e) => setType(e.target.value as EventType)}>
          {TYPES.map((t) => (
            <option key={t} value={t}>
              {TYPE_LABEL[t]}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
        Course
        <select className={inputClass} value={course} onChange={(e) => setCourse(e.target.value)}>
          <option value="">Campus-wide</option>
          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.code}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
        {type === "exam" || type === "quiz" ? "Starts" : "Due"}
        <input type="datetime-local" className={inputClass} value={due} onChange={(e) => setDue(e.target.value)} />
      </label>
      {type === "assignment" || type === "deadline" ? (
        <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
          Given out (optional, sets the colour scale)
          <input type="datetime-local" className={inputClass} value={opens} onChange={(e) => setOpens(e.target.value)} />
        </label>
      ) : (
        <label className="flex flex-col gap-1.5 text-[13px] text-text-2">
          Room (optional)
          <input className={inputClass} value={location} onChange={(e) => setLocation(e.target.value)} maxLength={120} />
        </label>
      )}
      {error ? (
        <p role="alert" className="text-[15px] text-danger sm:col-span-2">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end sm:col-span-2">
        <button
          type="submit"
          disabled={saving}
          className="h-10 rounded-chip bg-accent px-4 text-[15px] font-semibold text-white hover:bg-accent/90 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Add to calendar"}
        </button>
      </div>
    </form>
  );
}

function Reminders({ feedUrl }: { feedUrl: string }) {
  const [on, setOn] = useState(false);
  const [copied, setCopied] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    queueMicrotask(() => setOn(remindersEnabled()));
  }, []);

  const toggle = async () => {
    if (typeof Notification === "undefined") {
      setNote("This browser can't show notifications. Use the calendar link instead.");
      return;
    }
    if (on) {
      try {
        window.localStorage.setItem(ENABLED_KEY, "0");
      } catch {
        // ignore
      }
      setOn(false);
      return;
    }
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      setNote("Notifications are blocked for this site. Allow them in the browser's site settings.");
      return;
    }
    try {
      window.localStorage.setItem(ENABLED_KEY, "1");
    } catch {
      // ignore
    }
    setOn(true);
    setNote("Reminders on: 1 day, 2 hours and 30 minutes before deadlines, while CampusMind is open.");
    notify("CampusMind reminders are on", "You'll be reminded before deadlines and exams.", "reminders-on");
  };

  const webcal = feedUrl.replace(/^https?:/, "webcal:");
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(feedUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setNote(feedUrl);
    }
  };

  return (
    <section className="flex flex-col gap-3 rounded-card bg-surface p-5">
      <h2 className="text-[17px] font-semibold">Reminders</h2>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={toggle}
          aria-pressed={on}
          className={clsx(
            "flex h-10 items-center gap-2 rounded-chip px-4 text-[15px]",
            on ? "bg-accent-soft font-semibold text-accent" : "bg-surface-2 text-text hover:bg-border/60",
          )}
        >
          {on ? <Bell aria-hidden size={16} strokeWidth={1.75} /> : <BellOff aria-hidden size={16} strokeWidth={1.5} />}
          {on ? "Browser reminders on" : "Turn on browser reminders"}
        </button>
        <a
          href={webcal}
          className="flex h-10 items-center gap-2 rounded-chip bg-surface-2 px-4 text-[15px] text-text hover:bg-border/60"
        >
          <CalendarPlus aria-hidden size={16} strokeWidth={1.5} /> Add to my calendar
        </a>
        <button
          type="button"
          onClick={copy}
          className="flex h-10 items-center gap-2 rounded-chip bg-surface-2 px-4 text-[15px] text-text hover:bg-border/60"
        >
          {copied ? <Check aria-hidden size={16} strokeWidth={1.75} /> : <Copy aria-hidden size={16} strokeWidth={1.5} />}
          {copied ? "Copied" : "Copy calendar link"}
        </button>
      </div>
      <p className="text-[13px] text-text-2">
        &ldquo;Add to my calendar&rdquo; subscribes Google, Outlook or Apple Calendar to these deadlines. Your phone then
        reminds you a day and a few hours before, even when CampusMind is closed.
      </p>
      {note ? <p className="text-[13px] text-text-2">{note}</p> : null}
    </section>
  );
}

export default function CalendarPage() {
  // Dates depend on "now", which can't be prerendered: render on the client inside Suspense.
  return (
    <Suspense fallback={<LoadingDots label="Loading calendar" />}>
      <CalendarView />
    </Suspense>
  );
}

function CalendarView() {
  const { course } = usePrefs();
  const [events, setEvents] = useState<CalendarEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [month, setMonth] = useState(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });
  const [selected, setSelected] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  const load = useCallback(() => {
    api
      .events({ course_id: course?.id, include_suggested: true })
      .then((list) => {
        setEvents(list);
        setError(null);
      })
      .catch((err: Error) => setError(err.message));
  }, [course?.id]);
  useEffect(load, [load]);

  const confirmed = useMemo(() => (events ?? []).filter((e) => e.status === "confirmed"), [events]);
  const suggested = useMemo(() => (events ?? []).filter((e) => e.status === "suggested"), [events]);
  // "Now" ticks every minute so colours and "time left" labels stay current while the page is open.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(timer);
  }, []);
  const upcoming = useMemo(
    () => confirmed.filter((e) => new Date(e.due_at).getTime() >= now).slice(0, 8),
    [confirmed, now],
  );

  const byDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const e of confirmed) {
      const key = dayKey(new Date(e.due_at));
      map.set(key, [...(map.get(key) ?? []), e]);
    }
    return map;
  }, [confirmed]);

  const cells = useMemo(() => {
    const first = new Date(month);
    const offset = (first.getDay() + 6) % 7; // Monday first
    const start = new Date(first.getFullYear(), first.getMonth(), 1 - offset);
    return Array.from({ length: 42 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
  }, [month]);

  const remove = async (id: string) => {
    try {
      await api.deleteEvent(id);
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  };
  const confirm = async (id: string) => {
    try {
      await api.updateEvent(id, { status: "confirmed" });
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const todayKey = dayKey(new Date());
  const selectedEvents = selected ? (byDay.get(selected) ?? []) : [];

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <PageTitle subtitle={course ? `Exams and deadlines for ${course.code}, plus campus-wide dates.` : "Exams and deadlines. Choose a course to focus the calendar."}>
          Calendar
        </PageTitle>
        <button
          type="button"
          onClick={() => setAdding((v) => !v)}
          className="flex h-10 items-center gap-2 rounded-chip bg-accent px-4 text-[15px] font-semibold text-white hover:bg-accent/90"
        >
          {adding ? <X aria-hidden size={16} strokeWidth={2} /> : <Plus aria-hidden size={16} strokeWidth={2} />}
          {adding ? "Close" : "Add event"}
        </button>
      </div>

      {adding ? (
        <AddEventForm
          courseId={course?.id ?? null}
          onDone={() => {
            setAdding(false);
            load();
          }}
        />
      ) : null}
      {error ? <ErrorNote>{error}</ErrorNote> : null}
      {!events && !error ? <LoadingDots label="Loading calendar" /> : null}

      {suggested.length ? (
        <section className="rounded-card bg-surface p-5">
          <h2 className="text-[17px] font-semibold">Dates found in your documents</h2>
          <p className="mt-1 text-[15px] text-text-2">Check each one against the source before adding it.</p>
          <ul className="mt-3 flex flex-col divide-y divide-border">
            {suggested.map((e) => (
              <li key={e.id} className="flex flex-wrap items-center gap-3 py-2.5">
                <div className="min-w-0 flex-1">
                  <p className="text-[15px] text-text">{e.title}</p>
                  <p className="text-[13px] text-text-2 tabular-nums">
                    {formatWhen(e)}
                    {e.source_title ? ` · ${e.source_title}${e.page ? `, p. ${e.page}` : ""}` : ""}
                    {e.notes ? ` · “${e.notes}”` : ""}
                  </p>
                </div>
                <button type="button" onClick={() => confirm(e.id)} className="h-9 rounded-chip bg-accent-soft px-3 text-[13px] font-semibold text-accent">
                  Add
                </button>
                <button type="button" onClick={() => remove(e.id)} className="h-9 rounded-chip px-3 text-[13px] text-text-2 hover:bg-surface-2">
                  Dismiss
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {events ? (
        <section>
          <h2 className="mb-2 text-[17px] font-semibold">Coming up</h2>
          {upcoming.length ? (
            <ul className="flex flex-col divide-y divide-border overflow-hidden rounded-card bg-surface">
              {upcoming.map((e) => (
                <EventRow key={e.id} e={e} onDelete={remove} />
              ))}
            </ul>
          ) : (
            <EmptyNote>Nothing coming up. Add an assignment or exam, or upload a course handout.</EmptyNote>
          )}
          <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-text-2">
            <span className="flex items-center gap-1.5"><Dot color="var(--event-exam)" /> Exam or quiz</span>
            <span className="flex items-center gap-1.5"><Dot color="var(--urgency-green)" /> Plenty of time</span>
            <span className="flex items-center gap-1.5"><Dot color="var(--urgency-yellow)" /> Getting close</span>
            <span className="flex items-center gap-1.5"><Dot color="var(--urgency-orange)" /> Soon</span>
            <span className="flex items-center gap-1.5"><Dot color="var(--urgency-red)" /> Under a day</span>
          </p>
        </section>
      ) : null}

      <section className="rounded-card bg-surface p-3 sm:p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-[17px] font-semibold">
            {month.toLocaleDateString("en-GB", { month: "long", year: "numeric" })}
          </h2>
          <div className="flex gap-1">
            <button type="button" aria-label="Previous month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))} className="flex size-10 items-center justify-center rounded-chip hover:bg-surface-2">
              <ChevronLeft size={18} strokeWidth={1.5} />
            </button>
            <button type="button" aria-label="Next month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))} className="flex size-10 items-center justify-center rounded-chip hover:bg-surface-2">
              <ChevronRight size={18} strokeWidth={1.5} />
            </button>
          </div>
        </div>
        <div className="grid grid-cols-7 gap-px text-center text-[12px] text-text-2">
          {WEEKDAYS.map((d) => (
            <div key={d} className="pb-1">
              {d}
            </div>
          ))}
        </div>
        <div className="grid grid-cols-7 gap-1">
          {cells.map((d) => {
            const key = dayKey(d);
            const dayEvents = byDay.get(key) ?? [];
            const inMonth = d.getMonth() === month.getMonth();
            return (
              <button
                key={key}
                type="button"
                onClick={() => setSelected(key === selected ? null : key)}
                aria-label={`${d.toLocaleDateString("en-GB", { day: "numeric", month: "long" })}${dayEvents.length ? `, ${dayEvents.length} events` : ""}`}
                className={clsx(
                  "flex min-h-14 flex-col items-stretch gap-0.5 rounded-chip p-1 text-left sm:min-h-20",
                  selected === key ? "bg-accent-soft" : "hover:bg-surface-2",
                  !inMonth && "opacity-40",
                )}
              >
                <span className={clsx("text-[13px] tabular-nums", key === todayKey ? "font-semibold text-accent" : "text-text-2")}>
                  {d.getDate()}
                </span>
                {dayEvents.slice(0, 2).map((e) => {
                  const u = urgency(e);
                  return (
                    <span
                      key={e.id}
                      className="truncate rounded px-1 text-[11px] leading-4 font-semibold max-sm:h-1.5 max-sm:rounded-full max-sm:p-0 max-sm:text-transparent"
                      style={{ color: u.color, background: `color-mix(in srgb, ${u.color} 16%, transparent)` }}
                    >
                      {e.title.replace(/^Demo:\s*/, "")}
                    </span>
                  );
                })}
                {dayEvents.length > 2 ? <span className="text-[11px] text-text-2">+{dayEvents.length - 2}</span> : null}
              </button>
            );
          })}
        </div>
        {selected ? (
          <div className="mt-3">
            {selectedEvents.length ? (
              <ul className="flex flex-col divide-y divide-border rounded-card bg-surface-2/50">
                {selectedEvents.map((e) => (
                  <EventRow key={e.id} e={e} onDelete={remove} />
                ))}
              </ul>
            ) : (
              <p className="px-1 text-[15px] text-text-2">Nothing on this day.</p>
            )}
          </div>
        ) : null}
      </section>

      <Reminders feedUrl={api.calendarFeedUrl(course?.id)} />
    </section>
  );
}
