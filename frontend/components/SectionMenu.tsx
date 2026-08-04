"use client";

import { useEffect, useState } from "react";

export interface MenuGroup {
  group?: string;
  items: { id: string; label: string }[];
}

/**
 * Sticky, independently-scrollable section menu with active-section highlighting (spec §11).
 *
 * - Sticky on desktop; if the list is taller than the viewport it scrolls on its own
 *   (`overflow-y-auto` + `overscroll-contain`), so scrolling over the menu scrolls the menu and
 *   scrolling over the content scrolls the page.
 * - The current section is tracked with an IntersectionObserver and highlighted (darker text +
 *   an accent bar). Links are real anchors, so they are keyboard-accessible and deep-linkable.
 * - On mobile it collapses into a native <details> disclosure.
 */
export function SectionMenu({ label, groups }: { label: string; groups: MenuGroup[] }) {
  const ids = groups.flatMap((g) => g.items.map((i) => i.id));
  const [active, setActive] = useState<string | null>(ids[0] ?? null);

  useEffect(() => {
    const els = ids
      .map((id) => document.getElementById(id))
      .filter((e): e is HTMLElement => e !== null);
    if (els.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-96px 0px -60% 0px", threshold: 0 }
    );
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
    // ids is derived from the static `groups` prop; recomputing each render is fine.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groups]);

  const linkClass = (id: string) =>
    `focus-ring block rounded px-2 py-1 text-[13px] transition-colors ${
      active === id
        ? "bg-arepo-accentTint font-medium text-arepo-accentActive"
        : "text-arepo-ink2 hover:bg-arepo-surface2 hover:text-arepo-ink"
    }`;

  const list = (
    <>
      {groups.map((g, gi) => (
        <div key={g.group ?? `g${gi}`} className="flex flex-col gap-0.5">
          {g.group && <span className="section-label mb-1 text-[11px]">{g.group}</span>}
          {g.items.map((it) => (
            <a key={it.id} href={`#${it.id}`} className={linkClass(it.id)}>
              {it.label}
            </a>
          ))}
        </div>
      ))}
    </>
  );

  return (
    <>
      {/* Desktop: sticky, independently scrollable. */}
      <nav
        aria-label={label}
        className="no-scrollbar sticky top-24 hidden h-fit max-h-[calc(100vh-7rem)] w-52 shrink-0 flex-col gap-4 self-start overflow-y-auto overscroll-contain pr-1 lg:flex"
      >
        {list}
      </nav>
      {/* Mobile: collapsible. */}
      <details className="mb-4 rounded-card border border-arepo-border bg-arepo-surface2 p-3 lg:hidden">
        <summary className="cursor-pointer text-[13px] font-medium text-arepo-ink">
          Jump to section
        </summary>
        <div className="mt-3 flex flex-col gap-3">{list}</div>
      </details>
    </>
  );
}
