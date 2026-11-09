"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense } from "react";

import { CourseSelector } from "@/components/CourseSelector";

const LINKS = [
  { href: "/", label: "Ask" },
  { href: "/lectures", label: "Lectures" },
  { href: "/flagged", label: "Flagged" },
  { href: "/practice", label: "Practice" },
  { href: "/sources", label: "Sources" },
] as const;

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function GlassNav() {
  return (
    <Suspense fallback={<NavBar pathname={null} />}>
      <ActiveNav />
    </Suspense>
  );
}

function ActiveNav() {
  return <NavBar pathname={usePathname()} />;
}

function NavBar({ pathname }: { pathname: string | null }) {
  return (
    <header className="sticky top-0 z-40 px-2 pt-2 md:px-4 md:pt-3">
      <nav aria-label="Main" className="glass mx-auto flex max-w-[1040px] flex-wrap items-center gap-x-2 px-3 py-1.5 md:gap-6 md:px-5">
        <Link
          href="/"
          className="hidden shrink-0 text-[15px] font-semibold tracking-tight text-text min-[400px]:block md:text-[17px]"
        >
          CampusMind
        </Link>
        <ul className="flex min-w-0 items-center gap-0.5 overflow-x-auto [scrollbar-width:none] md:gap-1">
          {LINKS.map((link) => {
            const active = pathname !== null && isActive(pathname, link.href);
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  aria-current={active ? "page" : undefined}
                  className={clsx(
                    "flex h-11 items-center rounded-chip px-2 text-[15px] transition-colors duration-200 ease-standard md:px-3",
                    active ? "bg-accent-soft font-semibold text-accent" : "text-text-2 hover:text-text",
                  )}
                >
                  {link.label}
                </Link>
              </li>
            );
          })}
        </ul>
        <div className="ml-auto max-sm:w-full max-sm:border-t max-sm:border-border/60 max-sm:pt-1 max-sm:[&>div]:ml-auto max-sm:flex">
          <CourseSelector />
        </div>
      </nav>
    </header>
  );
}
