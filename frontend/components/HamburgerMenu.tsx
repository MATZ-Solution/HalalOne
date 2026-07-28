"use client"

import { useState, useEffect } from "react"
import { createPortal } from "react-dom"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import MenuIcon from "@/icons/menu_icon.svg"
import CloseIcon from "@/icons/close_icon.svg"

const LINKS = [
    { label: "Home", href: "/" },
    { label: "Directories", href: "/directory" },
    { label: "Assistant", href: "/chat" },
    { label: "About Us", href: "/about" },
]

// Small-screen nav (hidden from md up). The trigger sits at the far-right of
// the header, level with the logo. Tapping it opens a full-window overlay with
// the links stacked top-to-bottom, each separated by a divider line. The
// overlay is portalled onto <body> so no header/flex ancestor can constrain it.
export default function HamburgerMenu() {
    const [open, setOpen] = useState(false)
    const [mounted, setMounted] = useState(false)

    // Portals need the DOM; only render the overlay after mount.
    useEffect(() => setMounted(true), [])

    // Freeze the page behind the overlay and allow Escape to close it.
    useEffect(() => {
        if (!open) return
        const previous = document.body.style.overflow
        document.body.style.overflow = "hidden"
        const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false)
        window.addEventListener("keydown", onKey)
        return () => {
            document.body.style.overflow = previous
            window.removeEventListener("keydown", onKey)
        }
    }, [open])

    const overlay = (
        <AnimatePresence>
            {open && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2, ease: "easeOut" }}
                    className="fixed inset-0 z-100 flex h-screen w-screen flex-col bg-background"
                >
                    <div className="flex items-center justify-end px-6 py-3">
                        <button
                            type="button"
                            aria-label="Close menu"
                            onClick={() => setOpen(false)}
                            className="flex items-center justify-center rounded-lg p-2 text-foreground/80 transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                        >
                            <CloseIcon className="block h-6 w-6" />
                        </button>
                    </div>

                    <nav className="flex flex-col border-y border-black/10 divide-y divide-black/10 dark:border-white/10 dark:divide-white/10">
                        {LINKS.map((link) => (
                            <Link
                                key={link.href}
                                href={link.href}
                                onClick={() => setOpen(false)}
                                className="google-sans-flex-700 tracking-tight px-6 py-5 text-2xl text-foreground/90 transition-colors hover:bg-black/5 dark:hover:bg-white/10"
                            >
                                {link.label}
                            </Link>
                        ))}
                    </nav>
                </motion.div>
            )}
        </AnimatePresence>
    )

    return (
        <div className="md:hidden">
            <button
                type="button"
                aria-label="Open menu"
                aria-expanded={open}
                onClick={() => setOpen(true)}
                className="flex items-center justify-center rounded-lg p-2 text-foreground/80 transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
            >
                <MenuIcon className="block h-6 w-6" />
            </button>

            {mounted && createPortal(overlay, document.body)}
        </div>
    )
}
