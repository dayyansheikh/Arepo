import styles from "./unlock.module.css";

export type PadlockState = "locked" | "open";

/**
 * Small padlock in the warm-neutral palette with the red accent on the keyhole. When `state` is
 * "open" the shackle lifts and swings (CSS, ~600 ms, off under prefers-reduced-motion) and the
 * keyhole turns green. `shake` replays a short shake for a failed attempt.
 */
export function Padlock({ state, shakeKey = 0, size = 72 }: { state: PadlockState; shakeKey?: number; size?: number }) {
  const open = state === "open";
  return (
    <span
      key={shakeKey}
      className={`inline-flex ${shakeKey ? styles.shake : ""} ${open ? styles.open : ""}`}
      aria-hidden="true"
    >
      <svg width={size} height={(size * 56) / 48} viewBox="0 0 48 56" fill="none">
        <path
          className={styles.shackle}
          d="M15 25V17.5a9 9 0 0 1 18 0V25"
          stroke="#3A3A38"
          strokeWidth="3.5"
          strokeLinecap="round"
        />
        <rect x="7" y="24" width="34" height="27" rx="7" fill="#F4F2EF" stroke="#101010" strokeWidth="2" />
        <g className={styles.keyhole} style={{ fill: open ? "#1C7C54" : "#E50C0E" }}>
          <circle cx="24" cy="35.5" r="3.4" />
          <rect x="22.6" y="37" width="2.8" height="7" rx="1.4" />
        </g>
      </svg>
    </span>
  );
}
