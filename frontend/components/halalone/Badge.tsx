import { type CSSProperties, type ReactNode } from "react"
import Icon from "./Icon"

type Variant = "verified" | "neutral" | "gold" | "solid" | "warning" | "danger"

const variants: Record<Variant, { background: string; color: string; icon?: string }> = {
  verified: { background: "color-mix(in srgb, var(--green-700) 14%, transparent)", color: "var(--green-800)", icon: "shield-check" },
  neutral: { background: "var(--cream-100)", color: "var(--charcoal-600)" },
  gold: { background: "var(--gold-200)", color: "var(--gold-600)" },
  solid: { background: "var(--green-800)", color: "var(--cream-50)" },
  warning: { background: "color-mix(in srgb, var(--status-warning) 22%, transparent)", color: "var(--gold-600)", icon: "alert-triangle" },
  danger: { background: "color-mix(in srgb, var(--status-danger) 14%, transparent)", color: "var(--status-danger)", icon: "x-circle" },
}

export type BadgeProps = {
  children: ReactNode
  variant?: Variant
  icon?: string
  size?: "sm" | "md"
  style?: CSSProperties
}

export default function Badge({ children, variant = "verified", icon, size = "md", style }: BadgeProps) {
  const v = variants[variant] || variants.neutral
  const glyph = icon || v.icon
  const pad = size === "sm" ? "3px 9px" : "5px 12px"
  const fs = size === "sm" ? 11 : 12.5
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: pad,
        borderRadius: "var(--radius-pill)",
        fontSize: fs,
        fontWeight: 700,
        letterSpacing: "-0.005em",
        fontFamily: "var(--font-sans)",
        background: v.background,
        color: v.color,
        ...style,
      }}
    >
      {glyph && <Icon name={glyph} size={size === "sm" ? 12 : 13} color={v.color} />}
      {children}
    </span>
  )
}
