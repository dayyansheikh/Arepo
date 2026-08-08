import type { Metadata } from "next";
import { Suspense } from "react";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { displayFont } from "./fonts";
import "./globals.css";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";
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
      {/* Sticky-footer shell (final-completion prompt D2): the body is a full-viewport flex column
          (100dvh), the main region is flex-1, and the footer follows main. On a short page (sign in,
          sign up, reset, not-found) main grows to fill and the footer sits at the very bottom; on a
          long page main grows with the content and the footer follows it. Verified on sign-in,
          sign-up and reset at desktop, mobile and zoom. */}
      <body className="font-sans min-h-[100dvh] flex flex-col">
        <Suspense fallback={null}>
          <ModeProvider>
            <AuthProvider>
              <DegradationBanner />
              <TopBar />
              <main className="mx-auto w-full max-w-shell flex-1 px-5 py-8 sm:px-8 lg:px-12">
                {children}
              </main>
              <Footer />
            </AuthProvider>
          </ModeProvider>
        </Suspense>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
