import { type CSSProperties } from "react"

export type LogoProps = {
  size?: number
  onDark?: boolean
  style?: CSSProperties
}

export default function Logo({ size = 28, onDark = false, style }: LogoProps) {
  const green = onDark ? "var(--white)" : "var(--green-800)"
  const gold = "var(--gold-500)"
  return (
    <span style={{ display: "inline-flex", alignItems: "center", ...style }}>
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
