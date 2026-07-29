"use client"
import { useRef, useState, useEffect, useLayoutEffect, useReducer, type ChangeEvent, type ClipboardEvent } from "react"
import { useRouter, useParams } from "next/navigation"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"

import ImageIcon from "../../../icons/image_colored_icon.svg"
import StockPotIcon from "../../../icons/stockpot_icon.svg"
import CoffeeIcon from "../../../icons/coffee_icon.svg"
import CookieIcon from "../../../icons/cookie_icon.svg"
import HalalOneIcon from "../../../icons/halal_one_icon.svg"
import ArrowUpIcon from "../../../icons/arrow_up_icon.svg"
import RightPanelCloseIcon from "../../../icons/right_panel_close_icon.svg"
import RightPanelOpenIcon from "../../../icons/right_panel_open_icon.svg"
import InkPenIcon from "../../../icons/ink_pen_icon.svg"
import SearchIcon from "../../../icons/search_icon.svg"
import LogoutIcon from "../../../icons/logout_icon.svg"
import TrashIcon from "../../../icons/trash_icon.svg"

import { createClient } from "@/utils/supabase/client"
import useWebsocket from "@/hooks/useWebsocket"
import Image from "next/image"
import type { Product } from "@/types/product"
import { statusBadge, statusAccent, statusDot } from "@/utils/halalStatus"
import ProductDetailModal from "@/components/product/ProductDetailModal"
import Markdown from "@/components/markdown/Markdown"
import ImageExtractionDialog from "@/components/ImageExtractionDialog"
import SearchResultsDialog from "@/components/SearchResultsDialog"
import CompactionDialog from "@/components/CompactionDialog"

const fontThemes = { "light-tailwind": "text-black/50", "dark-tailwind": "text-black/80", "light-hex": "#00000080", "dark-hex": "#000000CC" }

// ---- backend message / streaming types (ported from HalalifyChat) ----
type AttachedImage = { previewUrl: string; base64: string; mimeType: string }

type Message = {
    id: string
    role: "user" | "agent"
    content: string
    products?: Product[]
    imageDataUrl?: string
    // Short-lived signed CDN URL for a stored image, returned on session reload.
    imageUrl?: string
}

type ToolCall = { tool: string; args: Record<string, unknown> }
type ReasoningContent = { node: string; reasoning: string }
type WebSource = { url: string; title?: string; favicon?: string; highlights?: string[] }
type Session = { session_id: string; title: string; description: string; created_at: string }

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
    // DB id of the persisted assistant message. Present on "results" so a client
    // that already loaded this answer via chat_history can drop the duplicate.
    message_id?: string
}

// Compaction handshake state for a session. "awaiting" shows the confirm modal;
// "running" shows a slim banner while the summary is generated. Kept inside
// Runtime so it stashes/restores on session switch exactly like streaming state.
type Compaction = {
    phase: "idle" | "awaiting" | "running"
    message?: string
    disclaimer?: string | null
}

const LOADING_PHRASES = ["Lock n Loaded", "Processing", "On it", "Right on it", "Firing it up", "Hold tight", "One sec", "Working on it", "Hang tight", "Let me check"]

// Human labels for the per-field grounding citations shown on web-result cards.
const FIELD_LABELS: Record<string, string> = {
    norm_name: "Name", companies: "Brand", halal_status: "Halal status", cert_bodies: "Certifier",
    cert_numbers: "Cert no.", category_l1: "Category", category_l2: "Subcategory", sold_in: "Sold in",
    marketplace: "Marketplace", barcodes: "Barcode", fda_numbers: "FDA no.", typical_uses: "Uses", health_info: "Health",
}

// The chat lives at /chat (new) and /chat/<session_id> (existing), so a reload
// restores the conversation the user was on. Session ids are uuids we generate;
// anything else in the slug is a hand-typed / stale URL and is treated as "new
// chat" rather than sent to the backend.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const isSessionId = (s: string | undefined): s is string => !!s && UUID_RE.test(s)

// Read the session id straight off the address bar. Used on popstate, where the
// router's params aren't re-delivered because we drive the URL ourselves.
const sessionIdFromPath = (): string | undefined => sessionIdFromSlug(window.location.pathname.split("/")[2])
const sessionIdFromSlug = (slug: string | undefined): string | undefined => (isSessionId(slug) ? slug : undefined)

// Point the address bar at a session WITHOUT a Next navigation. router.push
// would remount this page on every session switch, tearing down the long-lived
// socket and the in-flight cache; the native History API is supported by the App
// Router and keeps usePathname in sync. See:
// node_modules/next/dist/docs/01-app/02-guides/single-page-applications.md
const syncUrl = (sessionId: string | null, mode: "push" | "replace" = "push") => {
    const url = sessionId ? `/chat/${sessionId}` : "/chat"
    if (window.location.pathname === url) return
    if (mode === "push") window.history.pushState(null, "", url)
    else window.history.replaceState(null, "", url)
}

const hostOf = (url: string) => { try { return new URL(url).hostname.replace(/^www\./, "") } catch { return url } }
const faviconOf = (url: string) => { try { return `https://www.google.com/s2/favicons?sz=64&domain=${new URL(url).hostname}` } catch { return "" } }
const formatFieldValue = (value: unknown): string => {
    if (Array.isArray(value)) return value.filter(Boolean).join(", ")
    if (value === null || value === undefined || typeof value === "boolean") return ""
    return String(value)
}

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

// All per-session streaming state in one object, so a whole session can be moved
// as a unit between the on-screen view and the background cache of in-flight ones.
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
    messages: [], loading: false, statusMessage: null, loadingPhrase: "",
    intermediateSearchResults: null, toolCalls: [], reasoningContent: [],
    detailsOpen: false, webSources: [], searchDialogOpen: { showButton: false, showDialog: false },
    compaction: { phase: "idle" },
})

// Apply a single agent chunk to a runtime. Pure, so it drives both the on-screen
// session (via the reducer) and backgrounded ones (on their cache entry) identically.
const applyChunk = (rt: Runtime, data: StreamChunk): Runtime => {
    switch (data.type) {
        case "tool_status": {
            const toolCalls = data.tool && data.args !== undefined ? [...rt.toolCalls, { tool: data.tool, args: data.args }] : rt.toolCalls
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
            return { ...rt, intermediateSearchResults: { tool_name: data.tool ?? "", search_results: data.search_results ?? [] }, searchDialogOpen: { ...rt.searchDialogOpen, showButton: true } }
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
        case "results": {
            // The answer can reach us twice: once loaded from the DB by
            // chat_history, once pushed over pub/sub as the pipeline finishes.
            // Both carry the DB id, so the second one is dropped.
            const already = data.message_id !== undefined && rt.messages.some(m => m.id === data.message_id)
            const answer: Message = { id: data.message_id ?? crypto.randomUUID(), role: "agent", content: data.response ?? "", products: data.documents ?? [] }
            return {
                ...rt,
                messages: already ? rt.messages : [...rt.messages, answer],
                loading: false, statusMessage: null, toolCalls: [], reasoningContent: [],
                intermediateSearchResults: { tool_name: "", search_results: [] }, searchDialogOpen: { showButton: false, showDialog: false }, detailsOpen: false, webSources: [],
                compaction: { phase: "idle" },
            }
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
        case "reset": return emptyRuntime()
        case "hydrate": return action.runtime
        case "send": return { ...emptyRuntime(), messages: [...rt.messages, action.message], loading: true, loadingPhrase: action.phrase }
        case "chunk": return applyChunk(rt, action.data)
        case "promptRejected": {
            // Server rejected the just-sent prompt (rate/LLM cap): stop the spinner
            // and drop the optimistic user bubble so a retry is clean.
            const messages = rt.messages.length && rt.messages[rt.messages.length - 1].role === "user" ? rt.messages.slice(0, -1) : rt.messages
            return { ...emptyRuntime(), messages }
        }
        case "resumeTurn":
            // User answered the compaction prompt: close the modal and restart the
            // spinner while the held turn resumes (server confirms via its chunks).
            return { ...rt, loading: true, compaction: { phase: "idle" } }
        case "toggleDetails": return { ...rt, detailsOpen: !rt.detailsOpen }
        case "openSearchDialog": return { ...rt, searchDialogOpen: { ...rt.searchDialogOpen, showDialog: true } }
        case "closeSearchDialog": return { ...rt, searchDialogOpen: { ...rt.searchDialogOpen, showDialog: false } }
    }
}

// Bucket sessions by recency for the sidebar (Today / Yesterday / Last 7 Days / Older).
function groupSessions(sessions: Session[]): Record<string, Session[]> {
    const now = new Date()
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
    const day = 86400000
    const groups: Record<string, Session[]> = { "Today": [], "Yesterday": [], "Last 7 Days": [], "Older": [] }
    for (const s of sessions) {
        const t = new Date(s.created_at).getTime()
        if (t >= startOfToday) groups["Today"].push(s)
        else if (t >= startOfToday - day) groups["Yesterday"].push(s)
        else if (t >= startOfToday - 7 * day) groups["Last 7 Days"].push(s)
        else groups["Older"].push(s)
    }
    return groups
}

export default function Page() {
    const router = useRouter()
    const supabase = createClient()

    // ---- auth + profile ----
    const [authChecked, setAuthChecked] = useState<boolean>(false)
    const [profile, setProfile] = useState<{ name: string; email: string; avatarUrl: string }>({ name: "", email: "", avatarUrl: "" })
    const firstName = profile.name ? profile.name.split(" ")[0] : "there"

    useEffect(() => {
        supabase.auth.getSession().then(({ data: { session } }) => {
            if (!session) { router.push("/login"); return }
            const u = session.user
            const name = (u.user_metadata?.full_name as string) || (u.email ? u.email.split("@")[0] : "User")
            // Google sign-in populates avatar_url/picture on the Supabase user.
            const avatarUrl = (u.user_metadata?.avatar_url as string) || (u.user_metadata?.picture as string) || ""
            setProfile({ name, email: u.email ?? "", avatarUrl })
            setAuthChecked(true)
        })
    }, [])

    // ---- one long-lived socket, shared by the chat and the history cupboard ----
    const ws = useWebsocket(`${process.env.NEXT_PUBLIC_BACKEND_WS_URL}/ws`)
    const { isConnected, lastMessage, sendMessage, messageCount } = ws

    // ---- session routing ----
    // /chat/<session_id> deep-links (and survives a reload); /chat is a new chat.
    const params = useParams<{ slug?: string[] }>()
    const initialSessionId = sessionIdFromSlug(Array.isArray(params.slug) ? params.slug[0] : undefined)

    const [threadId, setThreadId] = useState<string>(() => initialSessionId ?? crypto.randomUUID())
    // Deep-linked into a session: start in the loading state so the skeleton shows
    // immediately and the landing screen never flashes before the history lands.
    const [historyLoading, setHistoryLoading] = useState<boolean>(() => initialSessionId !== undefined)
    // Read inside the [messageCount]-keyed receive effect, which would otherwise
    // close over a stale value.
    const historyLoadingRef = useRef<boolean>(initialSessionId !== undefined)
    useEffect(() => { historyLoadingRef.current = historyLoading }, [historyLoading])

    // ---- sidebar (their existing UI state) ----
    const [isChatSessionOpen, setIsChatSessionOpen] = useState<boolean>(false)
    const [isTextPresentSessionSearch, setIsTextPresentSessionSearch] = useState<boolean>(false)
    const [sessions, setSessions] = useState<Session[]>([])
    const [sessionQuery, setSessionQuery] = useState<string>("")
    const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
    const sessionSearchRef = useRef<HTMLDivElement | null>(null)

    // ---- composer + view state ----
    const inputRef = useRef<HTMLDivElement | null>(null)
    const fileInputRef = useRef<HTMLInputElement | null>(null)
    const messagesEndRef = useRef<HTMLDivElement | null>(null)
    const [isTextPresent, setIsTextPresent] = useState<boolean>(false)
    // Composer shape: oval (single line) → rectangle once the text wraps. Stays a
    // rectangle until the input is fully empty again, then reverts to oval.
    const [inputExpanded, setInputExpanded] = useState<boolean>(false)
    const [pendingImage, setPendingImage] = useState<AttachedImage | null>(null)
    const [dialogOpen, setDialogOpen] = useState<boolean>(false)
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
    const [toast, setToast] = useState<string | null>(null)
    // Shown (after a short grace period) whenever the socket is down, so no
    // message — prompt, chip, or image — can reach a disconnected backend.
    const [showDisconnected, setShowDisconnected] = useState<boolean>(false)
    const isConnectedRef = useRef(isConnected)

    // All per-session streaming state in one reducer, so a whole session can be
    // stashed/restored (and background sessions advanced) as a single unit.
    const [runtime, dispatch] = useReducer(runtimeReducer, undefined, emptyRuntime)
    const { messages, loading, statusMessage, loadingPhrase, intermediateSearchResults, toolCalls, reasoningContent, detailsOpen, webSources, searchDialogOpen, compaction } = runtime
    const hasMessages = messages.length > 0
    // Block sending while a compaction decision is pending or running — the backend
    // rejects it anyway, so gate it here for a clean UX.
    const compactionBlocking = compaction.phase !== "idle"
    const canSend = isTextPresent && !loading && isConnected && !compactionBlocking

    // Tracks the session whose history we've already requested (avoids re-fetch loops).
    const loadedSessionRef = useRef<string | null>(null)
    // Cache of sessions with an in-flight response ONLY. Leaving a streaming session
    // stashes it so its stream survives the switch; returning restores it without a
    // refetch. Evicted on completion, so it never fills with settled sessions.
    const inflightCacheRef = useRef<Map<string, Runtime>>(new Map())
    const prevThreadIdRef = useRef<string | null>(null)
    const runtimeRef = useRef(runtime)
    const loadingRef = useRef(false)

    useEffect(() => { runtimeRef.current = runtime; loadingRef.current = runtime.loading }, [runtime])

    // On session switch: stash an outgoing streaming session, then restore an
    // incoming stashed one (no refetch) or clear the view so history is fetched.
    useEffect(() => {
        const prev = prevThreadIdRef.current
        // Stash if streaming OR mid-compaction (awaiting a decision / running), so
        // the modal/banner survives the switch just like live stream progress.
        if (prev && prev !== threadId && (loadingRef.current || runtimeRef.current.compaction.phase !== "idle")) {
            inflightCacheRef.current.set(prev, runtimeRef.current)
        }
        prevThreadIdRef.current = threadId

        const cached = inflightCacheRef.current.get(threadId)
        if (cached) {
            inflightCacheRef.current.delete(threadId)      // active again; re-stash on next leave
            dispatch({ type: "hydrate", runtime: cached })
            loadedSessionRef.current = threadId            // suppress the history fetch below
            setHistoryLoading(false)                       // we already have messages; no skeleton
            return
        }
        dispatch({ type: "reset" })
        loadedSessionRef.current = null
    }, [threadId])

    // Request this session's history once the socket is up (serialize:false — this
    // client routes streamed chunks itself, so it wants whatever is persisted now).
    useEffect(() => {
        if (!isConnected) return
        if (loadedSessionRef.current === threadId) return
        sendMessage(JSON.stringify({ type: "chat_history", session_id: threadId, serialize: false }))
    }, [threadId, isConnected, sendMessage])

    // Back/forward between sessions. We drive the URL with the History API, so the
    // router won't re-render us on these — read the id off the path ourselves.
    useEffect(() => {
        const onPopState = () => {
            const id = sessionIdFromPath()
            setHistoryLoading(id !== undefined)
            setThreadId(id ?? crypto.randomUUID())
        }
        window.addEventListener("popstate", onPopState)
        return () => window.removeEventListener("popstate", onPopState)
    }, [])

    // Ask for the session list whenever the cupboard opens.
    useEffect(() => {
        if (isChatSessionOpen) sendMessage(JSON.stringify({ type: "chat_sessions" }))
        else setConfirmDeleteId(null)
    }, [isChatSessionOpen, sendMessage])

    // Ctrl/Cmd+K opens the cupboard and focuses the session search.
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
                e.preventDefault()
                setIsChatSessionOpen(true)
                setTimeout(() => sessionSearchRef.current?.focus(), 100)
            }
        }
        window.addEventListener("keydown", onKey)
        return () => window.removeEventListener("keydown", onKey)
    }, [])

    // Single websocket receive handler for every message type.
    useEffect(() => {
        if (!lastMessage) return
        try {
            const data = JSON.parse(lastMessage)

            // Rate-limit / high-load notice: toast it. If a prompt was optimistically
            // in flight, this was its rejection — stop the spinner and drop the bubble.
            if (data.type === "rate_limited") {
                setToast(data.response ?? "You have hit the rate limit. Please retry shortly.")
                if (loadingRef.current) dispatch({ type: "promptRejected" })
                return
            }

            // Route pipeline chunks by session id. A chunk for a session that isn't on
            // screen belongs to a stashed in-flight one: apply it to that cache entry so
            // its progress survives. Its terminal "results" settles it → drop the stash.
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
                if (data.session_id && data.session_id !== threadId) return
                // Keep the DB id: a "results" chunk for an answer already loaded here
                // carries the same id, which is how the duplicate gets dropped.
                const msgs: Message[] = (data.messages ?? []).map((m: { id?: string; role: string; content: string; search_results?: Product[]; image_url?: string }) => ({
                    id: m.id ?? crypto.randomUUID(),
                    role: m.role === "assistant" ? "agent" : "user",
                    content: m.content,
                    products: m.search_results ?? undefined,
                    imageUrl: m.image_url ?? undefined,
                }))
                // Asked for a session the backend has nothing for: it was deleted, it
                // belongs to another user (get_messages is ownership-scoped and
                // returns empty), or the id was hand-typed. Drop to a fresh chat
                // rather than strand the user on a thread whose id they don't own.
                // Guarded on historyLoadingRef so this only fires for a deep link or
                // an explicit session pick — a brand-new local chat also gets an
                // empty history back, and must not be recycled into another new id.
                if (historyLoadingRef.current && msgs.length === 0) {
                    setHistoryLoading(false)
                    setThreadId(crypto.randomUUID())
                    syncUrl(null, "replace")
                    return
                }

                // Re-show any pending compaction (fresh load / different instance).
                // Server "compacting" maps to the client's "running" banner.
                const c = data.compaction
                const compaction: Compaction = c?.phase === "awaiting"
                    ? { phase: "awaiting", message: c.message, disclaimer: c.disclaimer }
                    : c?.phase === "compacting"
                        ? { phase: "running", message: c.message }
                        : { phase: "idle" }
                // A pipeline is still running for this session somewhere in the
                // fleet (reloaded mid-answer): keep the spinner up. The answer
                // arrives on its own over pub/sub — no polling needed.
                const stillRunning = data.inflight === true || compaction.phase === "running"
                dispatch({
                    type: "hydrate",
                    runtime: { ...emptyRuntime(), messages: msgs, loading: stillRunning, loadingPhrase: stillRunning ? pickPhrase() : "", compaction },
                })
                loadedSessionRef.current = data.session_id ?? threadId
                setHistoryLoading(false)
                return
            }

            if (data.type === "chat_sessions") {
                setSessions(data.sessions ?? [])
                return
            }

            if (data.type === "delete_session" && data.status === "acknowledged") {
                setSessions(prev => prev.filter(s => s.session_id !== data.session_id))
                setToast("Session deleted")
                // Deleted the open chat → start a fresh thread (its history is gone).
                if (data.session_id === threadId) { setHistoryLoading(false); setThreadId(crypto.randomUUID()); syncUrl(null, "replace") }
                return
            }
        } catch { }
    }, [messageCount])

    // Auto-scroll to the latest message; auto-dismiss the toast.
    useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages, loading])
    useEffect(() => { if (!toast) return; const id = setTimeout(() => setToast(null), 3500); return () => clearTimeout(id) }, [toast])

    // Surface a persistent "connection lost" banner while the socket is down. The
    // backend can't notify over a closed socket, so we detect it client-side via
    // isConnected. A 3s grace avoids flashing on brief reconnects.
    useEffect(() => { isConnectedRef.current = isConnected }, [isConnected])
    useEffect(() => {
        if (isConnected) { setShowDisconnected(false); return }
        const id = setTimeout(() => { if (!isConnectedRef.current) setShowDisconnected(true) }, 3000)
        return () => clearTimeout(id)
    }, [isConnected])

    // ---- session actions ----
    // A new chat stays at /chat until its first prompt: the session row only exists
    // once the backend persists that message, so publishing the id sooner would put
    // a URL in the user's history that resolves to nothing.
    const handleNewChat = () => { setHistoryLoading(false); setThreadId(crypto.randomUUID()); syncUrl(null); setIsChatSessionOpen(false) }
    const handleSelectSession = (id: string) => { if (id === threadId) { setIsChatSessionOpen(false); return } setHistoryLoading(true); setThreadId(id); syncUrl(id); setIsChatSessionOpen(false) }
    // Dismissing the cupboard without picking a session (backdrop / X) resets the
    // search so it reopens empty. Selecting a session keeps the filter — the
    // contentEditable node is uncontrolled, so its text is cleared directly here.
    const dismissSessions = () => {
        setSessionQuery("")
        setIsTextPresentSessionSearch(false)
        if (sessionSearchRef.current) sessionSearchRef.current.innerText = ""
        setIsChatSessionOpen(false)
    }
    const handleDeleteSession = (id: string) => { sendMessage(JSON.stringify({ type: "delete_session", session_id: id })); setConfirmDeleteId(null) }
    const handleSignOut = async () => { await supabase.auth.signOut(); router.push("/login"); router.refresh() }

    // ---- composer actions (ported) ----
    const pickPhrase = () => LOADING_PHRASES[Math.floor(Math.random() * LOADING_PHRASES.length)]

    // Track text presence and grow the composer into a rectangle once the text
    // wraps past one line. It stays a rectangle until the input is fully empty.
    const handleInputChange = () => {
        const el = inputRef.current
        const hasChar = ((el?.innerText ?? "").replace(/\n/g, "")).length > 0
        setIsTextPresent(hasChar)
        if (!hasChar) { setInputExpanded(false); return }
        if (el && el.scrollHeight > 40) setInputExpanded(true)
    }

    const handleSend = () => {
        if (!isConnected || compactionBlocking) return
        const text = (inputRef.current?.innerText ?? "").trim()
        if (!text) return
        sendMessage(JSON.stringify({ type: "prompt", session_id: threadId, message: text }))
        // First prompt of a new chat: the session now exists server-side, so commit
        // its id to the URL (replace, not push — /chat and /chat/<id> are the same
        // conversation, and Back should leave the chat, not empty it).
        syncUrl(threadId, "replace")
        dispatch({ type: "send", message: { id: crypto.randomUUID(), role: "user", content: text }, phrase: pickPhrase() })
        if (inputRef.current) inputRef.current.innerText = ""
        setIsTextPresent(false)
        setInputExpanded(false)
    }

    const handleCompactConfirm = () => {
        sendMessage(JSON.stringify({ type: "compact_confirm", session_id: threadId }))
        dispatch({ type: "resumeTurn" })
    }

    const handleCompactDecline = () => {
        sendMessage(JSON.stringify({ type: "compact_decline", session_id: threadId }))
        dispatch({ type: "resumeTurn" })
    }

    // Send a starter-chip prompt without touching the composer.
    const sendChipPrompt = (text: string) => {
        if (!text.trim() || loading || !isConnected || compactionBlocking) return
        sendMessage(JSON.stringify({ type: "prompt", session_id: threadId, message: text }))
        syncUrl(threadId, "replace")
        dispatch({ type: "send", message: { id: crypto.randomUUID(), role: "user", content: text }, phrase: pickPhrase() })
    }

    const handleImageSelect = async (e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file || !file.type.startsWith("image/")) return
        setPendingImage(await fileToAttachedImage(file))
        setDialogOpen(true)
        e.target.value = ""
    }

    // Pasting an image (copied photo / screenshot) routes through the same
    // extraction flow as an upload; otherwise keep a plain-text paste.
    const handlePaste = async (e: ClipboardEvent<HTMLDivElement>) => {
        const imageFile =
            Array.from(e.clipboardData.files).find(f => f.type.startsWith("image/")) ??
            Array.from(e.clipboardData.items).find(it => it.kind === "file" && it.type.startsWith("image/"))?.getAsFile() ?? null
        if (imageFile) {
            e.preventDefault()
            setPendingImage(await fileToAttachedImage(imageFile))
            setDialogOpen(true)
            return
        }
        e.preventDefault()
        document.execCommand("insertText", false, e.clipboardData.getData("text/plain"))
    }

    const handleExtractionDialogClose = () => { if (pendingImage) URL.revokeObjectURL(pendingImage.previewUrl); setPendingImage(null); setDialogOpen(false) }

    const handleDialogConfirm = (fields: Record<string, string | string[]>, message: string, imageDataUrl: string) => {
        if (!isConnected) return
        sendMessage(JSON.stringify({
            type: "run_with_fields",
            session_id: threadId,
            fields,
            ...(message ? { message } : {}),
            ...(pendingImage ? { image_base64: pendingImage.base64, image_mime: pendingImage.mimeType } : {}),
        }))
        syncUrl(threadId, "replace")
        dispatch({ type: "send", message: { id: crypto.randomUUID(), role: "user", content: message, imageDataUrl }, phrase: pickPhrase() })
        if (pendingImage) URL.revokeObjectURL(pendingImage.previewUrl)
        setPendingImage(null)
        setDialogOpen(false)
    }

    const groupedSessions = groupSessions(
        sessions.filter(s => {
            const q = sessionQuery.trim().toLowerCase()
            if (!q) return true
            return (s.title ?? "").toLowerCase().includes(q) || (s.description ?? "").toLowerCase().includes(q)
        })
    )

    // ---- the composer pill (their design, wired) ----
    const inputBox = (
        <div id="chat-content" className={`relative bg-white shadow-[0_0_15px_-3px_rgba(0,0,0,0.1),0_0_6px_-4px_rgba(0,0,0,0.1)] flex gap-x-2 min-h-[48px] py-2 px-4 transition-all duration-200 ${inputExpanded ? "rounded-[20px] items-end" : "rounded-full items-center"}`}>
            <input disabled={!isConnected || compactionBlocking} ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleImageSelect} />
            <motion.div whileHover={{ color: isConnected && !compactionBlocking ? fontThemes["dark-hex"] : undefined }} onClick={() => isConnected && !loading && !compactionBlocking && fileInputRef.current?.click()} id="upload-image-button" className={`${fontThemes["light-tailwind"]} ${isConnected && !compactionBlocking ? "cursor-pointer" : "opacity-40 cursor-default"}`}>
                <ImageIcon className={`fill-current w-5.5 h-5.5`} />
            </motion.div>

            <div id="chat-input" ref={inputRef}
                contentEditable={isConnected && !compactionBlocking}
                onInput={handleInputChange}
                onPaste={handlePaste}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canSend) handleSend() } }}
                className="flex-1 max-h-[120px] scrollbar-none overflow-y-auto focus:outline-none google-sans-flex-400 text-[19px] text-[#1F1F1F] tracking-tight">
            </div>
            {!isTextPresent && (
                <span id="chat-input-placeholder" className={`absolute top-2.5 left-11.5 pointer-events-none text-[19px] google-sans-flex-400 text-[#1F1F1F]/60 tracking-tight`}>Is Haribo halal?</span>
            )}

            <motion.div whileHover={{ scale: canSend ? 1.05 : 1 }} onClick={() => canSend && handleSend()} id="send-prompt-button" className={`cursor-pointer rounded-full p-1.5 ${canSend ? "bg-teal-800" : "bg-teal-800/50 cursor-default"}`}>
                <ArrowUpIcon className="w-4.5 h-4.5" />
            </motion.div>
        </div>
    )

    // ---- live "thinking" indicator (full: status + tool-call & reasoning dropdowns + search progress) ----
    const loadingIndicator = (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-y-1.5">
            {/* Shimmer bar */}
            <div className="relative h-0.5 w-full overflow-hidden rounded-full bg-teal-800/10">
                <motion.div className="absolute inset-y-0" style={{ width: "55%", background: "linear-gradient(90deg, transparent, rgba(19,78,74,0.45), transparent)" }} animate={{ x: ["-100%", "280%"] }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }} />
            </div>

            {/* Status row */}
            {statusMessage ? (
                <button type="button" onClick={() => toolCalls.length > 0 && dispatch({ type: "toggleDetails" })} className={`flex items-center gap-x-1.5 text-left ${toolCalls.length > 0 ? "cursor-pointer" : "cursor-default"}`}>
                    <motion.p key={statusMessage} initial={{ opacity: 0 }} animate={{ opacity: [0.4, 0.8, 0.4] }} transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }} className="google-sans-flex-400 text-sm text-[#1F1F1F]/45">
                        {statusMessage}
                    </motion.p>
                    {toolCalls.length > 0 && (
                        <motion.svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-[#1F1F1F]/30" animate={{ rotate: detailsOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
                            <polyline points="6 9 12 15 18 9" />
                        </motion.svg>
                    )}
                </button>
            ) : (
                <div className="flex items-center">
                    <p className="google-sans-flex-400 text-sm tracking-tight text-[#1F1F1F]/35">{loadingPhrase}</p>
                    <motion.svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="ml-2 shrink-0 text-[#1F1F1F]/30" animate={{ x: [6, 0, -6], opacity: [0, 1, 0] }} transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}>
                        <polyline points="9 18 15 12 9 6" />
                    </motion.svg>
                </div>
            )}

            {/* Tool-call + reasoning dropdown */}
            <AnimatePresence>
                {detailsOpen && (
                    <motion.div className="flex gap-x-4 bg-teal-800/4 border border-teal-800/8 rounded-lg max-h-50 overflow-y-auto p-3">
                        {toolCalls.length > 0 && (
                            <div className="flex flex-col shrink-0 min-w-1/2 gap-y-2">
                                <strong className="mb-1.5 text-sm font-mono text-[#1F1F1F]/50">Tool calls</strong>
                                <div className="w-full flex justify-center mb-2.5"><div className="w-[98%] border-t border-teal-800/10" /></div>
                                {toolCalls.map((tc, i) => (
                                    <div key={i} className="flex flex-col gap-y-1.5">
                                        <p className="text-xs font-mono text-[#1F1F1F]/50">{tc.tool}</p>
                                        <pre className="text-xs font-mono overflow-x-auto whitespace-pre-wrap break-all leading-relaxed text-[#1F1F1F]/35">{JSON.stringify(tc.args, null, 2)}</pre>
                                    </div>
                                ))}
                            </div>
                        )}
                        {reasoningContent.length > 0 && (
                            <div className="flex flex-col gap-y-2">
                                <strong className="mb-1.5 text-sm font-mono text-[#1F1F1F]/50">Graph Execution</strong>
                                <div className="w-full flex justify-center mb-2.5"><div className="w-[98%] border-t border-teal-800/10" /></div>
                                {reasoningContent.map((r, i) => (
                                    <div className={`flex flex-col gap-y-2 ${i === reasoningContent.length - 1 ? "pb-3" : ""}`} key={i}>
                                        <div className="p-1 rounded-xs border border-teal-800/20 w-max"><p className="text-xs font-mono text-[#1F1F1F]/50">{r.node}</p></div>
                                        <p className="text-xs font-mono text-[#1F1F1F]/50">{r.reasoning}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Search-progress button */}
            <AnimatePresence>
                {searchDialogOpen.showButton && (
                    <motion.div onClick={() => dispatch({ type: "openSearchDialog" })} initial={{ opacity: 0 }} animate={{ opacity: [0.4, 0.8, 1] }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} className="w-max px-2 py-1 cursor-pointer flex gap-x-2 items-center rounded-xs border border-teal-800/20">
                        <div className="w-2 h-2 bg-teal-800/30 rounded-full"></div>
                        <p className="text-xs font-mono text-[#1F1F1F]/50">See search progress</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    )

    // Skeleton while an existing session's history is being fetched.
    const messagesSkeleton = (
        <div className="w-[90%] md:w-[75%] lg:w-[45%] mx-auto flex flex-col gap-y-6 pt-6">
            {[0, 1, 2, 3].map((i) => (
                <div key={i} className={`flex ${i % 2 === 1 ? "justify-end" : "justify-start"}`}>
                    {i % 2 === 1 ? (
                        <div className="h-10 w-1/2 rounded-2xl rounded-br-sm animate-pulse bg-teal-800/8" />
                    ) : (
                        <div className="w-full flex flex-col gap-y-2">
                            <div className="h-3 w-3/4 rounded animate-pulse bg-teal-800/8" />
                            <div className="h-3 w-5/6 rounded animate-pulse bg-teal-800/8" />
                            <div className="h-24 w-full rounded-xl animate-pulse bg-teal-800/5" />
                        </div>
                    )}
                </div>
            ))}
        </div>
    )

    if (!authChecked) return <div className="w-full min-h-dvh h-dvh" />

    return (
        <div className="w-full min-h-dvh h-dvh flex flex-col bg-gray-100/10 relative overflow-x-hidden">
            {/* Persistent connection-lost banner — stays until the socket restores. */}
            <AnimatePresence>
                {showDisconnected && (
                    <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} id="connection-alert" className="fixed top-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-x-2 px-4 py-1.5 rounded-full bg-red-500 shadow-lg">
                        <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
                        <p className="google-sans-flex-500 text-sm text-white tracking-tight">Connection lost — trying to reconnect…</p>
                    </motion.div>
                )}
            </AnimatePresence>
            {/* Backdrop — click outside the open cupboard to close it. */}
            <AnimatePresence>
                {isChatSessionOpen && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={dismissSessions} className="fixed inset-0 z-9 bg-black/10" />
                )}
            </AnimatePresence>
            <motion.div initial={{ x: "-100%" }} animate={{ x: isChatSessionOpen ? "0%" : "-100%" }} transition={{ duration: 0.4, ease: "linear" }} id="chat-history-cupboard" className="h-full absolute top-0 z-10">
                <div className="w-80 h-full bg-linear-to-b/hsl from-[#fbfffe] to-[#f6fffe] border-r border-teal-800/5 flex flex-col gap-y-2 p-4">
                    <div id="sidepanel-control" className="w-full flex items-center">
                        <div id="brand-logo" className="text-teal-800 flex">
                            <Image src="/images/halal_one_logo_pic.png" alt="halal_one_logo" width={120} height={20} />
                        </div>
                        <div onClick={dismissSessions} className="text-teal-800 ml-auto cursor-pointer">
                            <RightPanelCloseIcon className="w-6 h-6 fill-current" />
                        </div>
                    </div>
                    {/* new chat → fresh thread id (change wires this to the backend) */}
                    <motion.div onClick={handleNewChat} id="new-chat-button" whileTap={{ scale: 0.99 }} transition={{ duration: 0.2, ease: 'easeInOut' }} className="mt-[50%] w-full text-white px-4 py-2 rounded-lg bg-[#191919] flex gap-x-2 justify-center items-center cursor-pointer">
                        <InkPenIcon className="w-4.5 h-4.5 fill-current" />
                        <p className="google-sans-flex-500 text-[15px] tracking-tight">New Chat</p>
                    </motion.div>

                    <motion.div id="search-chat-sessions" className="border border-[#1f1f1f]/10 rounded-lg px-4 py-2 flex gap-x-2 items-center relative w-full bg-white inset-shadow-sm">
                        <div className="">
                            <SearchIcon className="w-4.5 h-4.5" />
                        </div>
                        {/* filters the loaded session list by title/description */}
                        <div
                            ref={sessionSearchRef}
                            contentEditable
                            onInput={(e) => {
                                const t = (e.currentTarget.innerText ?? "").trim();
                                setIsTextPresentSessionSearch(t.length > 0);
                                setSessionQuery(t);
                            }}
                            className="scrollbar-none flex-1 min-w-0 focus:outline-none google-sans-flex-400 text-sm text-[#1f1f1f]/90 overflow-x-auto whitespace-nowrap"
                        ></div>
                        {!isTextPresentSessionSearch && (
                            <span id="search-sessions-placeholder" className="absolute top-[9px] left-[41px] google-sans-flex-400 text-sm text-[#1f1f1f]/60">Search</span>
                        )}
                        <span className="google-sans-flex-400 text-sm text-[#115e59] tracking-tighter">Ct+k</span>
                    </motion.div>

                    <div id="chat-sessions" className="border-t border-teal-800/5 mt-4 flex-1 overflow-y-auto">
                        {/* Empty state — no past sessions yet. The prompt fires straight to the backend. */}
                        {sessions.length === 0 && (
                            <div className="flex flex-col items-center gap-y-3 mt-12 px-2 text-center">
                                <TrashIcon className="w-20 h-20 fill-current text-teal-800/30" />
                                <p className="google-sans-flex-500 text-sm text-[#1f1f1f]/70">No sessions yet. <br />
                                    <span className="google-sans-flex-500 text-sm text-[#1f1f1f]/70">Start your first session with Halalify, now!</span></p>
                                <motion.div
                                    onClick={() => { sendChipPrompt("Is Coca-Cola halal?"); setIsChatSessionOpen(false) }}
                                    whileTap={{ scale: isConnected ? 0.98 : 1 }}
                                    whileHover={{ scale: isConnected ? 1.02 : 1 }}
                                    transition={{ duration: 0.2, ease: "linear" }}
                                    className={`shadow-sm rounded-full px-4 py-2 bg-white border border-teal-800/8 ${isConnected ? "cursor-pointer" : "opacity-50 cursor-default"}`}
                                >
                                    <p className="google-sans-flex-500 text-sm text-teal-800 tracking-tight">Is Coca-Cola halal?</p>
                                </motion.div>
                            </div>
                        )}
                        {Object.entries(groupedSessions).map(([key, value]) => value.length === 0 ? null : (
                            <div className="mt-4 overflow-hidden" key={key}>
                                <p className="google-sans-flex-400 text-xs tracking-tight text-[#1F1F1F]/60">{key}</p>
                                {value.map(item => (
                                    <motion.div
                                        key={item.session_id}
                                        whileTap={{ scale: 0.99 }}
                                        whileHover={{ scale: 1.01 }}
                                        transition={{ duration: 0.3, ease: 'linear' }}
                                        onClick={() => handleSelectSession(item.session_id)}
                                        className={`group my-3 w-full flex items-center gap-x-2 cursor-pointer ${item.session_id === threadId ? "opacity-100" : ""}`}
                                    >
                                        <p className={`google-sans-flex-400 truncate tracking-tight text-sm flex-1 min-w-0 ${item.session_id === threadId ? "text-teal-800" : "text-[#000000]"}`}>
                                            {item.description || item.title}
                                        </p>
                                        {/* delete with inline confirm (✓ / ✗), revealed on hover */}
                                        {confirmDeleteId === item.session_id ? (
                                            <div className="shrink-0 flex items-center gap-x-1">
                                                <button onClick={(e) => { e.stopPropagation(); handleDeleteSession(item.session_id) }} className="text-red-500 cursor-pointer">
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                                                </button>
                                                <button onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(null) }} className="text-[#1f1f1f]/40 cursor-pointer">
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                                                </button>
                                            </div>
                                        ) : (
                                            <button onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(item.session_id) }} className="shrink-0 text-[#1f1f1f]/30 opacity-0 group-hover:opacity-100 hover:text-red-500 transition-opacity cursor-pointer">
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /><path d="M10 11v6M14 11v6" /><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" /></svg>
                                            </button>
                                        )}
                                    </motion.div>
                                ))}
                            </div>
                        ))}
                    </div>
                    <motion.div whileTap={{ scale: 0.99 }} onClick={handleSignOut} id="sign-out-button" className="bg-[#f8f8f8] hover:bg-[#ffffff] mt-auto px-4 py-2 border cursor-pointer border-[#1f1f1f]/5 rounded-lg">
                        <div className="flex gap-x-2 items-center">
                            {/* Google avatar if available, else an initial in a brand circle */}
                            {profile.avatarUrl ? (
                                <div className="rounded-full border border-[#1f1f1f]/10 w-7 h-7 bg-cover bg-center shrink-0" style={{ backgroundImage: `url(${profile.avatarUrl})` }} />
                            ) : (
                                <div className="rounded-full w-7 h-7 bg-teal-800 flex items-center justify-center shrink-0">
                                    <span className="google-sans-flex-600 text-xs text-white">{(profile.name || "U").charAt(0).toUpperCase()}</span>
                                </div>
                            )}
                            <div id="profile-details-box" className="flex flex-col min-w-0">
                                <p className="google-sans-flex-500 text-xs tracking-tight text-[#1f1f1f] truncate">{profile.name || "User"}</p>
                                <p className="google-sans-flex-400 text-xs tracking-tight text-[#1f1f1f]/60 truncate">{profile.email}</p>
                            </div>
                            <LogoutIcon className="ml-auto w-6 h-6 fill-current text-[#1f1f1f]/70" />
                        </div>
                    </motion.div>
                </div>
            </motion.div>
            <div id="sidebar-line" className="hidden md:block absolute h-full w-px bg-[#1f1f1f]/10 left-14"></div>
            <div id="top-options" className="py-2 px-3 w-full flex items-center">
                <div id="sidebar-handles" className="w-max text-teal-800 flex items-center gap-x-2">
                    <motion.div onClick={() => { setIsChatSessionOpen(true) }} className="cursor-pointer">
                        <RightPanelOpenIcon className="w-6 h-6 fill-current" />
                    </motion.div>
                    {/* Back to the landing page */}
                    <Link href="/" id="home-button" className="ml-6 flex items-center gap-x-1.5 border border-teal-800/10 hover:bg-teal-800/5 transition-colors px-3 py-1 rounded-md">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><path d="M9 22V12h6v10" /></svg>
                        <p className="google-sans-flex-500 text-[13px] tracking-tight">Home</p>
                    </Link>
                </div>
                <div id="brand-logo" className="ml-auto text-teal-800 border border-teal-800/5 flex w-max px-4 py-1 rounded-md">
                    {/* <HalalOneIcon className="fill-current" />
                    <p className={`dm-sans-700 tracking-tighter`}>HalalOne</p> */}
                    <Image src="/images/halal_one_logo_pic.png" alt="halal_one_logo" width={100} height={5} />
                </div>
            </div>

            {/* ---- chat column: skeleton / landing / conversation ---- */}
            {historyLoading && !hasMessages ? (
                <div id="chat-column" className="flex-1 overflow-y-auto p-2">
                    {messagesSkeleton}
                </div>
            ) : !hasMessages ? (
                <div id="chat-column" className="flex flex-col justify-center-safe items-center-safe flex-1 p-2 mb-8 relative">
                    <div className="h-full relative flex flex-col justify-center-safe items-center-safe">
                        <motion.div initial={{ rotate: 0 }} animate={{ rotate: 360 }} transition={{ duration: 10, ease: "linear", repeat: Infinity, repeatType: "loop" }}
                            className="absolute w-80 h-80 md:w-100 md:h-100 blur-2xl">
                            <div className="w-full h-full bg-radial from-teal-200/10 via-teal-400/10 to-teal-600/10 rounded-[60%_40%_30%_70%/60%_30%_70%_40%]"></div>
                        </motion.div>
                        <p className="whitespace-pre-line inter-500 text-4xl tracking-tighter subpixel-antialiased text-center text-teal-800">Hello {firstName},<br /><span className="text-black">How can I assist you today?</span></p>
                    </div>
                    <div className="mt-auto w-full flex flex-col gap-y-4 items-center">
                        <div id="chat-box-content" className={`rounded-[17px] w-[90%] md:w-[75%] lg:w-[35%]`}>
                            {inputBox}
                        </div>
                        <div className="flex justify-center items-center w-[90%] md:w-[75%] lg:w-[35%]">
                            <div className="md:hidden grid grid-cols-1 gap-2">
                                {promptChips.slice(0, 2).map((chip) => (
                                    <motion.div key={chip.id} onClick={() => sendChipPrompt(chip.text)} whileTap={{ scale: isConnected ? 0.98 : 1 }} whileHover={{ scale: isConnected ? 1.02 : 1 }} transition={{ duration: 0.2, ease: "linear" }} className={`shadow-sm rounded-full px-4 py-2 bg-white ${isConnected ? "cursor-pointer" : "opacity-50 cursor-default"}`}>
                                        <div className="flex gap-x-2 items-center">
                                            <div>{chip.icon}</div>
                                            <div>
                                                <p className={`google-sans-flex-600 text-sm subpixel-antialiased ${fontThemes["dark-tailwind"]} tracking-tighter`}>{chip.text}</p>
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                            <div className="hidden md:grid md:grid-cols-2 md:gap-2">
                                {promptChips.map((chip) => (
                                    <motion.div key={chip.id} onClick={() => sendChipPrompt(chip.text)} whileTap={{ scale: isConnected ? 0.98 : 1 }} whileHover={{ scale: isConnected ? 1.02 : 1 }} transition={{ duration: 0.2, ease: "linear" }} className={`shadow-sm rounded-full px-4 py-2 bg-white ${isConnected ? "cursor-pointer" : "opacity-50 cursor-default"}`}>
                                        <div className="flex gap-x-2 items-center">
                                            <div>{chip.icon}</div>
                                            <div>
                                                <p className={`google-sans-flex-600 text-sm subpixel-antialiased ${fontThemes["dark-tailwind"]} tracking-tighter`}>{chip.text}</p>
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                <div id="chat-column" className="flex flex-col flex-1 overflow-hidden relative">
                    {/* messages scroll */}
                    <div className="flex-1 overflow-y-auto">
                        <div className="w-[90%] md:w-[75%] lg:w-[35%] mx-auto flex flex-col gap-y-6 pt-6 pb-4">
                            {messages.map((msg) => (
                                <motion.div key={msg.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                                    {msg.role === "user" ? (
                                        <div className="max-w-[75%] flex flex-col gap-y-2 items-end">
                                            {(msg.imageDataUrl || msg.imageUrl) && (
                                                <img src={msg.imageDataUrl || msg.imageUrl} alt="" className="w-36 h-36 rounded-2xl rounded-br-sm object-cover" />
                                            )}
                                            {msg.content && <UserBubble content={msg.content} />}
                                        </div>
                                    ) : (
                                        <div className="flex flex-col gap-y-3 w-full">
                                            {msg.content && (
                                                <div className="leading-relaxed google-sans-flex-400 text-[#1f1f1f]/85 text-[19px]">
                                                    <Markdown textContent={msg.content} theme="light" />
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
                                                            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelectedProduct(product) } }}
                                                            className="relative group rounded-xl p-4 flex flex-col gap-y-3 transition-all duration-200 overflow-hidden cursor-pointer focus:outline-none border border-teal-800/8 bg-white shadow-sm hover:shadow-md hover:border-teal-800/15"
                                                        >
                                                            <div className={`absolute left-0 top-0 bottom-0 w-[3px] rounded-l-xl ${statusAccent(product.halal_status ?? "")}`} />
                                                            <div className="pl-3 flex flex-col gap-y-3">
                                                                <div className="flex items-start justify-between gap-x-4">
                                                                    <p className="google-sans-flex-600 capitalize leading-snug text-[#1f1f1f]">{product.norm_name}</p>
                                                                    {product.verified === false ? (
                                                                        <span className="shrink-0 flex items-center gap-x-1.5 text-xs google-sans-flex-500 px-2.5 py-1 rounded-full text-amber-500 bg-amber-500/10 border border-amber-500/30">
                                                                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                                                                            Unverified
                                                                        </span>
                                                                    ) : (
                                                                        <span className={`shrink-0 flex items-center gap-x-1.5 text-xs google-sans-flex-500 px-2.5 py-1 rounded-full ${statusBadge(product.halal_status ?? "")}`}>
                                                                            <span className={`w-1.5 h-1.5 rounded-full ${statusDot(product.halal_status ?? "")}`} />
                                                                            {product.halal_status}
                                                                        </span>
                                                                    )}
                                                                </div>
                                                                {(product.category_l1 || product.category_l2) && (
                                                                    <div className="flex flex-wrap gap-1.5">
                                                                        {[product.category_l1, product.category_l2].filter(Boolean).map((cat, j) => (
                                                                            <span key={j} className="text-xs google-sans-flex-400 px-2 py-0.5 rounded-md border text-[#1f1f1f]/50 bg-teal-800/4 border-teal-800/8">{cat}</span>
                                                                        ))}
                                                                    </div>
                                                                )}
                                                                {product.companies && product.companies.length > 0 && (
                                                                    <p className="text-sm google-sans-flex-400 leading-relaxed text-[#1f1f1f]/70">
                                                                        {product.companies.map(c => c.charAt(0).toUpperCase() + c.slice(1).toLowerCase()).join(" · ")}
                                                                    </p>
                                                                )}
                                                                {product.cert_bodies && product.cert_bodies.length > 0 && (
                                                                    <div className="flex flex-wrap items-center gap-1.5">
                                                                        <span className="google-sans-flex-400 text-xs text-[#1f1f1f]/30">Certified by</span>
                                                                        {product.cert_bodies.map((body, j) => (
                                                                            <span key={j} className="text-xs google-sans-flex-400 text-teal-700 bg-teal-800/8 border border-teal-800/15 px-2 py-0.5 rounded-md">{body}</span>
                                                                        ))}
                                                                    </div>
                                                                )}
                                                                {product.verified === false && product.grounding && product.grounding.length > 0 && (
                                                                    <div className="flex flex-col gap-y-2 pt-2 border-t border-teal-800/8">
                                                                        <span className="text-xs google-sans-flex-500 text-amber-600">Unverified · sourced from web</span>
                                                                        {product.grounding.map((g, gi) => {
                                                                            const value = formatFieldValue(product[g.field as keyof Product])
                                                                            if (!value) return null
                                                                            const sites = Array.from(new Map(g.citations.map(c => [hostOf(c.url), c])).values())
                                                                            return (
                                                                                <div key={gi} className="flex items-center justify-between gap-x-3">
                                                                                    <p className="text-xs google-sans-flex-400 leading-snug min-w-0">
                                                                                        <span className="text-[#1f1f1f]/40">{FIELD_LABELS[g.field] ?? g.field}: </span>
                                                                                        <span className="text-[#1f1f1f]/80">{value}</span>
                                                                                    </p>
                                                                                    {sites.length > 0 && (
                                                                                        <div className="inline-flex items-center gap-x-2 shrink-0 px-2 py-1 rounded-sm border border-teal-800/10 bg-teal-800/3">
                                                                                            <span className="text-xs google-sans-flex-400 tracking-tighter text-[#1f1f1f]/45">{sites.length > 1 ? "Sources" : "Source"}</span>
                                                                                            <div className="flex items-center gap-x-0.2">
                                                                                                {sites.map((c, ci) => (
                                                                                                    <a key={ci} href={c.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} title={c.title || hostOf(c.url)} className="block transition-transform hover:scale-110">
                                                                                                        <img src={faviconOf(c.url)} alt="" loading="lazy" className="w-3.5 h-3.5 rounded-full object-cover bg-white" />
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

                            {/* Live web-search sources */}
                            {loading && webSources.length > 0 && (
                                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-y-2 rounded-xl p-3 border border-teal-800/8 bg-white">
                                    <span className="text-xs google-sans-flex-500 text-[#1f1f1f]/50">Searching the web…</span>
                                    {webSources.map((s, i) => (
                                        <a key={s.url ?? i} href={s.url} target="_blank" rel="noopener noreferrer" className="flex flex-col gap-y-1 group">
                                            <div className="flex items-center gap-x-2">
                                                {s.favicon ? <img src={s.favicon} alt="" className="w-4 h-4 rounded-sm shrink-0 object-contain" /> : <span className="w-4 h-4 rounded-sm shrink-0 bg-teal-800/10" />}
                                                <span className="text-xs google-sans-flex-500 truncate group-hover:underline text-[#1f1f1f]/70">{s.title || hostOf(s.url)}</span>
                                            </div>
                                            {s.highlights && s.highlights[0] && (
                                                <p className="text-xs google-sans-flex-400 line-clamp-2 pl-6 text-[#1f1f1f]/40">{s.highlights[0]}</p>
                                            )}
                                        </a>
                                    ))}
                                </motion.div>
                            )}

                            <div ref={messagesEndRef} />
                        </div>
                    </div>

                    {/* input pinned to bottom */}
                    <div className="shrink-0 px-4 pt-3 pb-6 flex justify-center">
                        <div className="w-[90%] md:w-[75%] lg:w-[35%]">
                            {inputBox}
                        </div>
                    </div>
                </div>
            )}

            <div className="w-full flex justify-center-safe pb-1">
                <p className="google-sans-flex-400 text-[#1f1f1f]/60 text-sm">Halal One can make mistakes. Refer to full <span className="underline">guide</span></p>
            </div>

            {/* ---- modals + toast ---- */}
            <ProductDetailModal product={selectedProduct} onClose={() => setSelectedProduct(null)} />

            <AnimatePresence>
                {dialogOpen && pendingImage && (
                    <ImageExtractionDialog key="image-dialog" image={pendingImage} theme="light" onConfirm={handleDialogConfirm} onClose={handleExtractionDialogClose} />
                )}
            </AnimatePresence>

            <AnimatePresence>
                {searchDialogOpen.showDialog && (
                    <SearchResultsDialog onClose={() => dispatch({ type: "closeSearchDialog" })} theme="light" tool_name={intermediateSearchResults?.tool_name ?? "Tool"} search_results={intermediateSearchResults?.search_results ?? []} />
                )}
            </AnimatePresence>

            {/* Compaction: confirm modal (awaiting) and a slim banner (running). */}
            <AnimatePresence>
                {compaction.phase === "awaiting" && (
                    <CompactionDialog
                        key="compaction-dialog"
                        theme="light"
                        message={compaction.message ?? "Your conversation has hit the token limit."}
                        disclaimer={compaction.disclaimer}
                        onConfirm={handleCompactConfirm}
                        onDecline={handleCompactDecline}
                    />
                )}
            </AnimatePresence>

            <AnimatePresence>
                {compaction.phase === "running" && (
                    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }} className="fixed bottom-6 left-1/2 -translate-x-1/2 z-70 px-4 py-2 rounded-lg bg-teal-800 text-white text-sm google-sans-flex-500 shadow-lg max-w-[90%] text-center">
                        {compaction.message ?? "History is being compacted, please wait…"}
                    </motion.div>
                )}
            </AnimatePresence>

            <AnimatePresence>
                {toast && (
                    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }} className="fixed bottom-6 left-1/2 -translate-x-1/2 z-70 px-4 py-2 rounded-lg bg-amber-600 text-white text-sm google-sans-flex-500 shadow-lg max-w-[90%] text-center">
                        {toast}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

const promptChips = [
    {
        id: "1",
        icon: <CookieIcon className={`fill-current text-teal-800`} />,
        text: "Are Oreo cookies halal?",
        description: "Check the status of this popular cream-filled chocolate biscuit."
    },
    {
        id: "2",
        icon: <StockPotIcon className={`fill-current text-teal-800`} />,
        text: "Is Chicken broth halal?",
        description: "Find out if ready-made or restaurant chicken stock is permissible."
    },
    {
        id: "3",
        icon: <CoffeeIcon className={`fill-current text-teal-800`} />,
        text: "Is Espresso coffee halal?",
        description: "Learn about the permissibility of coffee and caffeine drinks."
    },
    {
        id: "4",
        icon: <StockPotIcon className={`fill-current text-teal-800`} />,
        text: "Is Daal Makhni halal?",
        description: "Learn about the permissibility of coffee and caffeine drinks."
    }
];


function UserBubble({ content }: { content: string }) {
    const ref = useRef<HTMLDivElement>(null);
    const [multiLine, setMultiLine] = useState(false);

    useLayoutEffect(() => {
        const el = ref.current;
        if (!el) return;
        // line-height ≈ text-[19px] * leading-snug(1.375) ≈ 26px
        // 2 lines + py-2.5 (20px) ≈ 72px. Anything taller = 3+ lines.
        const check = () => setMultiLine(el.scrollHeight > 48);
        check();
        const ro = new ResizeObserver(check);
        ro.observe(el);
        return () => ro.disconnect();
    }, [content]);

    return (
        <div
            ref={ref}
            className={`px-6 py-2.5 leading-snug whitespace-pre-wrap wrap-break-words google-sans-flex-400 bg-teal-800/5 text-[#1f1f1f] text-[19px] ${multiLine ? "rounded-2xl rounded-br-sm" : "rounded-full"
                }`}
        >
            {content}
        </div>
    );
}