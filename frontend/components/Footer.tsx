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
            <LogoMark size={22} />
            <span className="font-display text-[15px] font-semibold uppercase tracking-[0.16em]">
              Arepo
            </span>
          </span>
          <Link href="/how-it-works" className="hover:text-arepo-ink">
            How Arepo works
          </Link>
          <Link href="/methodology" className="hover:text-arepo-ink">
            Methodology
          </Link>
        </div>
        <p className="max-w-reading leading-relaxed">{data?.disclaimer ?? FALLBACK_DISCLAIMER}</p>

        <div className="flex flex-col gap-1 border-t border-arepo-border pt-4 text-[11px] sm:flex-row sm:items-center sm:justify-between">
          <span>Arepo · read-only research over public Polymarket data</span>
          <span className="sm:text-right">
            Designed and created by{" "}
            <span className="font-medium text-arepo-ink2">Dayyan Sheikh</span>{" "}
            ·{" "}
            <a
              href="mailto:dayyansheikh.work@gmail.com"
              className="hover:text-arepo-ink"
            >
              dayyansheikh.work@gmail.com
            </a>
          </span>
        </div>
      </div>
    </footer>
  );
}
