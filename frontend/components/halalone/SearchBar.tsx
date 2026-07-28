"use client"

import { type CSSProperties, type KeyboardEvent } from "react"
import Icon from "./Icon"

export type SearchBarProps = {
  placeholder?: string
  size?: "sm" | "md" | "lg"
  onDark?: boolean
  onSubmit?: (value: string) => void
  style?: CSSProperties
}

export default function SearchBar({
  placeholder = "Search anything halal",
  size = "md",
  onDark = false,
  onSubmit,
  style,
}: SearchBarProps) {
  const h = size === "lg" ? 56 : size === "sm" ? 42 : 50
  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") onSubmit?.(e.currentTarget.value)
  }
  return (
    <span
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        width: "100%",
        height: h,
        padding: "0 18px",
        borderRadius: "var(--radius-pill)",
        background: onDark ? "color-mix(in srgb, var(--white) 12%, transparent)" : "var(--white)",
        border: onDark ? "1px solid var(--border-on-dark)" : "1px solid var(--border-subtle)",
        boxShadow: onDark ? "none" : "var(--shadow-sm)",
        fontFamily: "var(--font-sans)",
        ...style,
      }}
    >
      <Icon name="search" size={size === "lg" ? 22 : 20} color={onDark ? "var(--cream-50)" : "var(--charcoal-600)"} />
      <input
        placeholder={placeholder}
        onKeyDown={onKeyDown}
        style={{
          flex: 1,
          border: "none",
          outline: "none",
          background: "transparent",
          fontFamily: "var(--font-sans)",
          fontSize: size === "lg" ? 17 : 15,
          color: onDark ? "var(--cream-50)" : "var(--text-body)",
          minWidth: 0,
        }}
      />
    </span>
  )
}
