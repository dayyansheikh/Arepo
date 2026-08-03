import type { Metadata } from "next";
import { Suspense } from "react";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { displayFont } from "./fonts";
import "./globals.css";
import { ModeProvider } from "@/lib/mode-context";
import { TopBar } from "@/components/TopBar";
import { DegradationBanner } from "@/components/DegradationBanner";
import { Footer } from "@/components/Footer";

export const metadata: Metadata = {
  title: {
    default: "Arepo: the hidden signal between the lines",
    template: "%s · Arepo",
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
      <body className="font-sans min-h-screen flex flex-col">
        <Suspense fallback={null}>
          <ModeProvider>
            <DegradationBanner />
            <TopBar />
            <main className="flex-1 mx-auto w-full max-w-shell px-5 py-8 sm:px-8 lg:px-12">
              {children}
            </main>
            <Footer />
          </ModeProvider>
        </Suspense>
      </body>
    </html>
  );
}
