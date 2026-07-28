"use client"

import { type CSSProperties, type ReactNode, type MouseEvent } from "react"

export type CardProps = {
  children: ReactNode
  surface?: "white" | "cream" | "green"
  interactive?: boolean
  padded?: boolean
  style?: CSSProperties
}

export default function Card({ children, surface = "white", interactive = false, padded = true, style }: CardProps) {
  const onGreen = surface === "green"
  const bg = surface === "cream" ? "var(--surface-cream)" : onGreen ? "var(--green-800)" : "var(--white)"

  const onEnter = (e: MouseEvent<HTMLDivElement>) => {
    if (!interactive) return
    e.currentTarget.style.transform = "translateY(-2px)"
    e.currentTarget.style.boxShadow = "var(--shadow-md)"
  }
  const onLeave = (e: MouseEvent<HTMLDivElement>) => {
    if (!interactive) return
    e.currentTarget.style.transform = "translateY(0)"
    e.currentTarget.style.boxShadow = "var(--shadow-sm)"
  }

  return (
    <div
      className={onGreen ? "hl-on-dark" : undefined}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      style={{
        background: bg,
        border: `1px solid ${onGreen ? "var(--border-on-dark)" : "var(--border-subtle)"}`,
        borderRadius: "var(--radius-lg)",
        padding: padded ? "var(--space-6)" : 0,
        boxShadow: "var(--shadow-sm)",
        color: onGreen ? "var(--cream-50)" : "var(--text-body)",
        cursor: interactive ? "pointer" : "default",
        transition: "transform var(--dur-base) var(--ease-out), box-shadow var(--dur-base) var(--ease-out)",
        ...style,
      }}
    >
      {children}
    </div>
  )
}
