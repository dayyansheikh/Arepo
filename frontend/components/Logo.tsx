/**
 * Arepo convergence mark. Four chevrons at N/E/S/W point inward toward a central
 * red node without touching it: the four things Arepo unites (information,
 * conviction, action, markets), the gap "between the lines", and the hidden
 * signal they reveal. See docs/brand-system.md. Legible down to 16px.
 *
 * Chevrons use `currentColor` (ink by default); the node is always Arepo red.
 */
export function LogoMark({
  size = 28,
  title,
}: {
  size?: number;
  title?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      {title ? <title>{title}</title> : null}
      <g
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      >
        {/* top chevron, apex pointing down toward centre */}
        <path d="M10.5 7 L16 12 L21.5 7" />
        {/* bottom chevron, apex pointing up */}
        <path d="M10.5 25 L16 20 L21.5 25" />
        {/* left chevron, apex pointing right */}
        <path d="M7 10.5 L12 16 L7 21.5" />
        {/* right chevron, apex pointing left */}
        <path d="M25 10.5 L20 16 L25 21.5" />
      </g>
      {/* the hidden central signal */}
      <circle cx="16" cy="16" r="2.7" fill="#E50C0E" />
    </svg>
  );
}

export function Logo({ size = 26 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2 select-none text-arepo-ink">
      <LogoMark size={size} title="Arepo" />
      <span className="font-semibold text-lg tracking-[-0.01em]">Arepo</span>
    </span>
  );
}
