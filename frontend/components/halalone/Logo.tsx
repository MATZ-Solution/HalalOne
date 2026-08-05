import { type CSSProperties } from "react"

export type LogoProps = {
  size?: number
  onDark?: boolean
  style?: CSSProperties
}

export default function Logo({ size = 28, onDark = false, style }: LogoProps) {
  const green = onDark ? "var(--white)" : "var(--green-800)"
  const gold = "var(--gold-500)"
  const mark = Math.round(size * 1.05)
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: size * 0.32, ...style }}>
      <svg width={mark} height={mark} viewBox="-16 -16 32 32" aria-hidden="true" style={{ flex: "0 0 auto" }}>
        <path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke={gold} strokeWidth="2.6" strokeLinejoin="round" />
        <path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke={green} strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 800,
          fontSize: size,
          letterSpacing: "-0.03em",
          lineHeight: 1,
          whiteSpace: "nowrap",
        }}
      >
        <span style={{ color: green }}>Halal</span>
        <span style={{ color: gold }}>One</span>
      </span>
    </span>
  )
}
