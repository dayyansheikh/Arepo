export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 28 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <circle cx="14" cy="14" r="12.5" stroke="#E7B24C" strokeWidth="1" />
      <circle cx="14" cy="14" r="8.5" stroke="#E7B24C" strokeWidth="1" opacity="0.7" />
      <circle cx="14" cy="14" r="1.6" fill="#E7B24C" />
      <line x1="14" y1="1.5" x2="14" y2="4.5" stroke="#E7B24C" strokeWidth="1" />
      <line x1="14" y1="23.5" x2="14" y2="26.5" stroke="#E7B24C" strokeWidth="1" />
      <line x1="1.5" y1="14" x2="4.5" y2="14" stroke="#E7B24C" strokeWidth="1" />
      <line x1="23.5" y1="14" x2="26.5" y2="14" stroke="#E7B24C" strokeWidth="1" />
      <line x1="14" y1="14" x2="20" y2="8.5" stroke="#E7B24C" strokeWidth="1.1" strokeLinecap="round" />
    </svg>
  );
}

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2 select-none">
      <LogoMark size={size} />
      <span className="font-semibold tracking-wide text-lg">
        Astrolabe
      </span>
    </span>
  );
}
