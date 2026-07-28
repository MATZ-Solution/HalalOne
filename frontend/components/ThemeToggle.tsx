"use client"

import { motion } from "framer-motion"
import type { Theme } from "@/components/markdown/Markdown"

type ThemeToggleProps = {
    theme: Theme
    onToggle: () => void
}

const THUMB_SIZE = 26
const TRACK_WIDTH = 60
const TRACK_PADDING = 3
const THUMB_TRAVEL = TRACK_WIDTH - THUMB_SIZE - TRACK_PADDING * 2

/** Google Material Symbols: dark_mode (outlined) */
function DarkModeIcon({ className }: { className?: string }) {
    return (
        <svg
            className={className}
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 -960 960 960"
            width="18"
            height="18"
            fill="currentColor"
            aria-hidden
        >
            <path d="M480-120q-150 0-255-105T120-480q0-150 105-255t255-105q14 0 27.5 1t26.5 3q-41 59-41.5 133.5T433-357q46 46 110.5 46.5T676-357q10 41 11.5 82.5T676-192q-91 82-196 82Z" />
        </svg>
    )
}

/** Google Material Symbols: light_mode (outlined) */
function LightModeIcon({ className }: { className?: string }) {
    return (
        <svg
            className={className}
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 -960 960 960"
            width="18"
            height="18"
            fill="currentColor"
            aria-hidden
        >
            <path d="M480-360q50 0 85-35t35-85q0-50-35-85t-85-35q-50 0-85 35t-35 85q0 50 35 85t85 35Zm0 80q-83 0-141.5-58.5T280-480q0-83 58.5-141.5T480-680q83 0 141.5 58.5T680-480q0 83-58.5 141.5T480-280ZM200-440H40v-80h160v80Zm720 0H760v-80h160v80ZM480-760v-160h80v160h-80Zm0 720v-160h80v160h-80ZM256-650l-101-97 57-59 96 100-52 56Zm492 492-97-101 59-57 100 96-62 62Zm-98-550 97-101 56 52-100 96-53-47Zm-492 492 101-97 47 53-96 100-52-56Z" />
        </svg>
    )
}

export default function ThemeToggle({ theme, onToggle }: ThemeToggleProps) {
    const isLight = theme === "light"

    return (
        <button
            type="button"
            role="switch"
            aria-checked={isLight}
            aria-label={isLight ? "Switch to dark mode" : "Switch to light mode"}
            onClick={onToggle}
            className={`fixed top-6 right-6 z-40 rounded-full border p-1 transition-colors cursor-pointer ${
                isLight
                    ? "border-black/15 bg-black/5 hover:bg-black/8"
                    : "border-white/15 bg-white/5 hover:bg-white/8"
            }`}
            style={{ width: TRACK_WIDTH + TRACK_PADDING * 2 }}
        >
            <div
                className="relative flex items-center justify-between rounded-full"
                style={{ width: TRACK_WIDTH, height: THUMB_SIZE + 2 }}
            >
                <DarkModeIcon
                    className={`absolute left-2 z-0 pointer-events-none transition-opacity duration-200 ${
                        isLight ? "opacity-35" : "opacity-100"
                    } ${isLight ? "text-black" : "text-white"}`}
                />
                <LightModeIcon
                    className={`absolute right-2 z-0 pointer-events-none transition-opacity duration-200 ${
                        isLight ? "opacity-100" : "opacity-35"
                    } ${isLight ? "text-black" : "text-white"}`}
                />

                <motion.div
                    className={`absolute top-1/2 -translate-y-1/2 rounded-full shadow-sm z-10 ${
                        isLight
                            ? "bg-white border border-black/10 shadow-black/10"
                            : "bg-white/15 border border-white/20 shadow-black/30"
                    }`}
                    style={{ width: THUMB_SIZE, height: THUMB_SIZE, left: TRACK_PADDING }}
                    animate={{ x: isLight ? THUMB_TRAVEL : 0 }}
                    transition={{ type: "spring", stiffness: 520, damping: 32 }}
                />
            </div>
        </button>
    )
}
