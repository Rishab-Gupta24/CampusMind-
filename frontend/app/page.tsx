"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AskThread } from "@/components/AskThread";
import { usePrefs } from "@/lib/prefs";

const EXAMPLES = [
  "What is the weightage of the comprehensive exam?",
  "Can I get a makeup if I miss an evaluation?",
  "What did the IC say about Bayes' theorem?",
];

export default function AskPage() {
  return (
    <Suspense fallback={null}>
      <Ask />
    </Suspense>
  );
}

function Ask() {
  const { course, section } = usePrefs();
  const initial = useSearchParams().get("q") ?? undefined;
  return (
    <AskThread
      courseId={course?.id ?? null}
      sectionId={section?.id ?? null}
      title="Ask anything about your courses or campus rules."
      examples={EXAMPLES}
      initialQuestion={initial}
    />
  );
}
