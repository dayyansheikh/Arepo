import Link from "next/link";

const TABS = [
  { href: "/lab", label: "Research", key: "research" },
  { href: "/lab/claude", label: "Claude", key: "claude" },
  { href: "/lab/members", label: "Members", key: "members" },
] as const;

/** Quiet tab switcher shown at the top of the owner-only Lab pages (never in public nav). */
export function LabTabs({ current }: { current: (typeof TABS)[number]["key"] }) {
  return (
    <nav aria-label="Lab sections" className="flex">
      <ul className="inline-flex gap-1 rounded-full border border-arepo-border bg-arepo-surface p-1">
        {TABS.map((t) => {
          const active = t.key === current;
          return (
            <li key={t.key}>
              <Link
                href={t.href}
                aria-current={active ? "page" : undefined}
                className={`focus-ring inline-flex rounded-full px-3.5 py-1.5 text-[13px] font-medium transition-colors ${
                  active ? "bg-arepo-ink text-white" : "text-arepo-ink2 hover:bg-arepo-surface2 hover:text-arepo-ink"
                }`}
              >
                {t.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
