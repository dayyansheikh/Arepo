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

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

/** The primary nav links. Rendered inline on desktop and as a wrapping row on
 * mobile, so the bar never needs horizontal scrolling. */
function NavLinks({ pathname }: { pathname: string }) {
  return (
    <>
      {NAV_LINKS.map((link) => {
        const active = isActive(pathname, link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            className={`focus-ring relative whitespace-nowrap rounded-md px-3 py-2 text-[15px] font-medium transition-colors ${
              active
                ? "text-arepo-ink after:absolute after:inset-x-3 after:-bottom-[11px] after:h-0.5 after:rounded-full after:bg-arepo-accent"
                : "text-arepo-muted hover:bg-arepo-surface2 hover:text-arepo-ink"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </>
  );
}

export function TopBar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-arepo-border bg-arepo-surface/95 backdrop-blur">
      <div className="mx-auto max-w-shell px-5 sm:px-8 lg:px-12">
        <div className="flex items-center justify-between gap-4 py-3.5">
          <Link href="/" className="focus-ring shrink-0 rounded-md" aria-label="Arepo home">
            <Logo size={34} />
          </Link>
          {/* Desktop: spread across the available width, no scrolling. */}
          <nav
            aria-label="Primary"
            className="hidden flex-1 items-center justify-center gap-1 lg:gap-2 md:flex"
          >
            <NavLinks pathname={pathname} />
          </nav>
          <div className="flex shrink-0 items-center gap-3">
            <StatusChip />
            <ModeSwitcher />
          </div>
        </div>
        {/* Mobile: links wrap onto their own row rather than scrolling. */}
        <nav
          aria-label="Primary"
          className="-mx-1 flex flex-wrap items-center gap-0.5 px-1 pb-2 md:hidden"
        >
          <NavLinks pathname={pathname} />
        </nav>
      </div>
    </header>
  );
}
