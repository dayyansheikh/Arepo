import type { Metadata } from "next";
import { Suspense } from "react";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { displayFont } from "./fonts";
import "./globals.css";
import { ModeProvider } from "@/lib/mode-context";
import { AuthProvider } from "@/lib/auth-context";
import { TopBar } from "@/components/TopBar";
import { DegradationBanner } from "@/components/DegradationBanner";
import { Footer } from "@/components/Footer";

export const metadata: Metadata = {
  // The browser tab title is exactly "Arepo" on every route (spec §9). `absolute` overrides any
  // per-page title so no route can set its own.
  title: {
    absolute: "Arepo",
    default: "Arepo",
    template: "Arepo",
  },
  description:
    "Arepo reads public prediction markets for the hidden signal between the lines: order-book state, price motion and anomaly signals over public Polymarket data. A read-only research instrument, not trading advice.",
  applicationName: "Arepo",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en-GB"
      className={`${GeistSans.variable} ${GeistMono.variable} ${displayFont.variable}`}
    >
      {/* The shell fills the viewport background (min-h-screen) but does NOT stretch the main
          region: the footer follows the content directly, so a short page (e.g. a not-found card)
          ends cleanly with the footer just below it rather than a large blank gap, while a long
          page scrolls normally (spec §4.6, §5). */}
      <body className="font-sans min-h-screen flex flex-col">
        <Suspense fallback={null}>
          <ModeProvider>
            <AuthProvider>
              <DegradationBanner />
              <TopBar />
              <main className="mx-auto w-full max-w-shell px-5 py-8 sm:px-8 lg:px-12">
                {children}
              </main>
              <Footer />
            </AuthProvider>
          </ModeProvider>
        </Suspense>
      </body>
    </html>
  );
}
