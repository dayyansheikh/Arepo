/**
 * Arepo grid mark — a faithful reconstruction of the supplied brand logo
 * (`design-assets/brand/AREPO logo (no word).png`): a 5x5 grid of cells where the
 * second column and the second row are filled Arepo red, forming the brand's
 * offset cross; the remaining cells are outlined. The supplied artwork is set on
 * black with white outlines; because Arepo's identity is light-only, empty cells
 * are drawn with an ink hairline outline on a transparent ground and the red
 * cells are preserved exactly. The arrangement and the red glyph are unchanged.
 * See docs/brand-system.md.
 */
const RED = "#E50C0E";
const CELLS = 5;
const PITCH = 6; // cell (5) + gap (1)
const SIZE_UNITS = CELLS * PITCH - 1; // 29

function isRed(row: number, col: number): boolean {
  // Second column (index 1) top-to-bottom, and second row (index 1) left-to-right.
  return col === 1 || row === 1;
}

export function LogoMark({ size = 26, title }: { size?: number; title?: string }) {
  const cells: React.ReactNode[] = [];
  for (let row = 0; row < CELLS; row++) {
    for (let col = 0; col < CELLS; col++) {
      const red = isRed(row, col);
      cells.push(
        <rect
          key={`${row}-${col}`}
          x={col * PITCH + 0.5}
          y={row * PITCH + 0.5}
          width={4}
          height={4}
          rx={0.6}
          fill={red ? RED : "none"}
          stroke={red ? "none" : "currentColor"}
          strokeWidth={red ? 0 : 1}
        />
      );
    }
  }
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${SIZE_UNITS} ${SIZE_UNITS}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
      className="text-arepo-borderStrong"
    >
      {title ? <title>{title}</title> : null}
      {cells}
    </svg>
  );
}

/**
 * Full lockup: grid mark + the AREPO wordmark set in the geometric display face
 * (Jost), uppercase with wide tracking to echo the supplied wordmark asset.
 */
export function Logo({ size = 26 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2.5 select-none text-arepo-ink">
      <LogoMark size={size} title="Arepo" />
      <span className="font-display text-[19px] font-semibold uppercase tracking-[0.22em] text-arepo-ink">
        Arepo
      </span>
    </span>
  );
}
