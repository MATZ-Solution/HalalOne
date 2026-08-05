"use client"
import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import LogoutButton from "@/components/auth/LogoutButton"

type Session = {
    session_id: string
    title: string
    description: string
    created_at: string
}

type Props = {
    activeThreadId: string
    onSelectSession: (id: string) => void
    onNewChat: () => void
    sendMessage: (message: string) => void
    lastMessage: string | null
    messageCount: number
}

export default function ChatHistory({
    activeThreadId,
    onSelectSession,
    onNewChat,
    sendMessage,
    lastMessage,
    messageCount,
}: Props) {
    const [open, setOpen] = useState(false)
    const [sessions, setSessions] = useState<Session[]>([])
    const [isLight, setIsLight] = useState(false)
    const [toast, setToast] = useState<string | null>(null)
    // Session id awaiting delete confirmation (null = none).
    const [confirmId, setConfirmId] = useState<string | null>(null)

    // Mirror the app theme
    useEffect(() => {
        const read = () => setIsLight(localStorage.getItem("halalify-theme") === "light")
        read()
        const id = setInterval(read, 200)
        return () => clearInterval(id)
    }, [])

    // Auto-dismiss the toast.
    useEffect(() => {
        if (!toast) return
        const id = setTimeout(() => setToast(null), 2500)
        return () => clearTimeout(id)
    }, [toast])

    // Ask the backend for this user's sessions whenever the drawer opens;
    // clear any pending delete confirmation when it closes.
    useEffect(() => {
        if (open) sendMessage(JSON.stringify({ type: "chat_sessions" }))
        else setConfirmId(null)
    }, [open, sendMessage])

    // Receive session list / delete acknowledgements over the socket.
    useEffect(() => {
        if (!lastMessage) return
        try {
            const data = JSON.parse(lastMessage)
            if (data.type === "chat_sessions") {
                setSessions(data.sessions ?? [])
            } else if (data.type === "delete_session" && data.status === "acknowledged") {
                setSessions(prev => prev.filter(s => s.session_id !== data.session_id))
                setToast("Session successfully deleted")
                // If the open session was deleted, start a fresh chat.
                if (data.session_id === activeThreadId) onNewChat()
            }
        } catch { }
    }, [messageCount])

    const fmt = (iso: string) =>
        new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" })

    const handleSelect = (id: string) => {
        onSelectSession(id)
        setOpen(false)
    }

    const handleNew = () => {
        onNewChat()
        setOpen(false)
    }

    const handleDelete = (id: string) => {
        sendMessage(JSON.stringify({ type: "delete_session", session_id: id }))
        setConfirmId(null)
    }

    const bg = isLight ? "bg-white border-black/10" : "bg-[#111] border-white/8"
    const text = isLight ? "text-black" : "text-white"
    const muted = isLight ? "text-black/40" : "text-white/40"
    const hover = isLight ? "hover:bg-black/5" : "hover:bg-white/5"
    const active = isLight ? "bg-black/8" : "bg-white/8"
    const btn = isLight
        ? "cursor-pointer text-black/40 hover:text-black/70 hover:bg-black/5"
        : "cursor-pointer text-white/40 hover:text-white/70 hover:bg-white/5"

    return (
        <>
            {/* Toggle button */}
            <motion.button
                onClick={() => setOpen(p => !p)}
                aria-label="Chat history"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.92 }}
                transition={{ type: "spring", stiffness: 400, damping: 22 }}
                className={`fixed top-3 left-4 z-50 p-2 rounded-lg border transition-colors ${btn} ${isLight ? "border-black/10 hover:border-black/20" : "border-white/10 hover:border-white/20"}`}
            >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="3" y1="6" x2="21" y2="6" />
                    <line x1="3" y1="12" x2="21" y2="12" />
                    <line x1="3" y1="18" x2="15" y2="18" />
                </svg>
            </motion.button>

            {/* Backdrop */}
            <AnimatePresence>
                {open && (
                    <motion.div
                        className="fixed inset-0 z-40 bg-black/20"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setOpen(false)}
                    />
                )}
            </AnimatePresence>

            {/* Drawer */}
            <AnimatePresence>
                {open && (
                    <motion.div
                        className={`fixed top-0 left-0 h-full w-64 z-50 flex flex-col border-r ${bg}`}
                        initial={{ x: "-100%" }}
                        animate={{ x: 0 }}
                        exit={{ x: "-100%" }}
                        transition={{ type: "spring", stiffness: 320, damping: 32 }}
                    >
                        {/* Header */}
                        <div className={`flex items-center justify-between px-4 py-4 border-b ${isLight ? "border-black/8" : "border-white/8"}`}>
                            <span className={`text-sm switzer-500 ${text}`}>Chats</span>
                            <button
                                onClick={() => setOpen(false)}
                                className={`p-1 rounded-md transition-colors ${btn}`}
                                aria-label="Close"
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <line x1="18" y1="6" x2="6" y2="18" />
                                    <line x1="6" y1="6" x2="18" y2="18" />
                                </svg>
                            </button>
                        </div>

                        {/* New chat */}
                        <button
                            onClick={handleNew}
                            className={`cursor-pointer mx-3 mt-3 mb-1 flex items-center gap-x-2 px-3 py-2 rounded-lg text-sm switzer-400 transition-colors ${isLight ? "border border-black/10 text-black/60 hover:bg-black/5" : "border border-white/10 text-white/60 hover:bg-white/5"}`}
                        >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                                <line x1="12" y1="5" x2="12" y2="19" />
                                <line x1="5" y1="12" x2="19" y2="12" />
                            </svg>
                            New chat
                        </button>

                        {/* Session list */}
                        <div
                            className="flex-1 overflow-y-auto py-2"
                            style={{
                                scrollbarWidth: "thin",
                                scrollbarColor: isLight ? "rgba(0,0,0,0.2) transparent" : "rgba(255,255,255,0.2) transparent",
                            }}
                        >
                            {sessions.length === 0 ? (
                                <p className={`px-4 py-8 text-xs text-center switzer-400 ${muted}`}>
                                    No previous chats
                                </p>
                            ) : (
                                sessions.map(s => (
                                    <div
                                        key={s.session_id}
                                        role="button"
                                        tabIndex={0}
                                        onClick={() => handleSelect(s.session_id)}
                                        onKeyDown={(e) => { if (e.key === "Enter") handleSelect(s.session_id) }}
                                        title={s.description}
                                        className={`group flex items-center gap-x-2 px-4 py-2.5 cursor-pointer transition-colors ${hover} ${s.session_id === activeThreadId ? active : ""}`}
                                    >
                                        <div className="min-w-0 flex-1">
                                            <p className={`text-xs switzer-500 truncate ${text}`}>{s.title}</p>
                                            {s.description && (
                                                <p className={`text-xs switzer-400 mt-0.5 line-clamp-2 ${muted}`}>{s.description}</p>
                                            )}
                                            <p className={`text-[11px] switzer-400 mt-1 ${muted}`}>{fmt(s.created_at)}</p>
                                        </div>
                                        {confirmId === s.session_id ? (
                                            // Inline confirm: ✓ deletes, ✗ cancels.
                                            <div className="shrink-0 flex items-center gap-x-1">
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handleDelete(s.session_id) }}
                                                    aria-label="Confirm delete"
                                                    className="cursor-pointer p-1 rounded-md text-red-500 hover:bg-red-500/10"
                                                >
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                                        <polyline points="20 6 9 17 4 12" />
                                                    </svg>
                                                </button>
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); setConfirmId(null) }}
                                                    aria-label="Cancel delete"
                                                    className={`cursor-pointer p-1 rounded-md ${isLight ? "text-black/40 hover:bg-black/5" : "text-white/40 hover:bg-white/5"}`}
                                                >
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                                        <line x1="18" y1="6" x2="6" y2="18" />
                                                        <line x1="6" y1="6" x2="18" y2="18" />
                                                    </svg>
                                                </button>
                                            </div>
                                        ) : (
                                            <button
                                                onClick={(e) => { e.stopPropagation(); setConfirmId(s.session_id) }}
                                                aria-label="Delete chat"
                                                className={`cursor-pointer shrink-0 p-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity ${isLight ? "text-black/40 hover:text-red-600 hover:bg-black/5" : "text-white/40 hover:text-red-400 hover:bg-white/5"}`}
                                            >
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                    <polyline points="3 6 5 6 21 6" />
                                                    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                                                    <path d="M10 11v6M14 11v6" />
                                                    <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                                                </svg>
                                            </button>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>

                        {/* Footer: sign out, bottom-left */}
                        <div className={`px-3 py-3 border-t ${isLight ? "border-black/8" : "border-white/8"}`}>
                            <LogoutButton />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Toast feedback */}
            <AnimatePresence>
                {toast && (
                    <motion.div
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 12 }}
                        className="fixed bottom-6 left-1/2 -translate-x-1/2 z-60 px-4 py-2 rounded-lg bg-green-600 text-white text-sm switzer-500 shadow-lg"
                    >
                        {toast}
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    )
}
