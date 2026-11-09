// The only way the frontend talks to the backend (Rules.md §1.24). Types follow the backend responses.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const OFFLINE = "CampusMind can't reach the server. Check that the backend is running.";
const GENERIC = "Something went wrong. Please try again.";

// ---------- Types ----------

export type Role = "ic" | "hod" | "instructor";
export type Scope = "all" | "docs" | "lectures";
export type SourceKind = "campus" | "handout" | "material" | "lecture";
export type Status = "processing" | "ready" | "failed";
export type Stage = "preparing" | "transcribing" | "flagging" | "indexing" | "notes";
export type BadgeName = "Official" | "IC" | "HOD" | "Flagged" | "Your section";

export interface Instructor {
  id?: string;
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

export interface AskRequest {
  question: string;
  scope: Scope;
  course_id?: string | null;
  section_id?: string | null;
  lecture_id?: string | null;
}

export interface SourceRef {
  n: number;
  title: string;
  kind: SourceKind;
  page: number | null;
  start_s: number | null;
  source_id: string;
  chunk_id: string;
  excerpt: string;
  badges: BadgeName[];
  flag_reason: string | null;
  instructor: Instructor | null;
}

export interface AskHandlers {
  onToken: (text: string) => void;
  onSources: (sources: SourceRef[]) => void;
  onNotFound: (message: string) => void;
  onDone: (answerId: string | null, answer: string) => void;
  onError: (message: string) => void;
}

export interface DocumentItem {
  id: string;
  title: string;
  kind: SourceKind;
  course_id: string | null;
  pages: number | null;
  source_date: string | null;
  status: Status;
  error: string | null;
  created_at: string;
  file_url?: string | null;
}

export interface LectureItem {
  id: string;
  title: string;
  course_id: string | null;
  section_id: string | null;
  section: string | null;
  instructor: Instructor | null;
  source_date: string | null;
  duration_s: number | null;
  status: Status;
  stage: Stage | null;
  error: string | null;
}

export interface TranscriptLine {
  start_s: number;
  end_s: number;
  text: string;
  flagged: boolean;
}

export interface FlaggedMoment {
  source_id: string;
  title: string;
  source_date: string | null;
  start_s: number;
  end_s: number;
  reason: string;
  quote: string;
  instructor: Instructor | null;
  section: string | null;
}

export interface LectureDetail extends LectureItem {
  transcript: TranscriptLine[];
  summary: string;
  key_points: string[];
  formulas: string[];
  flagged: FlaggedMoment[];
  audio_url: string | null;
}

export interface Insights {
  unanswered: { question: string; count: number; last_at: string }[];
  thumbs_down: { answer_id: string; question: string; answer: string; created_at: string }[];
}

export interface Health {
  ollama: boolean;
  supabase: boolean;
  llm_model: string;
  chunks: number;
}

export class ApiError extends Error {}

// ---------- HTTP helpers ----------

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(OFFLINE);
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { error?: string } | null;
    throw new ApiError(body?.error ?? GENERIC);
  }
  return (await res.json()) as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function query(params: Record<string, string | null | undefined>): string {
  const entries = Object.entries(params).filter((e): e is [string, string] => Boolean(e[1]));
  return entries.length ? `?${new URLSearchParams(entries).toString()}` : "";
}

// ---------- Ask (SSE over a POST body) ----------

function dispatch(name: string, payload: string, h: AskHandlers): void {
  const data = payload ? (JSON.parse(payload) as Record<string, unknown>) : {};
  switch (name) {
    case "token":
      h.onToken(String(data.text ?? ""));
      break;
    case "sources":
      h.onSources(data as unknown as SourceRef[]);
      break;
    case "not_found":
      h.onNotFound(String(data.message ?? ""));
      break;
    case "done":
      h.onDone((data.answer_id as string | null) ?? null, String(data.answer ?? ""));
      break;
    case "error":
      h.onError(String(data.error ?? GENERIC));
      break;
  }
}

export async function ask(req: AskRequest, handlers: AskHandlers, signal?: AbortSignal): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/ask`, {
      ...json(req),
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      signal,
    });
  } catch (err) {
    if ((err as Error).name !== "AbortError") handlers.onError(OFFLINE);
    return;
  }
  if (!res.ok || !res.body) {
    const body = (await res.json().catch(() => null)) as { error?: string } | null;
    handlers.onError(body?.error ?? GENERIC);
    return;
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value.replace(/\r\n/g, "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const raw = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        let name = "message";
        const data: string[] = [];
        for (const line of raw.split("\n")) {
          if (line.startsWith("event:")) name = line.slice(6).trim();
          else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
        }
        dispatch(name, data.join("\n"), handlers);
        boundary = buffer.indexOf("\n\n");
      }
    }
  } catch (err) {
    if ((err as Error).name !== "AbortError") handlers.onError(OFFLINE);
  }
}

// ---------- Uploads with progress (fetch has no upload progress) ----------

export function upload(
  path: "/api/documents" | "/api/lectures",
  form: FormData,
  onProgress: (fraction: number) => void,
): Promise<{ source_id: string; status: Status }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}${path}`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total);
    };
    xhr.onload = () => {
      type UploadBody = { error?: string; source_id?: string; status?: Status };
      let body: UploadBody | null;
      try {
        body = JSON.parse(xhr.responseText) as UploadBody;
      } catch {
        body = null;
      }
      if (xhr.status >= 200 && xhr.status < 300 && body?.source_id) {
        resolve({ source_id: body.source_id, status: body.status ?? "processing" });
      } else {
        reject(new ApiError(body?.error ?? GENERIC));
      }
    };
    xhr.onerror = () => reject(new ApiError(OFFLINE));
    xhr.send(form);
  });
}

// ---------- Endpoints ----------

export const api = {
  health: () => request<Health>("/api/health"),
  courses: () => request<Course[]>("/api/courses"),
  feedback: (answer_id: string, rating: 1 | -1) =>
    request<{ ok: boolean }>("/api/feedback", json({ answer_id, rating })),

  documents: () => request<DocumentItem[]>("/api/documents"),
  document: (id: string) => request<DocumentItem>(`/api/documents/${encodeURIComponent(id)}`),
  deleteDocument: (id: string) =>
    request<{ ok: boolean }>(`/api/documents/${encodeURIComponent(id)}`, { method: "DELETE" }),

  lectures: (courseId?: string | null) => request<LectureItem[]>(`/api/lectures${query({ course_id: courseId })}`),
  lecture: (id: string) => request<LectureDetail>(`/api/lectures/${encodeURIComponent(id)}`),

  flagged: (courseId?: string | null) => request<FlaggedMoment[]>(`/api/flagged${query({ course_id: courseId })}`),
  insights: () => request<Insights>("/api/insights"),
};
