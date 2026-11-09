"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { RoleBadge } from "@/components/Badge";
import { PageTitle } from "@/components/PageTitle";
import { FlaggedList } from "@/components/Transcript";
import { EmptyNote, ErrorNote, LoadingDots } from "@/components/ui";
import { api, type FlaggedMoment } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { usePrefs } from "@/lib/prefs";

export default function FlaggedPage() {
  const router = useRouter();
  const { course } = usePrefs();
  const [moments, setMoments] = useState<FlaggedMoment[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .flagged(course?.id)
      .then((list) => {
        if (!cancelled) {
          setMoments(list);
          setError(null);
        }
      })
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [course?.id]);

  // Grouped by lecture, newest lecture first (the API already sorts).
  const groups = useMemo(() => {
    const map = new Map<string, FlaggedMoment[]>();
    for (const m of moments ?? []) map.set(m.source_id, [...(map.get(m.source_id) ?? []), m]);
    return [...map.values()];
  }, [moments]);

  return (
    <section>
      <PageTitle
        subtitle={
          course
            ? `What instructors marked as important in ${course.code} lectures.`
            : "What instructors marked as important. Choose a course to narrow this down."
        }
      >
        Flagged
      </PageTitle>
      {error ? <ErrorNote>{error}</ErrorNote> : null}
      {!moments && !error ? <LoadingDots label="Loading flagged moments" /> : null}
      {moments && moments.length === 0 ? (
        <EmptyNote>No flagged moments yet. They appear when a lecture mentions exams, quizzes or things to note down.</EmptyNote>
      ) : null}
      <div className="flex flex-col gap-6">
        {groups.map((group) => {
          const first = group[0];
          return (
            <section key={first.source_id} aria-label={first.title}>
              <h2 className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[15px]">
                <span className="font-semibold text-text">{first.title}</span>
                {first.instructor ? (
                  <span className="flex items-center gap-1.5 text-text-2">
                    {first.instructor.name} <RoleBadge role={first.instructor.role} />
                  </span>
                ) : null}
                {first.section ? <span className="text-text-2">{first.section}</span> : null}
                {first.source_date ? <span className="text-text-2">{formatDate(first.source_date)}</span> : null}
              </h2>
              <FlaggedList
                moments={group}
                onOpen={(m) => router.push(`/lectures/${m.source_id}?t=${Math.floor(m.start_s)}`)}
              />
            </section>
          );
        })}
      </div>
    </section>
  );
}
