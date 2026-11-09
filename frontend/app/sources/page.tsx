"use client";

import { Plus, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { AddDocumentCard } from "@/components/AddDocumentCard";
import { KindBadge } from "@/components/Badge";
import { PageTitle } from "@/components/PageTitle";
import { EmptyNote, ErrorNote, LoadingDots, StatusText, Tabs } from "@/components/ui";
import { api, type DocumentItem, type Insights } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { usePrefs } from "@/lib/prefs";

type Tab = "documents" | "insights";

const KIND_LABEL: Record<string, string> = {
  campus: "Campus rule",
  handout: "Course handout",
  material: "Course material",
  lecture: "Lecture",
};

export default function SourcesPage() {
  const [tab, setTab] = useState<Tab>("documents");
  return (
    <section>
      <PageTitle subtitle="What CampusMind knows, and what students asked that it couldn't answer.">Sources</PageTitle>
      <Tabs
        label="Sources sections"
        value={tab}
        onChange={setTab}
        tabs={[
          { value: "documents", label: "Documents" },
          { value: "insights", label: "Insights" },
        ]}
      />
      <div className="mt-5">{tab === "documents" ? <Documents /> : <InsightsTab />}</div>
    </section>
  );
}

function Documents() {
  const { courses, course } = usePrefs();
  const [docs, setDocs] = useState<DocumentItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [confirming, setConfirming] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .documents()
      .then((list) => {
        setDocs(list);
        setError(null);
      })
      .catch((err: Error) => setError(err.message));
  }, []);
  useEffect(load, [load]);

  const remove = async (id: string) => {
    try {
      await api.deleteDocument(id);
      setConfirming(null);
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const code = (id: string | null) => (id ? (courses.find((c) => c.id === id)?.code ?? "") : "Campus");

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[15px] text-text-2">{docs ? `${docs.length} documents` : ""}</p>
        <button
          type="button"
          onClick={() => setAdding((v) => !v)}
          className="flex h-10 items-center gap-2 rounded-chip bg-accent px-4 text-[15px] font-semibold text-white hover:bg-accent/90"
        >
          {adding ? <X aria-hidden size={16} strokeWidth={2} /> : <Plus aria-hidden size={16} strokeWidth={2} />}
          {adding ? "Close" : "Add document"}
        </button>
      </div>
      {adding ? <AddDocumentCard courses={courses} defaultCourseId={course?.id ?? null} onDone={load} /> : null}
      {error ? <ErrorNote>{error}</ErrorNote> : null}
      {!docs && !error ? <LoadingDots label="Loading documents" /> : null}
      {docs && docs.length === 0 ? <EmptyNote>No documents yet. Add regulations, handouts or circulars.</EmptyNote> : null}
      {docs && docs.length > 0 ? (
        <div className="overflow-x-auto rounded-card bg-surface [contain:inline-size]">
          <table className="w-full text-left text-[15px]">
            <thead className="text-[13px] text-text-2">
              <tr className="border-b border-border">
                <th className="px-4 py-2.5 font-normal">Title</th>
                <th className="px-2 py-2.5 font-normal max-sm:hidden">Type</th>
                <th className="px-2 py-2.5 font-normal max-sm:hidden">Course</th>
                <th className="px-2 py-2.5 font-normal tabular-nums max-sm:hidden">Pages</th>
                <th className="px-2 py-2.5 font-normal">Status</th>
                <th className="px-2 py-2.5 font-normal">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {docs.map((d) => (
                <tr key={d.id}>
                  <td className="px-4 py-2.5 sm:max-w-[260px]">
                    <span className="block break-words text-text sm:truncate">{d.title}</span>
                    <span className="block text-[13px] text-text-2 sm:hidden">
                      {[KIND_LABEL[d.kind], code(d.course_id), d.pages ? `${d.pages} pages` : ""].filter(Boolean).join(" · ")}
                    </span>
                    {d.source_date ? <span className="text-[13px] text-text-2">{formatDate(d.source_date)}</span> : null}
                  </td>
                  <td className="px-2 py-2.5 max-sm:hidden">
                    <KindBadge kind={d.kind} />
                  </td>
                  <td className="px-2 py-2.5 whitespace-nowrap text-text-2 max-sm:hidden">{code(d.course_id)}</td>
                  <td className="px-2 py-2.5 text-text-2 tabular-nums max-sm:hidden">{d.pages ?? ""}</td>
                  <td className="px-2 py-2.5" title={d.error ?? undefined}>
                    <StatusText status={d.status} stage={d.stage} />
                  </td>
                  <td className="px-2 py-1.5 text-right whitespace-nowrap">
                    {confirming === d.id ? (
                      <span className="inline-flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => remove(d.id)}
                          className="h-9 rounded-chip px-3 text-[13px] font-semibold text-danger hover:bg-surface-2"
                        >
                          Delete
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirming(null)}
                          className="h-9 rounded-chip px-3 text-[13px] text-text-2 hover:bg-surface-2"
                        >
                          Cancel
                        </button>
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setConfirming(d.id)}
                        aria-label={`Delete ${d.title}`}
                        className="inline-flex size-11 items-center justify-center rounded-chip text-text-2 hover:bg-surface-2 hover:text-danger"
                      >
                        <Trash2 size={16} strokeWidth={1.5} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function InsightsTab() {
  const [data, setData] = useState<Insights | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .insights()
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <ErrorNote>{error}</ErrorNote>;
  if (!data) return <LoadingDots label="Loading insights" />;

  return (
    <div className="flex flex-col gap-8">
      <section>
        <h2 className="text-[17px] font-semibold">Questions CampusMind couldn&apos;t answer</h2>
        <p className="mt-1 text-[15px] text-text-2">Each one points at a document or lecture worth adding.</p>
        <div className="mt-3">
          {data.unanswered.length === 0 ? (
            <EmptyNote>Nothing yet. Questions without a good source show up here.</EmptyNote>
          ) : (
            <div className="overflow-x-auto rounded-card bg-surface [contain:inline-size]">
              <table className="w-full text-left text-[15px]">
                <thead className="text-[13px] text-text-2">
                  <tr className="border-b border-border">
                    <th className="px-4 py-2.5 font-normal">Question</th>
                    <th className="px-2 py-2.5 text-right font-normal">Times asked</th>
                    <th className="px-4 py-2.5 text-right font-normal">Last asked</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.unanswered.map((u) => (
                    <tr key={u.question}>
                      <td className="px-4 py-2.5 text-text">{u.question}</td>
                      <td className="px-2 py-2.5 text-right text-text-2 tabular-nums">{u.count}</td>
                      <td className="px-4 py-2.5 text-right whitespace-nowrap text-text-2">{formatDate(u.last_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
      <section>
        <h2 className="text-[17px] font-semibold">Answers rated down</h2>
        <p className="mt-1 text-[15px] text-text-2">Check these against the sources; add them to the eval set if wrong.</p>
        <div className="mt-3">
          {data.thumbs_down.length === 0 ? (
            <EmptyNote>No answers have been rated down.</EmptyNote>
          ) : (
            <ul className="flex flex-col divide-y divide-border overflow-hidden rounded-card bg-surface">
              {data.thumbs_down.map((t) => (
                <li key={t.answer_id}>
                  <details className="group px-4 py-3">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-[15px]">
                      <span className="text-text">{t.question}</span>
                      <span className="shrink-0 text-[13px] text-text-2">{formatDate(t.created_at)}</span>
                    </summary>
                    <p className="mt-2 text-[15px] leading-relaxed text-text-2">{t.answer}</p>
                  </details>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
