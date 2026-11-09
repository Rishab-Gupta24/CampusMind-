import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { GlassNav } from "@/components/GlassNav";
import { PrefsProvider } from "@/lib/prefs";

import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"], weight: ["400", "600"] });

export const metadata: Metadata = {
  title: "CampusMind",
  description: "Answers from your campus documents and lectures, with sources.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-dvh">
        <PrefsProvider>
          <GlassNav />
          <main className="mx-auto w-full max-w-[760px] px-4 pt-6 pb-12 md:px-8">{children}</main>
        </PrefsProvider>
      </body>
    </html>
  );
}
