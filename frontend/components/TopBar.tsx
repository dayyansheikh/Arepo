"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { initialsForUser } from "@/lib/account";
import { Logo } from "./Logo";
import { StatusChip } from "./StatusChip";

/** Right-hand auth affordance: initials when signed in, Sign in otherwise. */
function AuthLink({ pathname }: { pathname: string }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  const href = user ? "/account" : "/signin";
  const label = user ? initialsForUser(user) : "Sign in";
  const active = pathname.startsWith(href);
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      aria-label={user ? "Your account" : undefined}
      title={user ? "Your account" : undefined}
      className={`focus-ring inline-flex items-center justify-center whitespace-nowrap border text-[13px] font-semibold transition-colors ${
        user ? "h-9 w-9 rounded-full p-0" : "rounded-md px-3 py-1.5"
      } ${
        active
          ? "border-arepo-accent text-arepo-accentActive"
          : "border-arepo-border text-arepo-ink hover:bg-arepo-surface2"
      }`}
    >
      {label}
    </Link>
  );
}

const NAV_LINKS = [
  { href: "/", label: "Opportunities" },
  { href: "/markets", label: "Explore" },
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
      {/* The header spans a wide fluid width (not the narrower page shell) so the logo anchors the
          left edge, the account/mode controls the right edge, and the nav uses the centre space,
          instead of the whole bar bunching in the middle with empty sides when the viewport is
          wide or zoomed out (spec §8). Sensible gutters via the horizontal padding. */}
      <div className="mx-auto w-full max-w-[1920px] px-5 sm:px-8 lg:px-12">
        {/* flex-wrap so that on a very narrow viewport (e.g. 320px) the right-hand controls drop to
            their own line and then wrap internally, instead of the fixed-width mode switcher + auth
            link forcing the header — and therefore the whole document — wider than the viewport
            (final runtime acceptance §3). The controls no longer carry shrink-0 for the same reason. */}
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 py-3.5">
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
          <div className="flex min-w-0 flex-wrap items-center justify-end gap-x-3 gap-y-2">
            <StatusChip />
            <AuthLink pathname={pathname} />
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
