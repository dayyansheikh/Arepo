import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Suspense } from "react";
import "./globals.css";
import { ModeProvider } from "@/lib/mode-context";
import { TopBar } from "@/components/TopBar";
import { DegradationBanner } from "@/components/DegradationBanner";
import { Footer } from "@/components/Footer";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "Astrolabe — Prediction Market Intelligence",
  description:
    "An instrument for reading prediction markets: order book state, price motion, and anomaly signals over public Polymarket data.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body className="font-sans min-h-screen flex flex-col">
        <Suspense fallback={null}>
          <ModeProvider>
            <DegradationBanner />
            <TopBar />
            <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-6 sm:px-6">
              {children}
            </main>
            <Footer />
          </ModeProvider>
        </Suspense>
      </body>
    </html>
  );
}
