"use client"

import { useEffect } from "react"
import { motion } from "framer-motion"
import type { Product } from "@/types/product"

type Theme = "light" | "dark"

type Props = {
    search_results: Product[]
    tool_name: string
    theme: Theme
    onClose: () => void
}

const SearchResultsDialog = ({ search_results, tool_name, theme, onClose }: Props) => {
    const isLight = theme === "light"

    useEffect(() => {
        const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
        document.addEventListener("keydown", onKey)
        document.body.style.overflow = "hidden"
        return () => {
            document.removeEventListener("keydown", onKey)
            document.body.style.overflow = ""
        }
    }, [onClose])

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.button
                type="button"
                aria-label="Close"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={onClose}
                className="absolute inset-0 bg-black/70 backdrop-blur-sm cursor-default"
            />

            <motion.div
                role="dialog"
                aria-modal="true"
                initial={{ opacity: 0, scale: 0.96, y: 12 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96, y: 8 }}
                transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                className={`relative w-full max-w-lg max-h-[40vh] md:max-h-[70vh] flex flex-col rounded-2xl border shadow-2xl overflow-hidden ${isLight ? "bg-white border-black/10" : "bg-[#0c0c0c] border-white/10"
                    }`}
            >
                {/* Header */}
                <div className={`flex items-center justify-between px-5 pt-4 pb-3 shrink-0 border-b ${isLight ? "border-black/8" : "border-white/8"}`}>
                    <div className="flex items-center gap-x-2">
                        <p className={`font-mono text-xs ${isLight ? "text-black/50" : "text-white/50"}`}>
                            {tool_name}
                        </p>
                        <motion.span
                            animate={{ opacity: [0.4, 1, 0.4] }}
                            transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
                            className={`ml-2 w-1.5 h-1.5 rounded-full ${isLight ? "bg-black/40" : "bg-white/40"}`}
                        />
                        <p className={`font-mono text-xs ${isLight ? "text-black/50" : "text-white/50"}`}>
                            {search_results.length} result{search_results.length !== 1 ? "s" : ""} retrieved
                        </p>

                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Close"
                        className={`w-7 h-7 flex items-center justify-center rounded-lg transition-colors ${isLight ? "text-black/40 hover:text-black hover:bg-black/6" : "text-white/40 hover:text-white hover:bg-white/6"
                            }`}
                    >
                        <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                            <path d="M1 1L10 10M10 1L1 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                        </svg>
                    </button>
                </div>

                {/* JSON list */}
                <div className={`flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-y-3 ${isLight ? "scrollbar-thin-light" : "scrollbar-thin-dark"}`}>
                    {search_results.map((result, i) => (
                        <motion.pre
                            key={result.canonical_id}
                            initial={{ opacity: 0, x: -6 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.2, delay: i * 0.05 }}
                            className={`font-mono text-xs whitespace-pre-wrap break-all leading-relaxed p-3 rounded-lg border ${isLight
                                ? "text-black/60 bg-black/3 border-black/8"
                                : "text-white/60 bg-white/3 border-white/8"
                                }`}
                        >
                            {JSON.stringify(result, null, 2)}
                        </motion.pre>
                    ))}
                </div>
            </motion.div>
        </div>
    )
}

export default SearchResultsDialog
