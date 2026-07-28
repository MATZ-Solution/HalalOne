"use client"

import { motion } from "framer-motion"

type Theme = "light" | "dark"

type Props = {
    theme: Theme
    message: string
    disclaimer?: string | null
    onConfirm: () => void
    onDecline: () => void
}

// Shown when a session crosses the token threshold. The user chooses to compact
// now (summarize older turns) or keep going — declining raises the trigger, and
// after the third decline compaction is forced. Not dismissible by backdrop: the
// decision must be explicit, so there is no onClose.
export default function CompactionDialog({ theme, message, disclaimer, onConfirm, onDecline }: Props) {
    const isLight = theme === "light"
    const overlayBg = isLight ? "bg-black/50" : "bg-black/70"
    const dialogBg = isLight ? "bg-white border-black/10" : "bg-[#0c0c0c] border-white/10"
    const headingCls = isLight ? "text-black" : "text-white"
    const bodyCls = isLight ? "text-black/60" : "text-white/60"
    const sublabelCls = isLight ? "text-black/40" : "text-white/40"

    return (
        <div className="fixed inset-0 z-80 flex items-center justify-center p-4">
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className={`absolute inset-0 ${overlayBg} backdrop-blur-sm`}
            />

            <motion.div
                role="dialog"
                aria-modal="true"
                aria-label="Compact conversation"
                initial={{ opacity: 0, scale: 0.96, y: 12 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96, y: 8 }}
                transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                className={`relative w-full max-w-sm flex flex-col rounded-2xl border shadow-2xl overflow-hidden ${dialogBg}`}
            >
                <div className="px-5 pt-5 pb-4 flex flex-col gap-y-3">
                    <h2 className={`switzer-500 text-sm ${headingCls}`}>Conversation limit reached</h2>
                    <p className={`switzer-400 text-sm leading-relaxed ${bodyCls}`}>{message}</p>
                    {disclaimer && (
                        <p className={`switzer-400 text-xs leading-relaxed ${sublabelCls}`}>{disclaimer}</p>
                    )}
                </div>

                <div className="px-5 pb-5 flex items-center justify-end gap-x-2">
                    <button
                        type="button"
                        onClick={onDecline}
                        className={`px-3 py-1.5 rounded-lg text-sm switzer-400 transition-colors ${isLight
                            ? "text-black/50 hover:text-black hover:bg-black/5"
                            : "text-white/50 hover:text-white hover:bg-white/5"
                            }`}
                    >
                        Not now
                    </button>
                    <button
                        type="button"
                        onClick={onConfirm}
                        className={`px-4 py-1.5 rounded-lg text-sm switzer-500 transition-colors ${isLight
                            ? "bg-black text-white hover:bg-black/80"
                            : "bg-white text-black hover:bg-white/85"
                            }`}
                    >
                        Compact now
                    </button>
                </div>
            </motion.div>
        </div>
    )
}
