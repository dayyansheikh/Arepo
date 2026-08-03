"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "./Logo";
import { ModeSwitcher } from "./ModeSwitcher";
import { StatusChip } from "./StatusChip";

const NAV_LINKS = [
  { href: "/", label: "Overview" },
  { href: "/markets", label: "Markets" },
  { href: "/signals", label: "Signal Lab" },
  { href: "/replay", label: "Replay" },
  { href: "/how-it-works", label: "How It Works" },
  { href: "/methodology", label: "Methodology" },
];

export function TopBar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-arepo-border bg-arepo-surface/90 backdrop-blur">
      <div className="mx-auto flex max-w-shell flex-wrap items-center gap-x-6 gap-y-3 px-5 py-3 sm:px-8 lg:px-12">
        <Link href="/" className="focus-ring rounded-md" aria-label="Arepo home">
          <Logo />
        </Link>
        <nav
          aria-label="Primary"
          className="-mx-1 flex flex-1 items-center gap-0.5 overflow-x-auto px-1"
        >
          {NAV_LINKS.map((link) => {
            const active =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`focus-ring whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? "text-arepo-accent"
                    : "text-arepo-muted hover:text-arepo-ink"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-3">
          <StatusChip />
          <ModeSwitcher />
        </div>
      </div>
    </header>
  );
}
