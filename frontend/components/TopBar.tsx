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
  { href: "/methodology", label: "Methodology" },
];

export function TopBar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-astro-light-border dark:border-astro-border bg-astro-light-bg/90 dark:bg-astro-bg/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3 sm:px-6">
        <Link href="/" className="focus-ring rounded-instrument">
          <Logo />
        </Link>
        <nav aria-label="Primary" className="flex flex-1 flex-wrap items-center gap-1">
          {NAV_LINKS.map((link) => {
            const active =
              link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`focus-ring rounded-instrument px-3 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-astro-light-panel dark:bg-astro-panel text-astro-brass"
                    : "text-muted-fg hover:text-astro-light-text dark:hover:text-astro-text"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-3">
          <ModeSwitcher />
          <StatusChip />
        </div>
      </div>
    </header>
  );
}
