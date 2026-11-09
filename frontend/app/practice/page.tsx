"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { FlashcardsPanel } from "@/components/Flashcards";
import { PageTitle } from "@/components/PageTitle";
import { QuizPanel } from "@/components/Quiz";
import { LoadingDots, Tabs } from "@/components/ui";
import { usePrefs } from "@/lib/prefs";

type Tab = "quiz" | "flashcards";

export default function PracticePage() {
  return (
    <Suspense fallback={<LoadingDots label="Loading" />}>
      <Practice />
    </Suspense>
  );
}

function Practice() {
  const params = useSearchParams();
  const { course, section } = usePrefs();
  const [tab, setTab] = useState<Tab>(params.get("tab") === "flashcards" ? "flashcards" : "quiz");
  const topic = params.get("topic") ?? "";
  const lectureId = params.get("lecture");

  return (
    <section>
      <PageTitle
        subtitle={
          lectureId
            ? "Practice from one lecture."
            : course
              ? `Questions and flashcards from ${course.code} sources, including past papers.`
              : "Questions and flashcards from your campus sources. Choose a course to focus them."
        }
      >
        Practice
      </PageTitle>
      <Tabs
        label="Practice modes"
        value={tab}
        onChange={setTab}
        tabs={[
          { value: "quiz", label: "Quiz" },
          { value: "flashcards", label: "Flashcards" },
        ]}
      />
      <div className="mt-5">
        {tab === "quiz" ? (
          <QuizPanel
            initialTopic={topic}
            courseId={course?.id ?? null}
            sectionId={section?.id ?? null}
            lectureId={lectureId}
          />
        ) : (
          <FlashcardsPanel
            initialTopic={topic}
            courseId={course?.id ?? null}
            sectionId={section?.id ?? null}
            lectureId={lectureId}
          />
        )}
      </div>
    </section>
  );
}
