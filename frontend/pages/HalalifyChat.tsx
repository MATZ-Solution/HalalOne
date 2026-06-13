"use client"
import useWebsocket from "@/hooks/useWebsocket"
import SendIcon from "../icons/send_icon.svg"
import ImageIcon from "../icons/image_icon.svg"
import ScanIcon from "../icons/scan_icon.svg"
import QRBarcodeScanner from "@/components/QRBarcodeScanner"
import ImageExtractionDialog from "@/components/ImageExtractionDialog"
import { useRef, useState, useEffect, type ChangeEvent } from "react"
import { motion, AnimatePresence, m } from "framer-motion"
import type { Product } from "@/types/product"
import { statusBadge, statusAccent, statusDot } from "@/utils/halalStatus"
import ProductDetailModal from "@/components/product/ProductDetailModal"
import Markdown, { type Theme } from "@/components/markdown/Markdown"
import ThemeToggle from "@/components/ThemeToggle"
import SearchResultsDialog from "@/components/SearchResultsDialog"

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

type ReasoningContent = {
    node: string
    reasoning: string
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
    const [currentThreadID, setCurrentThreadID] = useState<string>(crypto.randomUUID())
    const { isConnected, lastMessage, sendMessage, messageCount } = useWebsocket(`${process.env.NEXT_PUBLIC_BACKEND_WS_URL}/ws/${currentThreadID}`)
    const inputRef = useRef<HTMLDivElement | null>(null)
    const fileInputRef = useRef<HTMLInputElement | null>(null)
    const messagesEndRef = useRef<HTMLDivElement | null>(null)
    const [theme, setTheme] = useState<Theme>("dark")
    const [textPresent, setTextPresent] = useState(false)
    const [pendingImage, setPendingImage] = useState<AttachedImage | null>(null)
    const [dialogOpen, setDialogOpen] = useState(false)
    const [searchDialogOpen, setSearchDialogOpen] = useState({ showButton: false, showDialog: false })
    const [messages, setMessages] = useState<Message[]>([])
    const [loading, setLoading] = useState(false)
    const [statusMessage, setStatusMessage] = useState<string | null>("Thinking through")
    const [loadingPhrase, setLoadingPhrase] = useState("")
    const [intermediateSearchResults, setIntermediateSearchResults] = useState<{ tool_name: string, search_results: Product[] } | null>(null)
    const [toolCalls, setToolCalls] = useState<ToolCall[]>([])
    const [reasoningContent, setReasoningContent] = useState<ReasoningContent[]>([])
    const [detailsOpen, setDetailsOpen] = useState(false)
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
    const [scannerOpen, setScannerOpen] = useState(false)
    const hasMessages = messages.length > 0
    const isLight = theme === "light"
    const canSend = textPresent && !loading
    const sendActive = isLight ? "#000000" : "#ffffff"
    const sendInactive = isLight ? "#00000040" : "#ffffff40"
    type Alerts = "connection" | "server crash" | "high load"
    const [permanentAlertDetails, setPermanentAlertDetails] = useState<{ alertType: Alerts, showAlert: boolean, alertContent: string | null }[]>([])
    const currentAlerts = useRef<(Alerts)[]>([])
    const [expandAlerts, setExpandAlerts] = useState<boolean>(false)
    const isConnectedRef = useRef(isConnected)

    useEffect(() => {
        isConnectedRef.current = isConnected
    }, [isConnected])

    useEffect(() => {
        let timeoutID: NodeJS.Timeout | null = null
        if (!isConnected && !currentAlerts.current.includes("connection")) {
            // wait 3 seconds before showing alert
            timeoutID = setTimeout(() => {
                if (isConnectedRef.current) {
                    return
                };
                setPermanentAlertDetails((prev) => [...(prev || []),
                {
                    alertType: "connection",
                    showAlert: true,
                    alertContent: 'NOT CONNECTED'
                }])
                currentAlerts.current.push("connection")
            }, 3000);
        } else {
            if (currentAlerts.current.includes("connection")) {
                setPermanentAlertDetails((prev) => prev?.filter(m => m.alertType != "connection"))
                currentAlerts.current = currentAlerts.current.filter(a => a !== "connection");
            }
        }
        return () => { if (timeoutID) clearTimeout(timeoutID) }

    }, [isConnected])



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
            console.log("Data", data)
            if (data.type === "tool_status") {
                setStatusMessage(data.message)
                setDetailsOpen(true)
                if (data.tool && data.args !== undefined) {
                    setToolCalls(prev => [...prev, { tool: data.tool, args: data.args }])
                }
            } else if (data.type === "reasoning") {

                setReasoningContent(prev => {
                    const exists = prev.some(m => m.node === data.node)

                    if (exists) {
                        return prev.map(m => m.node === data.node ? { ...m, reasoning: m.reasoning + data.reasoning } : m)
                    }
                    else {
                        return [...(prev || []), { node: data.node, reasoning: data.reasoning }]
                    }
                })
            } else if (data.type === "search_results") {
                setIntermediateSearchResults({ tool_name: data.tool, search_results: data.search_results ?? [] })
                setSearchDialogOpen(prev => ({ ...prev, showButton: true }))
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
                setReasoningContent([])
                setIntermediateSearchResults({ tool_name: "", search_results: [] })
                setSearchDialogOpen({ showButton: false, showDialog: false })
                setDetailsOpen(false)
            }
        } catch { }
    }, [messageCount])

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages, loading])

    const handleImageSelect = async (e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file || !file.type.startsWith("image/")) return
        const img = await fileToAttachedImage(file)
        setPendingImage(img)
        setDialogOpen(true)
        e.target.value = ""
    }

    const pickPhrase = () => LOADING_PHRASES[Math.floor(Math.random() * LOADING_PHRASES.length)]

    const handleExtractionDialogClose = () => {
        if (pendingImage) URL.revokeObjectURL(pendingImage.previewUrl)
        setPendingImage(null)
        setDialogOpen(false)
    }

    const handleSearchResultDialogClose = () => {
        setSearchDialogOpen(prev => ({ ...prev, showDialog: false }))
    }

    const handleDialogConfirm = (
        fields: Record<string, string | string[]>,
        message: string,
        imageDataUrl: string,
    ) => {
        setMessages(prev => [...prev, {
            id: crypto.randomUUID(),
            role: "user",
            content: message,
            imageDataUrl,
        }])
        sendMessage(JSON.stringify({
            type: "run_with_fields",
            fields,
            ...(message ? { message } : {}),
        }))
        if (pendingImage) URL.revokeObjectURL(pendingImage.previewUrl)
        setPendingImage(null)
        setDialogOpen(false)
        setLoading(true)
        setStatusMessage(null)
        setToolCalls([])
        setReasoningContent([])
        setIntermediateSearchResults({ tool_name: "", search_results: [] })
        setSearchDialogOpen({ showButton: false, showDialog: false })
        setDetailsOpen(false)
        setLoadingPhrase(pickPhrase())
    }

    const handleScanResult = (query: string) => {
        setScannerOpen(false)
        setMessages(prev => [...prev, { id: crypto.randomUUID(), role: "user", content: query }])
        sendMessage(JSON.stringify({ type: "prompt", message: query }))
        setLoading(true)
        setStatusMessage(null)
        setToolCalls([])
        setReasoningContent([])
        setIntermediateSearchResults({ tool_name: "", search_results: [] })
        setSearchDialogOpen({ showButton: false, showDialog: false })
        setDetailsOpen(false)
        setLoadingPhrase(pickPhrase())
    }

    const handleSend = () => {
        const text = inputRef.current?.textContent?.trim() || ""
        if (!text) return

        sendMessage(JSON.stringify({ type: "prompt", message: text }))
        setMessages(prev => [...prev, { id: crypto.randomUUID(), role: "user", content: text }])

        if (inputRef.current) inputRef.current.textContent = ""
        setTextPresent(false)
        setLoading(true)
        setStatusMessage(null)
        setToolCalls([])
        setReasoningContent([])
        setIntermediateSearchResults({ tool_name: "", search_results: [] })
        setSearchDialogOpen({ showButton: false, showDialog: false })
        setDetailsOpen(false)
        setLoadingPhrase(pickPhrase())
    }


    const inputBox = (
        <div className={`w-full p-2 rounded-lg border ${isLight ? "border-black/30" : "border-white/30"}`}>
            {/* {disconnection Status Alert} */}

            <div className="flex gap-x-2 items-end w-full">
                <div className="relative flex-1 min-w-0">
                    {!textPresent && (
                        <span className={`absolute left-0 top-0 switzer-400 pointer-events-none ${isLight ? "text-black/40" : "text-white/40"}`}>
                            Is Nurpur Milk halal?
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
                        contentEditable={isConnected}
                        className={`focus:outline-none w-full switzer-500 max-h-[200px] overflow-y-auto min-h-6 ${isLight ? "text-black" : "text-white"}`}
                    />
                </div>

                <input disabled={!isConnected} ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleImageSelect} />

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
                    onClick={() => !loading && fileInputRef.current?.click()}
                    aria-label="Upload image"
                    className={`shrink-0 w-6 h-6 transition-colors ${loading ? "cursor-default opacity-30" : "cursor-pointer"} ${isLight ? "text-black/40 hover:text-black" : "text-white/40 hover:text-white/80"}`}
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
                    onClick={() => toolCalls.length > 0 && setDetailsOpen(p => !p)}
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
                            animate={{ rotate: detailsOpen ? 180 : 0 }}
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
            <AnimatePresence>
                {detailsOpen && (
                    <motion.div className={`flex gap-x-4 ${isLight ? 'bg-black/4 border border-black/8 scrollbar-thin-light' : 'bg-white/4 border border-white/8 scrollbar-thin-dark'} rounded-lg max-h-50 overflow-y-auto p-3`}>
                        {/* Tool call dropdown */}
                        <AnimatePresence>
                            {detailsOpen && toolCalls.length > 0 && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: "auto" }}
                                    exit={{ opacity: 0, height: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="flex flex-col shrink-0 min-w-1/2 gap-y-2"
                                >
                                    <strong className={`mb-1.5 text-sm font-mono ${isLight ? "text-black/50" : "text-white/50"}`}>Tool calls</strong>
                                    <div className="w-full flex justify-center mb-2.5">
                                        <div className={`w-[98%] border-t ${isLight ? "border-black/10" : "border-white/10"}`} />
                                    </div>
                                    {toolCalls.map((tc, i) => (
                                        <div
                                            key={i}
                                            className={`flex flex-col gap-y-1.5`}
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
                        {/* {Reasoning dropdown} */}
                        <AnimatePresence>

                            {detailsOpen && reasoningContent && reasoningContent.length > 0 && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: "auto" }}
                                    exit={{ opacity: 0, height: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="flex flex-col gap-y-2"
                                >
                                    <strong className={`mb-1.5 text-sm font-mono ${isLight ? "text-black/50" : "text-white/50"}`}>Graph Execution</strong>
                                    <div className="w-full flex justify-center mb-2.5">
                                        <div className={`w-[98%] border-t ${isLight ? "border-black/10" : "border-white/10"}`} />
                                    </div>
                                    {reasoningContent.map((r, i) => (
                                        i === reasoningContent.length - 1 ? (
                                            // apply bottom padding to the last item
                                            <div className="flex flex-col gap-y-2 pb-3" key={i}>
                                                <div className={`p-1 rounded-xs border w-max ${isLight ? "border-red-400/30" : "border-green-500/20"}`}>
                                                    <p className={`text-xs font-mono ${isLight ? "text-black/50" : "text-white/50"}`}>{r.node}</p>
                                                </div>
                                                <div>
                                                    <p className={`text-xs font-mono ${isLight ? "text-black/50" : "text-white/50"}`}>{r.reasoning}</p>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="flex flex-col gap-y-2" key={i}>
                                                <div className={`p-1 rounded-xs border w-max ${isLight ? "border-red-400/30" : "border-green-500/20"}`}>
                                                    <p className={`text-xs font-mono ${isLight ? "text-black/50" : "text-white/50"}`}>{r.node}</p>
                                                </div>
                                                <div>
                                                    <p className={`text-xs font-mono ${isLight ? "text-black/50" : "text-white/50"}`}>{r.reasoning}</p>
                                                </div>
                                            </div>
                                        )
                                    ))}
                                </motion.div>
                            )}
                        </AnimatePresence>

                    </motion.div>
                )}
            </AnimatePresence>
            <AnimatePresence>
                {searchDialogOpen.showButton && (
                    <motion.div onClick={() => {
                        setSearchDialogOpen(prev => ({ ...prev, showDialog: true }))
                    }} initial={{ opacity: 0 }} animate={{ opacity: [0.4, 0.8, 1] }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}
                        className={`w-max px-2 py-1 cursor-pointer flex gap-x-2 items-center rounded-xs border ${isLight ? "border-red-400/30" : "border-green-500/20"}`}>
                        <div className={`w-2 h-2 ${isLight ? "bg-red-400/30" : "bg-green-500/20"} rounded-full`}></div>
                        <p className={`text-xs font-mono ${isLight ? " text-black /50" : "text-white/50"}`}>See search progress</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    )

    return (
        <div className={`w-full h-screen flex flex-col transition-colors duration-300 overflow-hidden ${isLight ? "bg-white" : "bg-black"}`}>

            {/* {alertDetails.showAlert && (
                <motion.div className="fixed w-full top-4 flex justify-center z-10">
                    <motion.div className="animate-pulse left-[40%] bg-orange-700 w-60 p-0.5 rounded-sm flex items-center">
                        <strong className="roboto-500 text-sm tracking-tight text-white ml-4">{alertDetails?.alertType}</strong>
                    </motion.div>
                </motion.div>
            )} */}

            <AnimatePresence>
                {permanentAlertDetails && permanentAlertDetails.length > 0 && (
                    <motion.div className="w-full fixed top-6 right-6 flex flex-col gap-y-2 items-center">
                        {permanentAlertDetails.slice(0, expandAlerts ? permanentAlertDetails.length - 1 : 1).map((m, i) => {
                            return (
                                <motion.div className="w-max" key={i}>
                                    {permanentAlertDetails.length > 1 && (
                                        <div onClick={() => {
                                            setExpandAlerts(prev => !prev)
                                        }} className="z-20 absolute cursor-pointer bg-white -top-4 right-0 w-5.5 h-5.5 flex justify-center items-center rounded-full border border-orange-400/40">
                                            <strong className={`switzer-800 text-xs ${isLight ? "text-orange-700" : "text-orange-700"}`}>
                                                {permanentAlertDetails.length}+
                                            </strong>
                                        </div>
                                    )}
                                    <div className="animate-pulse left-[40%] bg-orange-700 w-60 p-0.5 rounded-sm flex items-center">
                                        <strong className="roboto-500 text-sm tracking-tight text-white ml-4">{m.alertContent}</strong>
                                    </div>

                                </motion.div>
                            )
                        })}
                        <motion.div />
                    </motion.div>
                )}
            </AnimatePresence>
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
                                    Halal One
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

            <AnimatePresence>
                {dialogOpen && pendingImage && (
                    <ImageExtractionDialog
                        key="image-dialog"
                        image={pendingImage}
                        theme={theme}
                        onConfirm={handleDialogConfirm}
                        onClose={handleExtractionDialogClose}
                    />
                )}
            </AnimatePresence>

            <AnimatePresence>
                {/* some conditional logic here */}
                {searchDialogOpen.showDialog && (
                    <SearchResultsDialog onClose={handleSearchResultDialogClose} theme={theme} tool_name={intermediateSearchResults?.tool_name ?? "Tool"} search_results={intermediateSearchResults?.search_results ?? []}></SearchResultsDialog>
                )}
            </AnimatePresence>
        </div>
    )
}


const dummyProducts: Product[] = [
    {
        canonical_id: "prod_001",
        norm_name: "Organic Chicken Breast",
        companies: ["Tyson Foods", "Perdue Farms"],
        cert_bodies: ["USDA Organic", "Halal Certification Council"],
        typical_uses: ["Grilling", "Roasting", "Stir-fry"],
        marketplace: ["Walmart", "Kroger", "Whole Foods"],
        category_l1: "Meat & Poultry",
        category_l2: "Chicken",
        halal_status: "Halal Certified",
        sold_in: ["United States", "Canada"],
        cert_numbers: ["USDA-ORG-12345", "HAL-67890"],
        health_info: ["High protein", "No antibiotics", "Free-range"],
        fda_numbers: ["FDA-789-012"],
        barcodes: ["0721234567890", "0721234567891"]
    },
    {
        canonical_id: "prod_002",
        norm_name: "Aloe Vera Gel Drink",
        companies: ["Lily of the Desert"],
        cert_bodies: ["Halal Food Authority", "Kosher Certification"],
        typical_uses: ["Digestive health", "Hydration", "Skin health"],
        marketplace: ["Amazon", "CVS", "Walgreens"],
        category_l1: "Beverages",
        category_l2: "Functional Drinks",
        halal_status: "Halal Certified",
        sold_in: ["United States", "UK", "UAE"],
        cert_numbers: ["HFA-45678", "KOS-112233"],
        health_info: ["Supports digestion", "Rich in antioxidants", "Detoxifying"],
        fda_numbers: ["FDA-456-789"],
        barcodes: ["0851234567890"]
    },
    {
        canonical_id: "prod_003",
        norm_name: "Coconut Milk Powder",
        companies: ["Grace Foods", "Thai Kitchen"],
        cert_bodies: ["Halal Monitoring Committee"],
        typical_uses: ["Curries", "Smoothies", "Baking"],
        marketplace: ["Target", "Costco", "Aldi"],
        category_l1: "Pantry Staples",
        category_l2: "Milk & Cream Substitutes",
        halal_status: "Halal Certified",
        sold_in: ["United States", "Australia", "Singapore"],
        cert_numbers: ["HMC-98765"],
        health_info: ["Dairy-free", "Vegan", "Lactose-free"],
        fda_numbers: ["FDA-321-654"],
        barcodes: ["0412345678901", "0412345678902"]
    },
    {
        canonical_id: "prod_004",
        norm_name: "Beef Pepperoni Sticks",
        companies: ["Jack Link's", "Tillamook"],
        cert_bodies: ["IFANCA Halal"],
        typical_uses: ["Snacking", "Lunch boxes", "Hiking"],
        marketplace: ["7-Eleven", "Walmart", "Target"],
        category_l1: "Snacks",
        category_l2: "Meat Snacks",
        halal_status: "Halal Certified",
        sold_in: ["United States", "Canada", "UK"],
        cert_numbers: ["IFANCA-554433"],
        health_info: ["High protein", "Low carb", "No MSG"],
        fda_numbers: ["FDA-987-123"],
        barcodes: ["0712345678902"]
    },
    {
        canonical_id: "prod_005",
        norm_name: "Turmeric Ginger Tea",
        companies: ["Traditional Medicinals", "Yogi Tea"],
        cert_bodies: ["Halal Quality International"],
        typical_uses: ["Immune support", "Evening tea", "Anti-inflammatory"],
        marketplace: ["Sprouts", "Whole Foods", "Amazon"],
        category_l1: "Beverages",
        category_l2: "Herbal Tea",
        halal_status: "Halal Certified",
        sold_in: ["United States", "Germany", "France"],
        cert_numbers: ["HQI-778899"],
        health_info: ["Caffeine-free", "Anti-inflammatory", "Antioxidant-rich"],
        fda_numbers: ["FDA-654-321"],
        barcodes: ["0912345678903", "0912345678904"]
    }
]