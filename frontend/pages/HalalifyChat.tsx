"use client"
import useWebsocket from "@/hooks/useWebsocket"
import SendIcon from "../icons/send_icon.svg"
import ImageIcon from "../icons/image_icon.svg"
import ScanIcon from "../icons/scan_icon.svg"
import QRBarcodeScanner from "@/components/QRBarcodeScanner"
import { useRef, useState, useEffect, type ChangeEvent } from "react"
import { motion, AnimatePresence } from "framer-motion"
import type { Product } from "@/types/product"
import { statusBadge, statusAccent, statusDot } from "@/utils/halalStatus"
import ProductDetailModal from "@/components/product/ProductDetailModal"
import Markdown, { type Theme } from "@/components/markdown/Markdown"
import ThemeToggle from "@/components/ThemeToggle"

type AttachedImage = {
    previewUrl: string
    base64: string
    mimeType: string
}

type Message = {
    id: string
    role: "user" | "agent"
    content: string
    products?: Product[]
    imageDataUrl?: string
}

type ToolCall = {
    tool: string
    args: Record<string, unknown>
}

const THEME_STORAGE_KEY = "halalify-theme"

const LOADING_PHRASES = [
    "Lock n Loaded",
    "Processing",
    "On it",
    "Right on it",
    "Firing it up",
    "Hold tight",
    "One sec",
    "Working on it",
    "Hang tight",
    "Let me check",
]

async function fileToAttachedImage(file: File): Promise<AttachedImage> {
    const previewUrl = URL.createObjectURL(file)
    const base64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => {
            const result = reader.result as string
            const comma = result.indexOf(",")
            resolve(comma >= 0 ? result.slice(comma + 1) : result)
        }
        reader.onerror = () => reject(reader.error)
        reader.readAsDataURL(file)
    })
    return { previewUrl, base64, mimeType: file.type || "image/jpeg" }
}

export default function HalalifyChat() {
    const { lastMessage, sendMessage, messageCount } = useWebsocket(`${process.env.NEXT_PUBLIC_BACKEND_WS_URL}/ws`)

    const inputRef = useRef<HTMLDivElement | null>(null)
    const fileInputRef = useRef<HTMLInputElement | null>(null)
    const messagesEndRef = useRef<HTMLDivElement | null>(null)
    const [theme, setTheme] = useState<Theme>("dark")
    const [textPresent, setTextPresent] = useState(false)
    const [attachedImage, setAttachedImage] = useState<AttachedImage | null>(null)
    const [messages, setMessages] = useState<Message[]>([])
    const [loading, setLoading] = useState(false)
    const [statusMessage, setStatusMessage] = useState<string | null>(null)
    const [loadingPhrase, setLoadingPhrase] = useState("")
    const [toolCalls, setToolCalls] = useState<ToolCall[]>([])
    const [toolDetailsOpen, setToolDetailsOpen] = useState(false)
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
    const [scannerOpen, setScannerOpen] = useState(false)

    const hasMessages = messages.length > 0
    const isLight = theme === "light"
    const canSend = (textPresent || !!attachedImage) && !loading
    const sendActive = isLight ? "#000000" : "#ffffff"
    const sendInactive = isLight ? "#00000040" : "#ffffff40"

    useEffect(() => {
        const stored = localStorage.getItem(THEME_STORAGE_KEY)
        if (stored === "light" || stored === "dark") setTheme(stored)
    }, [])

    const toggleTheme = () => {
        setTheme((prev) => {
            const next: Theme = prev === "dark" ? "light" : "dark"
            localStorage.setItem(THEME_STORAGE_KEY, next)
            return next
        })
    }

    useEffect(() => {
        if (!lastMessage) return
        try {
            const data = JSON.parse(lastMessage)
            if (data.type === "status") {
                setStatusMessage(data.message)
                if (data.tool && data.args !== undefined) {
                    setToolCalls(prev => [...prev, { tool: data.tool, args: data.args }])
                }
            } else if (data.type === "results") {
                setMessages(prev => [...prev, {
                    id: crypto.randomUUID(),
                    role: "agent",
                    content: data.response ?? "",
                    products: data.documents ?? [],
                }])
                setLoading(false)
                setStatusMessage(null)
                setToolCalls([])
                setToolDetailsOpen(false)
            }
        } catch { }
    }, [messageCount])

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages, loading])

    const clearAttachedImage = () => {
        if (attachedImage) URL.revokeObjectURL(attachedImage.previewUrl)
        setAttachedImage(null)
    }

    const handleImageSelect = async (e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file || !file.type.startsWith("image/")) return
        if (attachedImage) URL.revokeObjectURL(attachedImage.previewUrl)
        const img = await fileToAttachedImage(file)
        setAttachedImage(img)
        e.target.value = ""
    }

    const pickPhrase = () => LOADING_PHRASES[Math.floor(Math.random() * LOADING_PHRASES.length)]

    const handleScanResult = (query: string) => {
        setScannerOpen(false)
        setMessages(prev => [...prev, { id: crypto.randomUUID(), role: "user", content: query }])
        sendMessage(JSON.stringify({ type: "prompt", message: query }))
        setLoading(true)
        setStatusMessage(null)
        setToolCalls([])
        setToolDetailsOpen(false)
        setLoadingPhrase(pickPhrase())
    }

    const handleSend = () => {
        const text = inputRef.current?.textContent?.trim() || ""

        if (attachedImage) {
            const imageDataUrl = `data:${attachedImage.mimeType};base64,${attachedImage.base64}`
            sendMessage(JSON.stringify({
                type: "image",
                ...(text ? { message: text } : {}),
                base64: attachedImage.base64,
                mime_type: attachedImage.mimeType,
            }))
            URL.revokeObjectURL(attachedImage.previewUrl)
            setAttachedImage(null)
            setMessages(prev => [...prev, {
                id: crypto.randomUUID(),
                role: "user",
                content: text,
                imageDataUrl,
            }])
        } else {
            if (!text) return
            sendMessage(JSON.stringify({ type: "prompt", message: text }))
            setMessages(prev => [...prev, { id: crypto.randomUUID(), role: "user", content: text }])
        }

        if (inputRef.current) inputRef.current.textContent = ""
        setTextPresent(false)
        setLoading(true)
        setStatusMessage(null)
        setToolCalls([])
        setToolDetailsOpen(false)
        setLoadingPhrase(pickPhrase())
    }

    const inputBox = (
        <div className={`relative flex flex-col gap-y-2 w-full p-2 rounded-lg border ${isLight ? "border-black/30" : "border-white/30"}`}>
            <div className="flex gap-x-2 items-end w-full">
                <motion.div className="flex flex-col flex-1 min-w-0 gap-y-2">
                    <div className="relative">
                        {!textPresent && !attachedImage && (
                            <span className={`absolute left-0 top-0 switzer-400 pointer-events-none ${isLight ? "text-black/40" : "text-white/40"}`}>
                                Is Nurpur Milk halal?
                            </span>
                        )}
                        {!textPresent && attachedImage && (
                            <span className={`absolute left-0 top-0 switzer-400 pointer-events-none ${isLight ? "text-black/40" : "text-white/40"}`}>
                                Is this halal?
                            </span>
                        )}
                        <div
                            ref={inputRef}
                            onInput={() => {
                                const t = inputRef.current?.textContent?.trim() || ""
                                setTextPresent(t.length > 0)
                            }}
                            onPaste={(e) => {
                                e.preventDefault()
                                const t = e.clipboardData.getData("text/plain")
                                document.execCommand("insertText", false, t)
                            }}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && !e.shiftKey) {
                                    e.preventDefault()
                                    if (canSend) handleSend()
                                }
                            }}
                            contentEditable
                            className={`focus:outline-none w-full switzer-500 max-h-[200px] overflow-y-auto min-h-6 ${isLight ? "text-black" : "text-white"}`}
                        />
                    </div>

                    <AnimatePresence>
                        {attachedImage && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: "auto" }}
                                exit={{ opacity: 0, height: 0 }}
                                className="relative w-14 h-14 shrink-0"
                            >
                                <img
                                    src={attachedImage.previewUrl}
                                    alt="Attached"
                                    className={`w-14 h-14 rounded-lg object-cover border ${isLight ? "border-black/20" : "border-white/20"}`}
                                />
                                <button
                                    type="button"
                                    onClick={clearAttachedImage}
                                    aria-label="Remove image"
                                    className={`absolute -top-1.5 -right-1.5 w-5 h-5 flex items-center justify-center rounded-full border transition-colors ${isLight
                                        ? "bg-white/90 border-black/20 text-black/70 hover:text-black hover:bg-black/10"
                                        : "bg-black/90 border-white/20 text-white/70 hover:text-white hover:bg-white/10"
                                    }`}
                                >
                                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
                                        <path d="M1 1L9 9M9 1L1 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                                    </svg>
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>

                <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleImageSelect} />

                <button
                    type="button"
                    onClick={() => !loading && setScannerOpen(true)}
                    aria-label="Scan QR or barcode"
                    className={`shrink-0 w-6 h-6 transition-colors ${loading ? "cursor-default opacity-30" : "cursor-pointer"} ${isLight ? "text-black/40 hover:text-black" : "text-white/40 hover:text-white/80"}`}
                >
                    <ScanIcon className="w-6 h-6 stroke-current" />
                </button>
                <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    aria-label="Upload image"
                    className={`shrink-0 w-6 h-6 transition-colors cursor-pointer ${isLight ? "text-black/40 hover:text-black" : "text-white/40 hover:text-white/80"}`}
                >
                    <ImageIcon className="w-6 h-6 fill-current" />
                </button>
                <motion.div
                    animate={{ color: canSend ? sendActive : sendInactive }}
                    transition={{ duration: 0.3, ease: "linear" }}
                    onClick={() => canSend && handleSend()}
                    className={`shrink-0 ${canSend ? "cursor-pointer" : "cursor-default"}`}
                >
                    <SendIcon className="w-6 h-6 fill-current" />
                </motion.div>
            </div>
        </div>
    )

    const loadingIndicator = (
        <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col gap-y-1.5"
        >
            {/* Shimmer bar */}
            <div className={`relative h-0.5 w-full overflow-hidden rounded-full ${isLight ? "bg-black/10" : "bg-white/10"}`}>
                <motion.div
                    className="absolute inset-y-0"
                    style={{
                        width: "55%",
                        background: isLight
                            ? "linear-gradient(90deg, transparent, rgba(0,0,0,0.35), transparent)"
                            : "linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)",
                    }}
                    animate={{ x: ["-100%", "280%"] }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                />
            </div>

            {/* Status row */}
            {statusMessage ? (
                <button
                    type="button"
                    onClick={() => toolCalls.length > 0 && setToolDetailsOpen(p => !p)}
                    className={`flex items-center gap-x-1.5 text-left ${toolCalls.length > 0 ? "cursor-pointer" : "cursor-default"}`}
                >
                    <motion.p
                        key={statusMessage}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: [0.4, 0.8, 0.4] }}
                        transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                        className={`switzer-400 text-sm ${isLight ? "text-black/40" : "text-white/40"}`}
                    >
                        {statusMessage}
                    </motion.p>
                    {toolCalls.length > 0 && (
                        <motion.svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="12"
                            height="12"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            className={`shrink-0 ${isLight ? "text-black/30" : "text-white/30"}`}
                            animate={{ rotate: toolDetailsOpen ? 180 : 0 }}
                            transition={{ duration: 0.2 }}
                        >
                            <polyline points="6 9 12 15 18 9" />
                        </motion.svg>
                    )}
                </button>
            ) : (
                <div className="flex items-center">
                    <p className={`switzer-400 text-sm tracking-tight ${isLight ? "text-black/30" : "text-white/30"}`}>
                        {loadingPhrase}
                    </p>
                    <motion.svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className={`ml-2 shrink-0 ${isLight ? "text-black/30" : "text-white/30"}`}
                        animate={{ x: [6, 0, -6], opacity: [0, 1, 0] }}
                        transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
                    >
                        <polyline points="9 18 15 12 9 6" />
                    </motion.svg>
                </div>
            )}

            {/* Tool call dropdown */}
            <AnimatePresence>
                {toolDetailsOpen && toolCalls.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden flex flex-col gap-y-2 pt-1"
                    >
                        {toolCalls.map((tc, i) => (
                            <div
                                key={i}
                                className={`rounded-lg p-3 flex flex-col gap-y-1.5 ${isLight ? "bg-black/4 border border-black/8" : "bg-white/4 border border-white/8"}`}
                            >
                                <p className={`text-xs font-mono ${isLight ? "text-black/50" : "text-white/50"}`}>
                                    {tc.tool}
                                </p>
                                <pre className={`text-xs font-mono overflow-x-auto whitespace-pre-wrap break-all leading-relaxed ${isLight ? "text-black/35" : "text-white/35"}`}>
                                    {JSON.stringify(tc.args, null, 2)}
                                </pre>
                            </div>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    )

    return (
        <div className={`w-full h-screen flex flex-col transition-colors duration-300 overflow-hidden ${isLight ? "bg-white" : "bg-black"}`}>
            <ThemeToggle theme={theme} onToggle={toggleTheme} />

            <AnimatePresence mode="wait">
                {!hasMessages ? (
                    <motion.div
                        key="landing"
                        className="flex-1 flex flex-col items-center justify-center px-4"
                        exit={{ opacity: 0, y: -24, transition: { duration: 0.25, ease: "easeIn" } }}
                    >
                        <div className="w-[80%] md:w-[60%] lg:w-[50%] flex flex-col gap-y-6">
                            <div>
                                <p className={`text-6xl tracking-tighter switzer-500 ${isLight ? "text-black" : "text-white"}`}>
                                    Halalify
                                </p>
                                <div className="rounded-sm switzer-500 text-white text-xs bg-green-600 px-2 h-4 w-max">
                                    <p>Check Halal Status</p>
                                </div>
                            </div>
                            {inputBox}
                        </div>
                    </motion.div>
                ) : (
                    <motion.div
                        key="chat"
                        className="flex-1 flex flex-col overflow-hidden"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.3, ease: "easeOut" }}
                    >
                        {/* Scrollable messages */}
                        <div className="flex-1 overflow-y-auto">
                            <div className="max-w-[80%] md:max-w-[60%] lg:max-w-[50%] mx-auto flex flex-col gap-y-6 pt-10 pb-4 px-4">

                                {messages.map((msg) => (
                                    <motion.div
                                        key={msg.id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.25 }}
                                        className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                                    >
                                        {msg.role === "user" ? (
                                            <div className="max-w-[75%] flex flex-col gap-y-2 items-end">
                                                {msg.imageDataUrl && (
                                                    <img
                                                        src={msg.imageDataUrl}
                                                        alt=""
                                                        className="w-36 h-36 rounded-2xl rounded-br-sm object-cover"
                                                    />
                                                )}
                                                {msg.content && (
                                                    <div className={`px-4 py-2.5 rounded-2xl rounded-br-sm switzer-500 text-sm leading-snug ${isLight ? "bg-black/8 text-black" : "bg-white/10 text-white"}`}>
                                                        {msg.content}
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <div className="flex flex-col gap-y-3 w-full">
                                                {msg.content && (
                                                    <div className={`switzer-400 text-sm leading-relaxed ${isLight ? "text-black/80" : "text-white/80"}`}>
                                                        <Markdown textContent={msg.content} theme={theme} />
                                                    </div>
                                                )}
                                                {msg.products && msg.products.length > 0 && (
                                                    <div className="flex flex-col gap-y-2">
                                                        {msg.products.map((product, i) => (
                                                            <motion.div
                                                                key={product.canonical_id}
                                                                role="button"
                                                                tabIndex={0}
                                                                initial={{ opacity: 0, y: 10 }}
                                                                animate={{ opacity: 1, y: 0 }}
                                                                transition={{ duration: 0.25, delay: i * 0.06 }}
                                                                onClick={() => setSelectedProduct(product)}
                                                                onKeyDown={(e) => {
                                                                    if (e.key === "Enter" || e.key === " ") {
                                                                        e.preventDefault()
                                                                        setSelectedProduct(product)
                                                                    }
                                                                }}
                                                                className={`relative group rounded-xl p-4 flex flex-col gap-y-3 transition-all duration-200 overflow-hidden cursor-pointer focus:outline-none ${isLight
                                                                    ? "border border-black/8 bg-black/2 hover:bg-black/4 hover:border-black/15 focus-visible:ring-1 focus-visible:ring-black/20"
                                                                    : "border border-white/8 bg-white/2 hover:bg-white/4 hover:border-white/15 focus-visible:ring-1 focus-visible:ring-white/20"
                                                                }`}
                                                            >
                                                                <div className={`absolute left-0 top-0 bottom-0 w-[3px] rounded-l-xl ${statusAccent(product.halal_status ?? "")}`} />
                                                                <div className="pl-3 flex flex-col gap-y-3">
                                                                    <div className="flex items-start justify-between gap-x-4">
                                                                        <p className={`switzer-500 capitalize leading-snug ${isLight ? "text-black" : "text-white"}`}>
                                                                            {product.norm_name}
                                                                        </p>
                                                                        <span className={`shrink-0 flex items-center gap-x-1.5 text-xs switzer-500 px-2.5 py-1 rounded-full ${statusBadge(product.halal_status ?? "")}`}>
                                                                            <span className={`w-1.5 h-1.5 rounded-full ${statusDot(product.halal_status ?? "")}`} />
                                                                            {product.halal_status}
                                                                        </span>
                                                                    </div>
                                                                    {(product.category_l1 || product.category_l2) && (
                                                                        <div className="flex flex-wrap gap-1.5">
                                                                            {[product.category_l1, product.category_l2].filter(Boolean).map((cat, j) => (
                                                                                <span key={j} className={`text-xs switzer-400 px-2 py-0.5 rounded-md border ${isLight
                                                                                    ? "text-black/40 bg-black/5 border-black/8"
                                                                                    : "text-white/40 bg-white/5 border-white/8"
                                                                                }`}>
                                                                                    {cat}
                                                                                </span>
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                    {product.companies && product.companies.length > 0 && (
                                                                        <p className={`text-sm switzer-400 leading-relaxed ${isLight ? "text-black/70" : "text-white/70"}`}>
                                                                            {product.companies.map(c =>
                                                                                c.charAt(0).toUpperCase() + c.slice(1).toLowerCase()
                                                                            ).join(" · ")}
                                                                        </p>
                                                                    )}
                                                                    {product.cert_bodies && product.cert_bodies.length > 0 && (
                                                                        <div className="flex flex-wrap items-center gap-1.5">
                                                                            <span className={`switzer-400 text-xs ${isLight ? "text-black/25" : "text-white/25"}`}>
                                                                                Certified by
                                                                            </span>
                                                                            {product.cert_bodies.map((body, j) => (
                                                                                <span key={j} className="text-xs switzer-400 text-green-400/60 bg-green-500/8 border border-green-500/20 px-2 py-0.5 rounded-md">
                                                                                    {body}
                                                                                </span>
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </motion.div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </motion.div>
                                ))}

                                {loading && loadingIndicator}

                                <div ref={messagesEndRef} />
                            </div>
                        </div>

                        {/* Input pinned to bottom */}
                        <div className={`shrink-0 px-4 pt-3 pb-6 flex justify-center border-t ${isLight ? "border-black/8" : "border-white/8"}`}>
                            <div className="w-[80%] md:w-[60%] lg:w-[50%]">
                                {inputBox}
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {scannerOpen && (
                <QRBarcodeScanner
                    theme={theme}
                    onDetected={handleScanResult}
                    onClose={() => setScannerOpen(false)}
                />
            )}

            <ProductDetailModal
                product={selectedProduct}
                onClose={() => setSelectedProduct(null)}
            />
        </div>
    )
}
