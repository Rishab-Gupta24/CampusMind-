// The only way the frontend talks to the backend (Rules.md §1.24).
// Types follow docs/Architecture.md §7. With NEXT_PUBLIC_USE_MOCK=true every call returns mock data.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";

// ---------- Types ----------

export type Role = "ic" | "hod" | "instructor";
export type Scope = "all" | "docs" | "lectures";
export type SourceKind = "campus" | "handout" | "lecture";
export type Status = "processing" | "ready" | "failed";
export type BadgeName = "Official" | "IC" | "HOD" | "Flagged" | "Your section";

export interface Instructor {
  name: string;
  role: Role;
}

export interface Section {
  id: string;
  name: string;
  instructor: Instructor | null;
}

export interface Course {
  id: string;
  code: string;
  title: string;
  sections: Section[];
}

export interface Health {
  ollama: boolean;
  supabase: boolean;
  llm_model: string;
  chunks: number;
}

export interface AskRequest {
  question: string;
  scope: Scope;
  course_id?: string;
  section_id?: string;
  lecture_id?: string;
}

export interface SourceRef {
  n: number;
  title: string;
  kind: SourceKind;
  page?: number;
  start_s?: number;
  source_id: string;
  chunk_id: string;
  excerpt: string;
  badges: BadgeName[];
  flag_reason?: string | null;
  instructor?: Instructor | null;
}

export type AskEvent =
  | { type: "token"; text: string }
  | { type: "sources"; sources: SourceRef[] }
  | { type: "not_found"; message: string }
  | { type: "done"; answer_id: string; answer: string }
  | { type: "error"; error: string };

export interface DocumentItem {
  id: string;
  title: string;
  kind: SourceKind;
  course_id: string | null;
  pages: number | null;
  source_date: string | null;
  status: Status;
}

export interface LectureItem {
  id: string;
  title: string;
  course_id: string;
  section_id: string;
  instructor: Instructor | null;
  source_date: string | null;
  duration_s: number | null;
  status: Status;
}

export interface TranscriptLine {
  start_s: number;
  end_s: number;
  text: string;
  flagged?: boolean;
}

export interface FlaggedMoment {
  source_id: string;
  title: string;
  start_s: number;
  reason: string;
  instructor: Instructor | null;
}

export interface LectureDetail {
  status: Status;
  transcript: TranscriptLine[];
  summary: string;
  key_points: string[];
  formulas: string[];
  flagged: FlaggedMoment[];
  audio_url: string | null;
}

export interface Insights {
  unanswered: { question: string; count: number; last_at: string }[];
  thumbs_down: { answer_id: string; question: string; created_at: string }[];
}

export class ApiError extends Error {}

// ---------- HTTP helpers ----------

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError("CampusMind can't reach the server. Check that the backend is running.");
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { error?: string } | null;
    throw new ApiError(body?.error ?? "Something went wrong. Please try again.");
  }
  return (await res.json()) as T;
}

// ---------- Mock data (until the backend endpoints exist) ----------

const MOCK_COURSES: Course[] = [
  {
    id: "00000000-0000-0000-0000-0000000000c1",
    code: "MATH F113",
    title: "Probability and Statistics",
    sections: [
      { id: "00000000-0000-0000-0000-0000000000d1", name: "L1", instructor: { name: "Dr. Asha Demo", role: "ic" } },
      { id: "00000000-0000-0000-0000-0000000000d2", name: "L2", instructor: { name: "Dr. Chen Example", role: "instructor" } },
    ],
  },
];

const MOCK_SOURCES: SourceRef[] = [
  {
    n: 1,
    title: "Academic Regulations",
    kind: "campus",
    page: 12,
    source_id: "mock-regulations",
    chunk_id: "mock-regulations_12_0",
    excerpt: "A student who misses a mid-semester test for a genuine reason may apply for a makeup test.",
    badges: ["Official"],
  },
  {
    n: 2,
    title: "MATH F113 · Lecture 4",
    kind: "lecture",
    start_s: 760,
    source_id: "mock-lecture-4",
    chunk_id: "mock-lecture-4_760_0",
    excerpt: "Bayes' theorem with two events — this will definitely come in the exam.",
    badges: ["Flagged", "IC"],
  },
];

const NOT_FOUND = "I couldn't find this in the campus sources. Try rephrasing, or check with the academic office.";

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

async function* mockAsk(req: AskRequest): AsyncGenerator<AskEvent> {
  await wait(400);
  if (/weather|cricket|movie/i.test(req.question)) {
    yield { type: "not_found", message: NOT_FOUND };
    return;
  }
  const answer = "Apply to the Instructor-in-Charge for a makeup test within the stated window [1]. ";
  for (const word of answer.split(/(?<= )/)) {
    await wait(40);
    yield { type: "token", text: word };
  }
  yield { type: "sources", sources: MOCK_SOURCES.slice(0, 1) };
  yield { type: "done", answer_id: "mock-answer", answer };
}

// ---------- SSE parsing for POST /api/ask ----------

async function* streamAsk(req: AskRequest): AsyncGenerator<AskEvent> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(req),
    });
  } catch {
    yield { type: "error", error: "CampusMind can't reach the server. Check that the backend is running." };
    return;
  }
  if (!res.ok || !res.body) {
    const body = (await res.json().catch(() => null)) as { error?: string } | null;
    yield { type: "error", error: body?.error ?? "Something went wrong. Please try again." };
    return;
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value.replace(/\r\n/g, "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const raw = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const event = parseSseEvent(raw);
      if (event) yield event;
      boundary = buffer.indexOf("\n\n");
    }
  }
}

function parseSseEvent(raw: string): AskEvent | null {
  let name = "message";
  const data: string[] = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) name = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
  }
  const payload = data.join("\n");
  switch (name) {
    case "token":
      return { type: "token", text: (JSON.parse(payload) as { text: string }).text };
    case "sources":
      return { type: "sources", sources: JSON.parse(payload) as SourceRef[] };
    case "not_found":
      return { type: "not_found", message: (JSON.parse(payload) as { message: string }).message };
    case "done": {
      const done = JSON.parse(payload) as { answer_id: string; answer: string };
      return { type: "done", answer_id: done.answer_id, answer: done.answer };
    }
    case "error":
      return { type: "error", error: (JSON.parse(payload) as { error: string }).error };
    default:
      return null;
  }
}

// ---------- Public API ----------

export const api = {
  health: (): Promise<Health> =>
    USE_MOCK
      ? Promise.resolve({ ollama: true, supabase: true, llm_model: "mock", chunks: 0 })
      : request<Health>("/api/health"),

  courses: (): Promise<Course[]> => (USE_MOCK ? Promise.resolve(MOCK_COURSES) : request<Course[]>("/api/courses")),

  ask: (req: AskRequest): AsyncGenerator<AskEvent> => (USE_MOCK ? mockAsk(req) : streamAsk(req)),

  feedback: (answer_id: string, rating: 1 | -1): Promise<{ ok: boolean }> =>
    USE_MOCK
      ? Promise.resolve({ ok: true })
      : request("/api/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ answer_id, rating }),
        }),

  documents: {
    list: (): Promise<DocumentItem[]> => (USE_MOCK ? Promise.resolve([]) : request<DocumentItem[]>("/api/documents")),
    upload: (form: FormData): Promise<{ source_id: string; status: Status }> =>
      USE_MOCK
        ? Promise.resolve({ source_id: "mock-doc", status: "processing" })
        : request("/api/documents", { method: "POST", body: form }),
    remove: (id: string): Promise<{ ok: boolean }> =>
      USE_MOCK ? Promise.resolve({ ok: true }) : request(`/api/documents/${id}`, { method: "DELETE" }),
  },

  lectures: {
    list: (courseId?: string): Promise<LectureItem[]> =>
      USE_MOCK
        ? Promise.resolve([])
        : request<LectureItem[]>(`/api/lectures${courseId ? `?course_id=${encodeURIComponent(courseId)}` : ""}`),
    get: (id: string): Promise<LectureDetail> =>
      USE_MOCK
        ? Promise.resolve({
            status: "ready",
            transcript: [],
            summary: "",
            key_points: [],
            formulas: [],
            flagged: [],
            audio_url: null,
          })
        : request<LectureDetail>(`/api/lectures/${encodeURIComponent(id)}`),
    upload: (form: FormData): Promise<{ source_id: string; status: Status }> =>
      USE_MOCK
        ? Promise.resolve({ source_id: "mock-lecture", status: "processing" })
        : request("/api/lectures", { method: "POST", body: form }),
  },

  flagged: (courseId: string): Promise<FlaggedMoment[]> =>
    USE_MOCK ? Promise.resolve([]) : request<FlaggedMoment[]>(`/api/flagged?course_id=${encodeURIComponent(courseId)}`),

  insights: (): Promise<Insights> =>
    USE_MOCK ? Promise.resolve({ unanswered: [], thumbs_down: [] }) : request<Insights>("/api/insights"),
};
