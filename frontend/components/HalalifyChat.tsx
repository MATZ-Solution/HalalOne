"use client"
import SendIcon from "../icons/send_icon.svg"
import ImageIcon from "../icons/image_icon.svg"
import ScanIcon from "../icons/scan_icon.svg"
import QRBarcodeScanner from "@/components/QRBarcodeScanner"
import ImageExtractionDialog from "@/components/ImageExtractionDialog"
import CompactionDialog from "@/components/CompactionDialog"
import { useRef, useState, useEffect, useReducer, type ChangeEvent, type ClipboardEvent } from "react"
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
    // Short-lived signed CDN URL for a stored image, returned on session reload.
    imageUrl?: string
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

type WS = {
    isConnected: boolean
    lastMessage: string | null
    messageCount: number
    sendMessage: (message: string) => void
}

type Props = {
    threadId: string
    ws: WS
    historyLoading: boolean
    onHistoryLoaded: () => void
}

// A source streamed live while the WebSearch tool runs.
type WebSource = { url: string; title?: string; favicon?: string; highlights?: string[] }

// Human labels for the per-field grounding citations shown on web-result cards.
const FIELD_LABELS: Record<string, string> = {
    norm_name: "Name",
    companies: "Brand",
    halal_status: "Halal status",
    cert_bodies: "Certifier",
    cert_numbers: "Cert no.",
    category_l1: "Category",
    category_l2: "Subcategory",
    sold_in: "Sold in",
    marketplace: "Marketplace",
    barcodes: "Barcode",
    fda_numbers: "FDA no.",
    typical_uses: "Uses",
    health_info: "Health",
}

const hostOf = (url: string) => {
    try { return new URL(url).hostname.replace(/^www\./, "") } catch { return url }
}

// Render a product field's value (string or string[]) as a readable string.
const formatFieldValue = (value: unknown): string => {
    if (Array.isArray(value)) return value.filter(Boolean).join(", ")
    if (value === null || value === undefined || typeof value === "boolean") return ""
    return String(value)
}

// A website's favicon, derived from its URL via Google's favicon service.
const faviconOf = (url: string) => {
    try { return `https://www.google.com/s2/favicons?sz=64&domain=${new URL(url).hostname}` } catch { return "" }
}

// One streamed chunk from the agent (the shapes we read off it).
type StreamChunk = {
    type: string
    session_id?: string
    message?: string
    tool?: string
    args?: Record<string, unknown>
    node?: string
    reasoning?: string
    search_results?: Product[]
    url?: string
    title?: string
    favicon?: string
    highlights?: string[]
    response?: string
    documents?: Product[]
    disclaimer?: string | null
}

// All per-session streaming state in one object, so a whole session can be moved
// as a unit between the on-screen view and the background cache of in-flight ones.
// Compaction handshake state for a session. "awaiting" shows the confirm modal;
// "running" shows a slim banner while the summary is generated. Kept inside
// Runtime so it stashes/restores on session switch exactly like streaming state.
type Compaction = {
    phase: "idle" | "awaiting" | "running"
    message?: string
    disclaimer?: string | null
}

type Runtime = {
    messages: Message[]
    loading: boolean
    statusMessage: string | null
    loadingPhrase: string
    intermediateSearchResults: { tool_name: string; search_results: Product[] } | null
    toolCalls: ToolCall[]
    reasoningContent: ReasoningContent[]
    detailsOpen: boolean
    webSources: WebSource[]
    searchDialogOpen: { showButton: boolean; showDialog: boolean }
    compaction: Compaction
}

const emptyRuntime = (): Runtime => ({
    messages: [],
    loading: false,
    statusMessage: null,
    loadingPhrase: "",
    intermediateSearchResults: null,
    toolCalls: [],
    reasoningContent: [],
    detailsOpen: false,
    webSources: [],
    searchDialogOpen: { showButton: false, showDialog: false },
    compaction: { phase: "idle" },
})

// Apply a single agent chunk to a runtime. Pure, so it drives both the on-screen
// session (via the reducer) and backgrounded ones (on their cache entry) identically.
const applyChunk = (rt: Runtime, data: StreamChunk): Runtime => {
    switch (data.type) {
        case "tool_status": {
            const toolCalls = data.tool && data.args !== undefined
                ? [...rt.toolCalls, { tool: data.tool, args: data.args }]
                : rt.toolCalls
            return { ...rt, statusMessage: data.message ?? null, detailsOpen: true, toolCalls }
        }
        case "reasoning": {
            const node = data.node ?? ""
            const reasoning = data.reasoning ?? ""
            const exists = rt.reasoningContent.some(m => m.node === node)
            const reasoningContent = exists
                ? rt.reasoningContent.map(m => m.node === node ? { ...m, reasoning: m.reasoning + reasoning } : m)
                : [...rt.reasoningContent, { node, reasoning }]
            return { ...rt, reasoningContent }
        }
        case "search_results":
            return {
                ...rt,
                intermediateSearchResults: { tool_name: data.tool ?? "", search_results: data.search_results ?? [] },
                searchDialogOpen: { ...rt.searchDialogOpen, showButton: true },
            }
        case "web_source":
            if (rt.webSources.some(s => s.url === data.url)) return rt
            return { ...rt, webSources: [...rt.webSources, { url: data.url as string, title: data.title, favicon: data.favicon, highlights: data.highlights }] }
        case "compaction_request":
            // Turn is paused pending the user's decision — stop the spinner.
            return { ...rt, loading: false, compaction: { phase: "awaiting", message: data.message, disclaimer: data.disclaimer } }
        case "compaction_running":
            return { ...rt, loading: true, statusMessage: data.message ?? null, compaction: { phase: "running", message: data.message } }
        case "compaction_done":
        case "compaction_failed":
            // The resumed answer streams next; leave loading as-is until results.
            return { ...rt, compaction: { phase: "idle" } }
        case "results":
            return {
                ...rt,
                messages: [...rt.messages, { id: crypto.randomUUID(), role: "agent", content: data.response ?? "", products: data.documents ?? [] }],
                loading: false,
                statusMessage: null,
                toolCalls: [],
                reasoningContent: [],
                intermediateSearchResults: { tool_name: "", search_results: [] },
                searchDialogOpen: { showButton: false, showDialog: false },
                detailsOpen: false,
                webSources: [],
                compaction: { phase: "idle" },
            }
        default:
            return rt
    }
}

type RuntimeAction =
    | { type: "reset" }
    | { type: "hydrate"; runtime: Runtime }
    | { type: "send"; message: Message; phrase: string }
    | { type: "chunk"; data: StreamChunk }
    | { type: "promptRejected" }
    | { type: "resumeTurn" }
    | { type: "toggleDetails" }
    | { type: "openSearchDialog" }
    | { type: "closeSearchDialog" }

const runtimeReducer = (rt: Runtime, action: RuntimeAction): Runtime => {
    switch (action.type) {
        case "reset":
            return emptyRuntime()
        case "hydrate":
            return action.runtime
        case "send":
            // New turn: keep the conversation, add the user message, clear panels.
            return { ...emptyRuntime(), messages: [...rt.messages, action.message], loading: true, loadingPhrase: action.phrase }
        case "chunk":
            return applyChunk(rt, action.data)
        case "promptRejected": {
            // The server rejected the just-sent prompt (rate/LLM cap): stop the
            // spinner and drop the optimistic user bubble so a retry is clean.
            const messages = rt.messages.length && rt.messages[rt.messages.length - 1].role === "user"
                ? rt.messages.slice(0, -1) : rt.messages
            return { ...emptyRuntime(), messages }
        }
        case "resumeTurn":
            // User answered the compaction prompt: close the modal and restart the
            // spinner while the held turn resumes (server confirms via its chunks).
            return { ...rt, loading: true, compaction: { phase: "idle" } }
        case "toggleDetails":
            return { ...rt, detailsOpen: !rt.detailsOpen }
        case "openSearchDialog":
            return { ...rt, searchDialogOpen: { ...rt.searchDialogOpen, showDialog: true } }
        case "closeSearchDialog":
            return { ...rt, searchDialogOpen: { ...rt.searchDialogOpen, showDialog: false } }
    }
}

export default function HalalifyChat({ threadId, ws, historyLoading, onHistoryLoaded }: Props) {
    const { isConnected, lastMessage, sendMessage, messageCount } = ws
    const inputRef = useRef<HTMLDivElement | null>(null)
    const fileInputRef = useRef<HTMLInputElement | null>(null)
    const messagesEndRef = useRef<HTMLDivElement | null>(null)
    const [theme, setTheme] = useState<Theme>("dark")
    const [textPresent, setTextPresent] = useState(false)
    const [pendingImage, setPendingImage] = useState<AttachedImage | null>(null)
    const [dialogOpen, setDialogOpen] = useState(false)
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
    const [scannerOpen, setScannerOpen] = useState(false)
    // Transient toast for rate-limit / high-load notices from the backend.
    const [toast, setToast] = useState<string | null>(null)

    // All per-session streaming state in one reducer, so a whole session can be
    // stashed/restored (and background sessions advanced) as a single unit.
    const [runtime, dispatch] = useReducer(runtimeReducer, undefined, emptyRuntime)
    const {
        messages, loading, statusMessage, loadingPhrase,
        intermediateSearchResults, toolCalls, reasoningContent,
        detailsOpen, webSources, searchDialogOpen, compaction,
    } = runtime
    const hasMessages = messages.length > 0
    const isLight = theme === "light"
    // Block sending while a compaction decision is pending or running — the
    // backend rejects it anyway, so gate it here for a clean UX.
    const compactionBlocking = compaction.phase !== "idle"
    const canSend = textPresent && !loading && !compactionBlocking
    const sendActive = isLight ? "#000000" : "#ffffff"
    const sendInactive = isLight ? "#00000040" : "#ffffff40"
    type Alerts = "connection" | "server crash" | "high load"
    const [permanentAlertDetails, setPermanentAlertDetails] = useState<{ alertType: Alerts, showAlert: boolean, alertContent: string | null }[]>([])
    const currentAlerts = useRef<(Alerts)[]>([])
    const [expandAlerts, setExpandAlerts] = useState<boolean>(false)
    const isConnectedRef = useRef(isConnected)
    // Tracks the session whose history we've already requested, so a reconnect
    // doesn't clobber an in-progress conversation.
    const loadedSessionRef = useRef<string | null>(null)

    // Cache of sessions with an in-flight response ONLY (keyed by session id).
    // Leaving a streaming session stashes it here so its stream survives the
    // switch; returning restores it without a DB refetch. Evicted on completion,
    // so it never fills with settled sessions.
    const inflightCacheRef = useRef<Map<string, Runtime>>(new Map())
    // Previous threadId, so the switch effect knows which session it's leaving.
    const prevThreadIdRef = useRef<string | null>(null)
    // Live mirror of the whole runtime, read when stashing on switch (the switch
    // effect must see the outgoing session's latest state, not a stale closure).
    const runtimeRef = useRef(runtime)
    const loadingRef = useRef(false)

    useEffect(() => {
        isConnectedRef.current = isConnected
    }, [isConnected])

    useEffect(() => {
        runtimeRef.current = runtime
        loadingRef.current = runtime.loading
    }, [runtime])

    // Runs whenever the active session changes. Stashes an outgoing session that's
    // still streaming, then either restores an incoming stashed session (no
    // refetch) or clears the view so its history is fetched from the backend.
    useEffect(() => {
        const prev = prevThreadIdRef.current
        // Leaving a session whose response is still streaming? Stash its whole
        // runtime so the switch doesn't kill the stream — chunks for it keep being
        // applied to the stash by session id until it completes.
        if (prev && prev !== threadId) {
            // Stash if streaming OR mid-compaction (awaiting a decision / running),
            // so the modal/alert survives the switch just like live stream progress.
            if (loadingRef.current || runtimeRef.current.compaction.phase !== "idle") {
                inflightCacheRef.current.set(prev, runtimeRef.current)
                console.log(`[inflight-cache] STASH ${prev} — streaming/compacting, ${runtimeRef.current.messages.length} msgs kept`)
            } else {
                console.log(`[inflight-cache] no stash for ${prev} — not streaming (settled)`)
            }
        }
        prevThreadIdRef.current = threadId

        // Returning to a still-streaming session we stashed → restore it (with its
        // live progress), no refetch.
        const cached = inflightCacheRef.current.get(threadId)
        if (cached) {
            console.log(`[inflight-cache] HIT ${threadId} — restoring ${cached.messages.length} msgs, loading=${cached.loading} (no refetch)`)
            inflightCacheRef.current.delete(threadId)   // active again; re-stash on next leave
            dispatch({ type: "hydrate", runtime: cached })
            loadedSessionRef.current = threadId          // suppress the history fetch below
            onHistoryLoaded()                            // we already have messages; no skeleton
            return
        }

        console.log(`[inflight-cache] MISS ${threadId} — will fetch history. cached keys=[${[...inflightCacheRef.current.keys()].join(", ")}]`)
        // Fresh/settled session → clear and let the effect below fetch its history.
        dispatch({ type: "reset" })
        loadedSessionRef.current = null
    }, [threadId])

    // Request this session's history. Switching sessions reconnects the socket,
    // so this re-runs when the live socket comes up; we only stop re-requesting
    // once the history response for this session has actually arrived (the
    // receive handler sets loadedSessionRef), which avoids losing the request on
    // a socket that's about to close during a reconnect.
    useEffect(() => {
        if (!isConnected) return
        if (loadedSessionRef.current === threadId) return
        // serialize:false — never block behind an in-flight pipeline. This client
        // routes streamed chunks by session id and renders them itself, so it wants
        // whatever is persisted right now, not a snapshot delayed until completion.
        sendMessage(JSON.stringify({ type: "chat_history", session_id: threadId, serialize: false }))
    }, [threadId, isConnected, sendMessage])

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
            // console.log("Data", data)

            // Rate-limit / high-load notice: toast it. If a prompt was optimistically
            // in flight, this was its rejection — stop the spinner and drop the bubble.
            if (data.type === "rate_limited") {
                setToast(data.response ?? "You have hit the rate limit. Please retry shortly.")
                if (loadingRef.current) dispatch({ type: "promptRejected" })
                return
            }

            // Route pipeline chunks by session id. A chunk whose session isn't the
            // one on screen belongs to a stashed in-flight session: apply it to that
            // session's cache entry so its live progress is preserved for the user's
            // return. Its terminal "results" means it settled → drop the stash
            // (returning then reloads the completed conversation from the DB).
            const streamTypes = ["tool_status", "reasoning", "search_results", "web_source", "results", "compaction_request", "compaction_running", "compaction_done", "compaction_failed"]
            if (streamTypes.includes(data.type)) {
                if (data.session_id && data.session_id !== threadId) {
                    const sid: string = data.session_id
                    if (data.type === "results") inflightCacheRef.current.delete(sid)
                    else inflightCacheRef.current.set(sid, applyChunk(inflightCacheRef.current.get(sid) ?? emptyRuntime(), data))
                } else {
                    dispatch({ type: "chunk", data })
                }
                return
            }

            if (data.type === "chat_history") {
                // Backend returned a session's stored messages — render them.
                if (data.session_id && data.session_id !== threadId) return
                const messages: Message[] = (data.messages ?? []).map((m: { role: string; content: string; search_results?: Product[]; image_url?: string }) => ({
                    id: crypto.randomUUID(),
                    role: m.role === "assistant" ? "agent" : "user",
                    content: m.content,
                    products: m.search_results ?? undefined,
                    imageUrl: m.image_url ?? undefined,
                }))
                // Re-show any pending compaction (fresh load / different instance).
                // Server "compacting" maps to the client's "running" banner.
                const c = data.compaction
                const compaction: Compaction = c?.phase === "awaiting"
                    ? { phase: "awaiting", message: c.message, disclaimer: c.disclaimer }
                    : c?.phase === "compacting"
                        ? { phase: "running", message: c.message }
                        : { phase: "idle" }
                dispatch({ type: "hydrate", runtime: { ...emptyRuntime(), messages, loading: compaction.phase === "running", compaction } })
                // Mark loaded only now that the response has arrived, so the
                // request isn't lost on a socket that closed during reconnect.
                loadedSessionRef.current = data.session_id ?? threadId
                // History is in — swap the skeleton for the real messages.
                onHistoryLoaded()
            }
        } catch { }
    }, [messageCount])

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages, loading])

    // Auto-dismiss the rate-limit toast.
    useEffect(() => {
        if (!toast) return
        const id = setTimeout(() => setToast(null), 3500)
        return () => clearTimeout(id)
    }, [toast])

    const handleImageSelect = async (e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file || !file.type.startsWith("image/")) return
        const img = await fileToAttachedImage(file)
        setPendingImage(img)
        setDialogOpen(true)
        e.target.value = ""
    }

    // Pasting into the input: if the clipboard carries an image (e.g. a copied
    // product photo or a screenshot), route it through the same extraction flow
    // as an upload. Otherwise, keep the plain-text paste (strips formatting).
    const handlePaste = async (e: ClipboardEvent<HTMLDivElement>) => {
        const imageFile =
            Array.from(e.clipboardData.files).find(f => f.type.startsWith("image/")) ??
            Array.from(e.clipboardData.items)
                .find(it => it.kind === "file" && it.type.startsWith("image/"))
                ?.getAsFile() ??
            null
        if (imageFile) {
            e.preventDefault()
            const img = await fileToAttachedImage(imageFile)
            setPendingImage(img)
            setDialogOpen(true)
            return
        }
        // No image → plain-text paste.
        e.preventDefault()
        document.execCommand("insertText", false, e.clipboardData.getData("text/plain"))
    }

    const pickPhrase = () => LOADING_PHRASES[Math.floor(Math.random() * LOADING_PHRASES.length)]

    const handleExtractionDialogClose = () => {
        if (pendingImage) URL.revokeObjectURL(pendingImage.previewUrl)
        setPendingImage(null)
        setDialogOpen(false)
    }

    const handleSearchResultDialogClose = () => {
        dispatch({ type: "closeSearchDialog" })
    }

    const handleDialogConfirm = (
        fields: Record<string, string | string[]>,
        message: string,
        imageDataUrl: string,
    ) => {
        sendMessage(JSON.stringify({
            type: "run_with_fields",
            session_id: threadId,
            fields,
            ...(message ? { message } : {}),
            ...(pendingImage ? { image_base64: pendingImage.base64, image_mime: pendingImage.mimeType } : {}),
        }))
        dispatch({
            type: "send",
            message: { id: crypto.randomUUID(), role: "user", content: message, imageDataUrl },
            phrase: pickPhrase(),
        })
        if (pendingImage) URL.revokeObjectURL(pendingImage.previewUrl)
        setPendingImage(null)
        setDialogOpen(false)
    }

    const handleScanResult = (query: string) => {
        setScannerOpen(false)
        sendMessage(JSON.stringify({ type: "prompt", session_id: threadId, message: query }))
        dispatch({
            type: "send",
            message: { id: crypto.randomUUID(), role: "user", content: query },
            phrase: pickPhrase(),
        })
    }

    const handleSend = () => {
        // innerText preserves line breaks the user typed (textContent flattens
        // them). trim() only strips leading/trailing space, keeping internal
        // newlines intact so the prompt is sent and stored exactly as typed.
        const text = (inputRef.current?.innerText ?? "").trim()
        if (!text) return

        sendMessage(JSON.stringify({ type: "prompt", session_id: threadId, message: text }))
        dispatch({
            type: "send",
            message: { id: crypto.randomUUID(), role: "user", content: text },
            phrase: pickPhrase(),
        })

        if (inputRef.current) inputRef.current.innerText = ""
        setTextPresent(false)
    }

    const handleCompactConfirm = () => {
        sendMessage(JSON.stringify({ type: "compact_confirm", session_id: threadId }))
        dispatch({ type: "resumeTurn" })
    }

    const handleCompactDecline = () => {
        sendMessage(JSON.stringify({ type: "compact_decline", session_id: threadId }))
        dispatch({ type: "resumeTurn" })
    }


    const inputBox = (
        <div className={`w-full p-2 rounded-lg border shadow-sm ${isLight ? "border-black/10" : "border-white/10"}`}>
            {/* {disconnection Status Alert} */}

            <div className={`flex gap-x-2 items-end w-full`}>
                <div className="relative flex-1 min-w-0">
                    {!textPresent && (
                        <span className={`absolute left-0 top-0 inter-400 pointer-events-none ${isLight ? "text-black/40" : "text-white/40"}`}>
                            Is E101 halal?
                        </span>
                    )}
                    <div
                        ref={inputRef}
                        onInput={() => {
                            const t = (inputRef.current?.innerText ?? "").trim()
                            setTextPresent(t.length > 0)
                        }}
                        onPaste={handlePaste}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault()
                                if (canSend) handleSend()
                            }
                        }}
                        contentEditable={isConnected}
                        className={`focus:outline-none w-full inter-400 max-h-[200px] overflow-y-auto min-h-6 ${isLight ? "text-black/90" : "text-white/90"}`}
                    />
                </div>

                <input disabled={!isConnected || compactionBlocking} ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleImageSelect} />

                {/* scanner only for mobile application */}
                {/* <button
                    type="button"
                    onClick={() => !loading && setScannerOpen(true)}
                    aria-label="Scan QR or barcode"
                    className={`shrink-0 w-6 h-6 transition-colors ${loading ? "cursor-default opacity-30" : "cursor-pointer"} ${isLight ? "text-black/40 hover:text-black" : "text-white/40 hover:text-white/80"}`}
                >
                    <ScanIcon className="w-6 h-6 stroke-current" />
                </button> */}
                <button
                    type="button"
                    onClick={() => !loading && !compactionBlocking && fileInputRef.current?.click()}
                    aria-label="Upload image"
                    className={`shrink-0 w-6 h-6 transition-colors ${loading || compactionBlocking ? "cursor-default opacity-30" : "cursor-pointer"} ${isLight ? "text-black/40 hover:text-black" : "text-white/40 hover:text-white/80"}`}
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
                    onClick={() => toolCalls.length > 0 && dispatch({ type: "toggleDetails" })}
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
                    <motion.div onClick={() => dispatch({ type: "openSearchDialog" })} initial={{ opacity: 0 }} animate={{ opacity: [0.4, 0.8, 1] }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}
                        className={`w-max px-2 py-1 cursor-pointer flex gap-x-2 items-center rounded-xs border ${isLight ? "border-red-400/30" : "border-green-500/20"}`}>
                        <div className={`w-2 h-2 ${isLight ? "bg-red-400/30" : "bg-green-500/20"} rounded-full`}></div>
                        <p className={`text-xs font-mono ${isLight ? " text-black /50" : "text-white/50"}`}>See search progress</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    )

    // Shown while an existing session's history is being fetched — pulsing
    // placeholders for alternating user/agent messages.
    const messagesSkeleton = (
        <div className="flex-1 overflow-hidden">
            <div className="max-w-[80%] md:max-w-[60%] lg:max-w-[50%] mx-auto flex flex-col gap-y-6 pt-10 pb-4 px-4">
                {[0, 1, 2, 3].map((i) => {
                    const mine = i % 2 === 1
                    const bar = isLight ? "bg-black/8" : "bg-white/10"
                    const block = isLight ? "bg-black/5" : "bg-white/5"
                    return (
                        <div key={i} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                            {mine ? (
                                <div className={`h-10 w-1/2 rounded-2xl rounded-br-sm animate-pulse ${bar}`} />
                            ) : (
                                <div className="w-full flex flex-col gap-y-2">
                                    <div className={`h-3 w-3/4 rounded animate-pulse ${bar}`} />
                                    <div className={`h-3 w-5/6 rounded animate-pulse ${bar}`} />
                                    <div className={`h-24 w-full rounded-xl animate-pulse ${block}`} />
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>
        </div>
    )

    return (
        <div className={`w-full h-screen flex flex-col transition-colors duration-300 overflow-hidden ${isLight ? "bg-white scrollbar-thin-light" : "bg-black scrollbar-thin-dark"}`}>

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
                {/* Skeleton only when we truly have nothing to show yet. If messages
                    are already present (e.g. restored from the in-flight cache), show
                    them immediately regardless of a lingering historyLoading flag. */}
                {historyLoading && !hasMessages ? (
                    <motion.div
                        key="skeleton"
                        className="flex-1 flex flex-col overflow-hidden"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        {messagesSkeleton}
                    </motion.div>
                ) : !hasMessages ? (
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
                                <div className="rounded-sm inter-500 text-white text-xs bg-green-500/90 px-2 h-4 w-max">
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
                                                {msg.imageDataUrl ? (
                                                    <img
                                                        src={msg.imageDataUrl}
                                                        alt=""
                                                        className="w-36 h-36 rounded-2xl rounded-br-sm object-cover"
                                                    />
                                                ) : msg.imageUrl ? (
                                                    <img
                                                        src={msg.imageUrl}
                                                        alt=""
                                                        className="w-36 h-36 rounded-2xl rounded-br-sm object-cover"
                                                    />
                                                ) : null}
                                                {msg.content && (
                                                    <div className={`px-4 py-2.5 rounded-2xl rounded-br-sm leading-snug whitespace-pre-wrap wrap-break-words ${isLight ? "bg-black/10 text-black inter-400" : "bg-white/10 text-white inter-300"}`}>
                                                        {msg.content}
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <div className="flex flex-col gap-y-3 w-full">
                                                {msg.content && (
                                                    <div className={`leading-relaxed ${isLight ? "text-black/80 inter-400" : "text-white/80 inter-300"}`}>
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
                                                                        {product.verified === false ? (
                                                                            <span className="shrink-0 flex items-center gap-x-1.5 text-xs switzer-500 px-2.5 py-1 rounded-full text-amber-500 bg-amber-500/10 border border-amber-500/30">
                                                                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                                                                                Unverified
                                                                            </span>
                                                                        ) : (
                                                                            <span className={`shrink-0 flex items-center gap-x-1.5 text-xs switzer-500 px-2.5 py-1 rounded-full ${statusBadge(product.halal_status ?? "")}`}>
                                                                                <span className={`w-1.5 h-1.5 rounded-full ${statusDot(product.halal_status ?? "")}`} />
                                                                                {product.halal_status}
                                                                            </span>
                                                                        )}
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
                                                                    {product.verified === false && product.grounding && product.grounding.length > 0 && (
                                                                        <div className={`flex flex-col gap-y-2 pt-2 border-t ${isLight ? "border-black/8" : "border-white/8"}`}>
                                                                            <span className={`text-xs switzer-500 ${isLight ? "text-amber-600" : "text-amber-400/80"}`}>
                                                                                Unverified · sourced from web
                                                                            </span>
                                                                            {product.grounding.map((g, gi) => {
                                                                                const value = formatFieldValue(product[g.field as keyof Product])
                                                                                if (!value) return null
                                                                                // De-dupe citations by site so each source appears once.
                                                                                const sites = Array.from(new Map(g.citations.map(c => [hostOf(c.url), c])).values())
                                                                                return (
                                                                                    <div key={gi} className="flex items-center justify-between gap-x-3">
                                                                                        <p className="text-xs switzer-400 leading-snug min-w-0">
                                                                                            <span className={isLight ? "text-black/40" : "text-white/40"}>{FIELD_LABELS[g.field] ?? g.field}: </span>
                                                                                            <span className={isLight ? "text-black/80" : "text-white/80"}>{value}</span>
                                                                                        </p>
                                                                                        {sites.length > 0 && (
                                                                                            <div className={`inline-flex items-center gap-x-2 shrink-0 px-2 py-1 rounded-sm border ${isLight ? "border-black/10 bg-black/3" : "border-white/10 bg-white/5"}`}>
                                                                                                <span className={`text-xs inter-400 tracking-tighter ${isLight ? "text-black/45" : "text-white/45"}`}>{sites.length > 1 ? "Sources" : "Source"}</span>
                                                                                                <div className="flex items-center gap-x-0.2">
                                                                                                    {sites.map((c, ci) => (
                                                                                                        <a
                                                                                                            key={ci}
                                                                                                            href={c.url}
                                                                                                            target="_blank"
                                                                                                            rel="noopener noreferrer"
                                                                                                            onClick={(e) => e.stopPropagation()}
                                                                                                            title={c.title || hostOf(c.url)}
                                                                                                            className="block transition-transform hover:scale-110"
                                                                                                        >
                                                                                                            <img
                                                                                                                src={faviconOf(c.url)}
                                                                                                                alt=""
                                                                                                                loading="lazy"
                                                                                                                className="w-3.5 h-3.5 rounded-full object-cover bg-white"
                                                                                                            />
                                                                                                        </a>
                                                                                                    ))}
                                                                                                </div>
                                                                                            </div>
                                                                                        )}
                                                                                    </div>
                                                                                )
                                                                            })}
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

                                {loading && webSources.length > 0 && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 8 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className={`flex flex-col gap-y-2 rounded-xl p-3 border ${isLight ? "border-black/8 bg-black/2" : "border-white/8 bg-white/2"}`}
                                    >
                                        <span className={`text-xs switzer-500 ${isLight ? "text-black/50" : "text-white/50"}`}>
                                            Searching the web…
                                        </span>
                                        {webSources.map((s, i) => (
                                            <a
                                                key={s.url ?? i}
                                                href={s.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex flex-col gap-y-1 group"
                                            >
                                                <div className="flex items-center gap-x-2">
                                                    {s.favicon
                                                        ? <img src={s.favicon} alt="" className="w-4 h-4 rounded-sm shrink-0 object-contain" />
                                                        : <span className={`w-4 h-4 rounded-sm shrink-0 ${isLight ? "bg-black/10" : "bg-white/10"}`} />}
                                                    <span className={`text-xs switzer-500 truncate group-hover:underline ${isLight ? "text-black/70" : "text-white/70"}`}>
                                                        {s.title || hostOf(s.url)}
                                                    </span>
                                                </div>
                                                {s.highlights && s.highlights[0] && (
                                                    <p className={`text-xs switzer-400 line-clamp-2 pl-6 ${isLight ? "text-black/40" : "text-white/40"}`}>
                                                        {s.highlights[0]}
                                                    </p>
                                                )}
                                            </a>
                                        ))}
                                    </motion.div>
                                )}

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

            {/* Compaction: confirm modal (awaiting) and a slim banner (running). */}
            <AnimatePresence>
                {compaction.phase === "awaiting" && (
                    <CompactionDialog
                        key="compaction-dialog"
                        theme={theme}
                        message={compaction.message ?? "Your conversation has hit the token limit."}
                        disclaimer={compaction.disclaimer}
                        onConfirm={handleCompactConfirm}
                        onDecline={handleCompactDecline}
                    />
                )}
            </AnimatePresence>
            <AnimatePresence>
                {compaction.phase === "running" && (
                    <motion.div
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 12 }}
                        className="fixed bottom-6 left-1/2 -translate-x-1/2 z-70 px-4 py-2 rounded-lg bg-emerald-700 text-white text-sm switzer-500 shadow-lg max-w-[90%] text-center"
                    >
                        {compaction.message ?? "History is being compacted, please wait…"}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Rate-limit / high-load toast */}
            <AnimatePresence>
                {toast && (
                    <motion.div
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 12 }}
                        className="fixed bottom-6 left-1/2 -translate-x-1/2 z-70 px-4 py-2 rounded-lg bg-amber-600 text-white text-sm switzer-500 shadow-lg max-w-[90%] text-center"
                    >
                        {toast}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}