"use client"

import Link from "next/link"
import { type CSSProperties, type ReactNode, type MouseEvent } from "react"

type Variant = "primary" | "gold" | "secondary" | "ghost" | "danger"
type Size = "sm" | "md" | "lg"

const sizes: Record<Size, { padding: string; fontSize: number; height: number; gap: number }> = {
  sm: { padding: "8px 16px", fontSize: 13, height: 36, gap: 6 },
  md: { padding: "11px 22px", fontSize: 15, height: 44, gap: 8 },
  lg: { padding: "14px 28px", fontSize: 17, height: 52, gap: 10 },
}

const variants: Record<Variant, CSSProperties> = {
  primary: { background: "var(--green-800)", color: "var(--cream-50)" },
  gold: { background: "var(--gold-500)", color: "var(--green-900)" },
  secondary: { background: "transparent", color: "var(--green-800)", borderColor: "var(--green-800)" },
  ghost: { background: "transparent", color: "var(--green-800)" },
  danger: { background: "var(--status-danger)", color: "#fff" },
}

const hovers: Record<Variant, string> = {
  primary: "var(--green-900)",
  gold: "var(--gold-600)",
  secondary: "color-mix(in srgb, var(--green-800) 8%, transparent)",
  ghost: "color-mix(in srgb, var(--green-800) 8%, transparent)",
  danger: "color-mix(in srgb, var(--status-danger) 82%, #000)",
}

export type ButtonProps = {
  children: ReactNode
  variant?: Variant
  size?: Size
  pill?: boolean
  block?: boolean
  href?: string
  onClick?: () => void
  style?: CSSProperties
  ariaLabel?: string
}

export default function Button({
  children,
  variant = "primary",
  size = "md",
  pill = true,
  block = false,
  href,
  onClick,
  style,
  ariaLabel,
}: ButtonProps) {
  const s = sizes[size] || sizes.md
  const v = variants[variant]
  const merged: CSSProperties = {
    display: block ? "flex" : "inline-flex",
    width: block ? "100%" : undefined,
    alignItems: "center",
    justifyContent: "center",
    gap: s.gap,
    fontFamily: "var(--font-sans)",
    fontWeight: 700,
    fontSize: s.fontSize,
    lineHeight: 1,
    padding: s.padding,
    minHeight: s.height,
    borderRadius: pill ? "var(--radius-pill)" : "var(--radius-sm)",
    border: "1px solid transparent",
    cursor: "pointer",
    letterSpacing: "-0.01em",
    transition:
      "background var(--dur-fast) var(--ease-standard), color var(--dur-fast) var(--ease-standard), transform var(--dur-fast) var(--ease-standard), box-shadow var(--dur-fast) var(--ease-standard)",
    WebkitTapHighlightColor: "transparent",
    ...v,
    ...style,
  }

  const baseBg = (style?.background as string) ?? (v.background as string)
  const onEnter = (e: MouseEvent<HTMLElement>) => {
    e.currentTarget.style.background = hovers[variant]
    if (variant === "primary" || variant === "gold" || variant === "danger") e.currentTarget.style.transform = "translateY(-1px)"
  }
  const onLeave = (e: MouseEvent<HTMLElement>) => {
    e.currentTarget.style.background = baseBg
    e.currentTarget.style.transform = "translateY(0)"
  }

  if (href) {
    return (
      <Link href={href} style={merged} aria-label={ariaLabel} onMouseEnter={onEnter} onMouseLeave={onLeave}>
        {children}
      </Link>
    )
  }
  return (
    <button type="button" style={merged} aria-label={ariaLabel} onClick={onClick} onMouseEnter={onEnter} onMouseLeave={onLeave}>
      {children}
    </button>
  )
}
