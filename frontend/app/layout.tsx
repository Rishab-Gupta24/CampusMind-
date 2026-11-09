import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import { GlassNav } from "@/components/GlassNav";
import { ReminderService } from "@/components/ReminderService";
import { ServiceWorker } from "@/components/ServiceWorker";
import { PrefsProvider } from "@/lib/prefs";

import "katex/dist/katex.min.css";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"], weight: ["400", "600"] });

export const metadata: Metadata = {
  title: "CampusMind",
  description: "Answers from your campus documents and lectures, with sources.",
  applicationName: "CampusMind",
  appleWebApp: { capable: true, title: "CampusMind", statusBarStyle: "default" },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F5F5F7" },
    { media: "(prefers-color-scheme: dark)", color: "#000000" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-dvh">
        <PrefsProvider>
          <GlassNav />
          <ReminderService />
          <ServiceWorker />
          <main className="mx-auto w-full max-w-[760px] px-4 pt-6 pb-12 md:px-8">{children}</main>
        </PrefsProvider>
      </body>
    </html>
  );
}
