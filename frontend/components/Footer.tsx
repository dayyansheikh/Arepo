"use client";

import Link from "next/link";
import { useAsync } from "@/lib/use-async";
import { getMeta } from "@/lib/api";
import { LogoMark } from "./Logo";

const FALLBACK_DISCLAIMER =
  "Arepo is a read-only research instrument over public Polymarket data. It does not place trades, offer financial advice, or prove insider activity. It surfaces statistically unusual behaviour for further reading.";

export function Footer() {
  const { data } = useAsync(() => getMeta(), []);

  return (
    <footer className="mt-16 border-t border-arepo-border">
      <div className="mx-auto max-w-shell space-y-3 px-5 py-8 text-xs text-arepo-muted sm:px-8 lg:px-12">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <span className="inline-flex items-center gap-2 text-arepo-ink">
            <LogoMark size={18} />
            <span className="text-sm font-semibold tracking-[-0.01em]">Arepo</span>
          </span>
          <Link href="/how-it-works" className="hover:text-arepo-ink">
            How Arepo works
          </Link>
          <Link href="/methodology" className="hover:text-arepo-ink">
            Methodology
          </Link>
        </div>
        <p className="max-w-reading leading-relaxed">{data?.disclaimer ?? FALLBACK_DISCLAIMER}</p>
      </div>
    </footer>
  );
}
