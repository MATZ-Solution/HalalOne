"use client"
import { useRef, useState, useEffect, useLayoutEffect, useReducer, type ChangeEvent, type ClipboardEvent, type CSSProperties } from "react"
import { useRouter, useParams } from "next/navigation"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"

import CoffeeIcon from "../../../icons/coffee_icon.svg"
import CookieIcon from "../../../icons/cookie_icon.svg"
import FlaskIcon from "../../../icons/flask_icon.svg"
import DessertIcon from "../../../icons/dessert_icon.svg"

import { createClient } from "@/utils/supabase/client"
import useWebsocket from "@/hooks/useWebsocket"
import type { Product } from "@/types/product"
import ProductDetailModal from "@/components/product/ProductDetailModal"
import Markdown from "@/components/markdown/Markdown"
import ImageExtractionDialog from "@/components/ImageExtractionDialog"
import SearchResultsDialog from "@/components/SearchResultsDialog"
import CompactionDialog from "@/components/CompactionDialog"

// ---- backend message / streaming types (unchanged from the original) ----
type AttachedImage = { previewUrl: string; base64: string; mimeType: string }

type Message = {
    id: string
    role: "user" | "agent"
    content: string
    products?: Product[]
    imageDataUrl?: string
    imageUrl?: string
}

type ToolCall = { tool: string; args: Record<string, unknown> }
type ReasoningContent = { node: string; reasoning: string }
type WebSource = { url: string; title?: string; favicon?: string; highlights?: string[] }
type Session = { session_id: string; title: string; description: string; created_at: string }

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
    message_id?: string
}

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

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const isSessionId = (s: string | undefined): s is string => !!s && UUID_RE.test(s)

const sessionIdFromPath = (): string | undefined => sessionIdFromSlug(window.location.pathname.split("/")[2])
const sessionIdFromSlug = (slug: string | undefined): string | undefined => (isSessionId(slug) ? slug : undefined)

// Point the address bar at a session WITHOUT a Next navigation (keeps the socket
// and in-flight caches alive across session switches).
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

// All per-session streaming state in one object (moved as a unit between the
// on-screen view and the background cache of in-flight sessions).
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
            return { ...rt, loading: false, compaction: { phase: "awaiting", message: data.message, disclaimer: data.disclaimer } }
        case "compaction_running":
            return { ...rt, loading: true, statusMessage: data.message ?? null, compaction: { phase: "running", message: data.message } }
        case "compaction_done":
        case "compaction_failed":
            return { ...rt, compaction: { phase: "idle" } }
        case "results": {
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
            const messages = rt.messages.length && rt.messages[rt.messages.length - 1].role === "user" ? rt.messages.slice(0, -1) : rt.messages
            return { ...emptyRuntime(), messages }
        }
        case "resumeTurn":
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

// Scoped HalalOne palette + base rules, namespaced under .hochat-root.
const SCOPED_CSS = `
.hochat-root{
  --green-900:#07351F; --green-800:#0F4B2E; --green-700:#196B24; --green-100:#D9DED8;
  --gold-600:#B7902F; --gold-500:#C9A248; --gold-200:#EBDFC0;
  --cream-50:#FBFAF6; --cream-100:#F7F4EC;
  --ink:#222222; --muted:#657269; --danger:#B23A2E; --border:#D9DED8;
  --shadow-sm:0 2px 8px color-mix(in srgb,#07351F 8%,transparent);
  --shadow-md:0 10px 28px color-mix(in srgb,#07351F 12%,transparent);
  --font:var(--font-plus-jakarta-sans),ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-family:var(--font); color:var(--ink);
  -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
}
.hochat-root *{box-sizing:border-box;}
.hochat-root ::selection{background:var(--gold-200);color:var(--green-900);}
.hochat-root .cscroll::-webkit-scrollbar{width:8px;}
.hochat-root .cscroll::-webkit-scrollbar-thumb{background:color-mix(in srgb,var(--green-800) 20%,transparent);border-radius:8px;}
.hochat-root .cscroll-d::-webkit-scrollbar{width:8px;}
.hochat-root .cscroll-d::-webkit-scrollbar-thumb{background:rgba(251,250,246,.18);border-radius:8px;}
@keyframes hoc-fade{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}
@keyframes hoc-blink{0%,80%,100%{opacity:.25;transform:translateY(0);}40%{opacity:1;transform:translateY(-3px);}}
@keyframes hoc-pulse{0%,100%{opacity:.5;}50%{opacity:1;}}
`

export default function Page() {
    const router = useRouter()
    const supabase = createClient()

    // ---- auth + profile ----
    const [authChecked, setAuthChecked] = useState<boolean>(false)
    const [profile, setProfile] = useState<{ name: string; email: string; avatarUrl: string }>({ name: "", email: "", avatarUrl: "" })
    const firstName = profile.name ? profile.name.split(" ")[0] : "there"
    const initials = (profile.name || "U").split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase()

    useEffect(() => {
        supabase.auth.getSession().then(({ data: { session } }) => {
            if (!session) { router.push("/login"); return }
            const u = session.user
            const name = (u.user_metadata?.full_name as string) || (u.email ? u.email.split("@")[0] : "User")
            const avatarUrl = (u.user_metadata?.avatar_url as string) || (u.user_metadata?.picture as string) || ""
            setProfile({ name, email: u.email ?? "", avatarUrl })
            setAuthChecked(true)
        })
    }, [])

    // ---- one long-lived socket ----
    const ws = useWebsocket(`${process.env.NEXT_PUBLIC_BACKEND_WS_URL}/ws`)
    const { isConnected, lastMessage, sendMessage, messageCount } = ws

    // ---- session routing ----
    const params = useParams<{ slug?: string[] }>()
    const initialSessionId = sessionIdFromSlug(Array.isArray(params.slug) ? params.slug[0] : undefined)

    const [threadId, setThreadId] = useState<string>(() => initialSessionId ?? crypto.randomUUID())
    const [historyLoading, setHistoryLoading] = useState<boolean>(() => initialSessionId !== undefined)
    const historyLoadingRef = useRef<boolean>(initialSessionId !== undefined)
    useEffect(() => { historyLoadingRef.current = historyLoading }, [historyLoading])

    // ---- sidebar ----
    // Default OPEN on desktop, but on phones/tablets the sidebar is an overlay
    // that must start CLOSED. isMobile drives both the default and whether the
    // sidebar pushes the layout (desktop) or floats over it (mobile).
    const [sidebarOpen, setSidebarOpen] = useState<boolean>(true)
    const [isMobile, setIsMobile] = useState<boolean>(false)
    useEffect(() => {
        const mq = window.matchMedia("(max-width: 768px)")
        const apply = () => { setIsMobile(mq.matches); setSidebarOpen(!mq.matches) }
        apply()                                   // set correct state on first arrival
        mq.addEventListener("change", apply)      // re-apply when crossing the breakpoint
        return () => mq.removeEventListener("change", apply)
    }, [])
    const [, setIsTextPresentSessionSearch] = useState<boolean>(false)
    const [sessions, setSessions] = useState<Session[]>([])
    const [sessionQuery, setSessionQuery] = useState<string>("")
    const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
    const sessionSearchRef = useRef<HTMLInputElement | null>(null)

    // ---- composer + view state ----
    const inputRef = useRef<HTMLDivElement | null>(null)
    const fileInputRef = useRef<HTMLInputElement | null>(null)
    const messagesEndRef = useRef<HTMLDivElement | null>(null)
    const [isTextPresent, setIsTextPresent] = useState<boolean>(false)
    const [pendingImage, setPendingImage] = useState<AttachedImage | null>(null)
    const [dialogOpen, setDialogOpen] = useState<boolean>(false)
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
    const [toast, setToast] = useState<string | null>(null)
    const [showDisconnected, setShowDisconnected] = useState<boolean>(false)
    const isConnectedRef = useRef(isConnected)

    const [runtime, dispatch] = useReducer(runtimeReducer, undefined, emptyRuntime)
    const { messages, loading, statusMessage, loadingPhrase, intermediateSearchResults, toolCalls, reasoningContent, detailsOpen, webSources, searchDialogOpen, compaction } = runtime
    const hasMessages = messages.length > 0
    const compactionBlocking = compaction.phase !== "idle"
    const canSend = isTextPresent && !loading && isConnected && !compactionBlocking

    const loadedSessionRef = useRef<string | null>(null)
    const inflightCacheRef = useRef<Map<string, Runtime>>(new Map())
    const prevThreadIdRef = useRef<string | null>(null)
    const runtimeRef = useRef(runtime)
    const loadingRef = useRef(false)

    useEffect(() => { runtimeRef.current = runtime; loadingRef.current = runtime.loading }, [runtime])

    // On session switch: stash an outgoing streaming session, then restore an
    // incoming stashed one (no refetch) or clear the view so history is fetched.
    useEffect(() => {
        const prev = prevThreadIdRef.current
        if (prev && prev !== threadId && (loadingRef.current || runtimeRef.current.compaction.phase !== "idle")) {
            inflightCacheRef.current.set(prev, runtimeRef.current)
        }
        prevThreadIdRef.current = threadId

        const cached = inflightCacheRef.current.get(threadId)
        if (cached) {
            inflightCacheRef.current.delete(threadId)
            dispatch({ type: "hydrate", runtime: cached })
            loadedSessionRef.current = threadId
            setHistoryLoading(false)
            return
        }
        dispatch({ type: "reset" })
        loadedSessionRef.current = null
    }, [threadId])

    // Request this session's history once the socket is up.
    useEffect(() => {
        if (!isConnected) return
        if (loadedSessionRef.current === threadId) return
        sendMessage(JSON.stringify({ type: "chat_history", session_id: threadId, serialize: false }))
    }, [threadId, isConnected, sendMessage])

    // Back/forward between sessions.
    useEffect(() => {
        const onPopState = () => {
            const id = sessionIdFromPath()
            setHistoryLoading(id !== undefined)
            setThreadId(id ?? crypto.randomUUID())
        }
        window.addEventListener("popstate", onPopState)
        return () => window.removeEventListener("popstate", onPopState)
    }, [])

    // Ask for the session list on mount and whenever the socket (re)connects, so
    // the always-visible sidebar stays populated.
    useEffect(() => {
        if (isConnected) sendMessage(JSON.stringify({ type: "chat_sessions" }))
    }, [isConnected, sendMessage])

    // Ctrl/Cmd+K focuses the session search.
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
                e.preventDefault()
                setSidebarOpen(true)
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

            if (data.type === "rate_limited") {
                setToast(data.response ?? "You have hit the rate limit. Please retry shortly.")
                if (loadingRef.current) dispatch({ type: "promptRejected" })
                return
            }

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
                const msgs: Message[] = (data.messages ?? []).map((m: { id?: string; role: string; content: string; search_results?: Product[]; image_url?: string }) => ({
                    id: m.id ?? crypto.randomUUID(),
                    role: m.role === "assistant" ? "agent" : "user",
                    content: m.content,
                    products: m.search_results ?? undefined,
                    imageUrl: m.image_url ?? undefined,
                }))
                if (historyLoadingRef.current && msgs.length === 0) {
                    setHistoryLoading(false)
                    setThreadId(crypto.randomUUID())
                    syncUrl(null, "replace")
                    return
                }

                const c = data.compaction
                const compaction: Compaction = c?.phase === "awaiting"
                    ? { phase: "awaiting", message: c.message, disclaimer: c.disclaimer }
                    : c?.phase === "compacting"
                        ? { phase: "running", message: c.message }
                        : { phase: "idle" }
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
                if (data.session_id === threadId) { setHistoryLoading(false); setThreadId(crypto.randomUUID()); syncUrl(null, "replace") }
                return
            }
        } catch { }
    }, [messageCount])

    // Auto-scroll to the latest message; auto-dismiss the toast.
    useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages, loading])
    useEffect(() => { if (!toast) return; const id = setTimeout(() => setToast(null), 3500); return () => clearTimeout(id) }, [toast])

    // Persistent "connection lost" banner while the socket is down (3s grace).
    useEffect(() => { isConnectedRef.current = isConnected }, [isConnected])
    useEffect(() => {
        if (isConnected) { setShowDisconnected(false); return }
        const id = setTimeout(() => { if (!isConnectedRef.current) setShowDisconnected(true) }, 3000)
        return () => clearTimeout(id)
    }, [isConnected])

    // ---- session actions ----
    // On mobile the sidebar is an overlay, so close it after an action that
    // reveals the conversation.
    const closeSidebarOnMobile = () => { if (isMobile) setSidebarOpen(false) }
    const handleNewChat = () => { setHistoryLoading(false); setThreadId(crypto.randomUUID()); syncUrl(null); closeSidebarOnMobile() }
    const handleSelectSession = (id: string) => { closeSidebarOnMobile(); if (id === threadId) return; setHistoryLoading(true); setThreadId(id); syncUrl(id) }
    const handleDeleteSession = (id: string) => { sendMessage(JSON.stringify({ type: "delete_session", session_id: id })); setConfirmDeleteId(null) }
    const handleSignOut = async () => { await supabase.auth.signOut(); router.push("/login"); router.refresh() }

    // ---- composer actions ----
    const pickPhrase = () => LOADING_PHRASES[Math.floor(Math.random() * LOADING_PHRASES.length)]

    const handleInputChange = () => {
        const el = inputRef.current
        const hasChar = ((el?.innerText ?? "").replace(/\n/g, "")).length > 0
        setIsTextPresent(hasChar)
    }

    const handleSend = () => {
        if (!isConnected || compactionBlocking) return
        const text = (inputRef.current?.innerText ?? "").trim()
        if (!text) return
        sendMessage(JSON.stringify({ type: "prompt", session_id: threadId, message: text }))
        syncUrl(threadId, "replace")
        dispatch({ type: "send", message: { id: crypto.randomUUID(), role: "user", content: text }, phrase: pickPhrase() })
        if (inputRef.current) inputRef.current.innerText = ""
        setIsTextPresent(false)
    }

    const handleCompactConfirm = () => {
        sendMessage(JSON.stringify({ type: "compact_confirm", session_id: threadId }))
        dispatch({ type: "resumeTurn" })
    }

    const handleCompactDecline = () => {
        sendMessage(JSON.stringify({ type: "compact_decline", session_id: threadId }))
        dispatch({ type: "resumeTurn" })
    }

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

    // ---- composer pill ----
    const composer = (
        <div style={{ maxWidth: 760, margin: "0 auto" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, background: "#fff", border: "1px solid var(--border)", borderRadius: 26, padding: "8px 8px 8px 18px", boxShadow: "var(--shadow-md)" }}>
                <input disabled={!isConnected || compactionBlocking} ref={fileInputRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleImageSelect} />
                <button
                    type="button"
                    aria-label="Attach image"
                    onClick={() => isConnected && !loading && !compactionBlocking && fileInputRef.current?.click()}
                    style={{ border: "none", background: "transparent", cursor: isConnected && !compactionBlocking ? "pointer" : "default", color: "var(--muted)", display: "flex", padding: 2, opacity: isConnected && !compactionBlocking ? 1 : 0.4 }}
                >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="3" stroke="currentColor" strokeWidth="1.8" /><circle cx="8.5" cy="9.5" r="1.6" stroke="currentColor" strokeWidth="1.6" /><path d="m4 18 5-5 4 4 3-3 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </button>
                <div style={{ position: "relative", flex: 1, minWidth: 0 }}>
                    {!isTextPresent && (
                        <span aria-hidden="true" style={{ position: "absolute", top: "6px", left: 0, pointerEvents: "none", fontSize: 15, lineHeight: 1.5, color: "var(--muted)" }}>Is Haribo halal?</span>
                    )}
                    <div
                        id="chat-input"
                        ref={inputRef}
                        contentEditable={isConnected && !compactionBlocking}
                        onInput={handleInputChange}
                        onPaste={handlePaste}
                        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canSend) handleSend() } }}
                        style={{ maxHeight: 120, overflowY: "auto", outline: "none", fontFamily: "var(--font)", fontSize: 15, color: "var(--green-900)", padding: "6px 0", lineHeight: 1.5 }}
                        className="cscroll"
                    />
                </div>
                <button
                    type="button"
                    onClick={() => canSend && handleSend()}
                    aria-label="Send"
                    style={{ flex: "0 0 auto", width: 40, height: 40, borderRadius: "50%", border: "none", background: canSend ? "var(--green-700)" : "color-mix(in srgb,var(--green-700) 45%,transparent)", color: "#fff", cursor: canSend ? "pointer" : "default", display: "flex", alignItems: "center", justifyContent: "center", transition: "background .13s ease" }}
                >
                    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 20V5M6 11l6-6 6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </button>
            </div>

            {!hasMessages && !loading && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "center", marginTop: 14 }}>
                    {promptChips.map((chip) => (
                        <button
                            key={chip.id}
                            onClick={() => sendChipPrompt(chip.text)}
                            disabled={!isConnected}
                            style={{ display: "flex", alignItems: "center", gap: 9, background: "#fff", border: "1px solid var(--border)", borderRadius: 999, padding: "9px 16px", cursor: isConnected ? "pointer" : "default", fontFamily: "var(--font)", fontSize: 13, fontWeight: 700, color: "var(--green-800)", boxShadow: "var(--shadow-sm)", opacity: isConnected ? 1 : 0.5 }}
                        >
                            <span style={{ color: "var(--gold-600)", display: "flex" }}>{chip.icon}</span>
                            {chip.text}
                        </button>
                    ))}
                </div>
            )}

            <div style={{ textAlign: "center", fontSize: 12, color: "var(--muted)", marginTop: 14 }}>
                HalalOne can make mistakes. Refer to full <span style={{ fontWeight: 700, textDecoration: "underline", textUnderlineOffset: 2 }}>guide</span>.
            </div>
        </div>
    )

    // ---- live "thinking" indicator (status + tool-call & reasoning dropdowns + search progress) ----
    const loadingIndicator = (
        <div style={{ animation: "hoc-fade .2s ease both" }}>
            <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                <div style={{ flex: "0 0 auto", width: 32, height: 32, borderRadius: 9, background: "linear-gradient(150deg,#0F4B2E,#07351F)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <svg width="18" height="18" viewBox="-16 -16 32 32" aria-hidden="true"><path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke="var(--gold-500)" strokeWidth="2.8" strokeLinejoin="round" /><path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke="var(--cream-50)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </div>
                <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                    {/* status row */}
                    {statusMessage ? (
                        <button type="button" onClick={() => toolCalls.length > 0 && dispatch({ type: "toggleDetails" })} style={{ display: "flex", alignItems: "center", gap: 6, background: "transparent", border: "none", cursor: toolCalls.length > 0 ? "pointer" : "default", padding: 0, textAlign: "left" }}>
                            <span style={{ fontSize: 13, color: "var(--muted)" }}>{statusMessage}</span>
                            {toolCalls.length > 0 && (
                                <motion.svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" animate={{ rotate: detailsOpen ? 180 : 0 }} transition={{ duration: 0.2 }}><polyline points="6 9 12 15 18 9" /></motion.svg>
                            )}
                        </button>
                    ) : (
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--green-700)", animation: "hoc-blink 1s infinite" }} />
                            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--green-700)", animation: "hoc-blink 1s infinite .18s" }} />
                            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--green-700)", animation: "hoc-blink 1s infinite .36s" }} />
                            <span style={{ fontSize: 12.5, color: "var(--muted)", marginLeft: 6 }}>{loadingPhrase || "Checking halal status…"}</span>
                        </div>
                    )}

                    {/* tool-call + reasoning dropdown */}
                    <AnimatePresence>
                        {detailsOpen && (
                            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} style={{ overflow: "hidden" }}>
                                <div style={{ display: "flex", gap: 16, background: "color-mix(in srgb,var(--green-800) 4%,transparent)", border: "1px solid color-mix(in srgb,var(--green-800) 10%,transparent)", borderRadius: 10, maxHeight: 200, overflowY: "auto", padding: 12 }}>
                                    {toolCalls.length > 0 && (
                                        <div style={{ display: "flex", flexDirection: "column", flexShrink: 0, minWidth: "50%", gap: 8 }}>
                                            <strong style={{ fontSize: 12, fontFamily: "monospace", color: "var(--muted)" }}>Tool calls</strong>
                                            {toolCalls.map((tc, i) => (
                                                <div key={i} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                                                    <p style={{ margin: 0, fontSize: 11, fontFamily: "monospace", color: "var(--muted)" }}>{tc.tool}</p>
                                                    <pre style={{ margin: 0, fontSize: 11, fontFamily: "monospace", overflowX: "auto", whiteSpace: "pre-wrap", wordBreak: "break-all", color: "var(--green-800)" }}>{JSON.stringify(tc.args, null, 2)}</pre>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    {reasoningContent.length > 0 && (
                                        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                                            <strong style={{ fontSize: 12, fontFamily: "monospace", color: "var(--muted)" }}>Graph Execution</strong>
                                            {reasoningContent.map((r, i) => (
                                                <div key={i} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                                    <div style={{ padding: 4, borderRadius: 4, border: "1px solid color-mix(in srgb,var(--green-800) 20%,transparent)", width: "max-content" }}><p style={{ margin: 0, fontSize: 11, fontFamily: "monospace", color: "var(--muted)" }}>{r.node}</p></div>
                                                    <p style={{ margin: 0, fontSize: 11, fontFamily: "monospace", color: "var(--muted)" }}>{r.reasoning}</p>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* search-progress button */}
                    <AnimatePresence>
                        {searchDialogOpen.showButton && (
                            <motion.button type="button" onClick={() => dispatch({ type: "openSearchDialog" })} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{ width: "max-content", padding: "5px 10px", cursor: "pointer", display: "flex", gap: 8, alignItems: "center", borderRadius: 8, border: "1px solid color-mix(in srgb,var(--green-800) 20%,transparent)", background: "#fff" }}>
                                <span style={{ width: 8, height: 8, background: "var(--gold-500)", borderRadius: "50%" }} />
                                <span style={{ fontSize: 11.5, fontFamily: "monospace", color: "var(--muted)" }}>See search progress</span>
                            </motion.button>
                        )}
                    </AnimatePresence>

                    {/* live web sources */}
                    {webSources.length > 0 && (
                        <div style={{ display: "flex", flexDirection: "column", gap: 8, borderRadius: 12, padding: 12, border: "1px solid var(--border)", background: "#fff" }}>
                            <span style={{ fontSize: 11.5, fontWeight: 700, color: "var(--muted)" }}>Searching the web…</span>
                            {webSources.map((s, i) => (
                                <a key={s.url ?? i} href={s.url} target="_blank" rel="noopener noreferrer" style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                        {s.favicon ? <img src={s.favicon} alt="" style={{ width: 16, height: 16, borderRadius: 3, objectFit: "contain" }} /> : <span style={{ width: 16, height: 16, borderRadius: 3, background: "color-mix(in srgb,var(--green-800) 10%,transparent)" }} />}
                                        <span style={{ fontSize: 12, fontWeight: 700, color: "var(--green-800)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.title || hostOf(s.url)}</span>
                                    </div>
                                    {s.highlights && s.highlights[0] && (
                                        <p style={{ margin: 0, paddingLeft: 24, fontSize: 12, color: "var(--muted)", overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>{s.highlights[0]}</p>
                                    )}
                                </a>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )

    // Skeleton while an existing session's history loads.
    const messagesSkeleton = (
        <div style={{ maxWidth: 760, margin: "0 auto", display: "flex", flexDirection: "column", gap: 22, paddingTop: 8 }}>
            {[0, 1, 2, 3].map((i) => (
                <div key={i} style={{ display: "flex", justifyContent: i % 2 === 1 ? "flex-end" : "flex-start" }}>
                    {i % 2 === 1 ? (
                        <div style={{ height: 40, width: "50%", borderRadius: 16, background: "color-mix(in srgb,var(--green-700) 8%,transparent)", animation: "hoc-pulse 1.4s ease-in-out infinite" }} />
                    ) : (
                        <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 8 }}>
                            <div style={{ height: 12, width: "75%", borderRadius: 6, background: "color-mix(in srgb,var(--green-700) 8%,transparent)", animation: "hoc-pulse 1.4s ease-in-out infinite" }} />
                            <div style={{ height: 12, width: "85%", borderRadius: 6, background: "color-mix(in srgb,var(--green-700) 8%,transparent)", animation: "hoc-pulse 1.4s ease-in-out infinite" }} />
                            <div style={{ height: 90, width: "100%", borderRadius: 12, background: "color-mix(in srgb,var(--green-700) 5%,transparent)", animation: "hoc-pulse 1.4s ease-in-out infinite" }} />
                        </div>
                    )}
                </div>
            ))}
        </div>
    )

    if (!authChecked) return <div className="hochat-root" style={{ height: "100dvh", background: "var(--cream-50)" }}><style>{SCOPED_CSS}</style></div>

    return (
        <div className="hochat-root" style={{ height: "100dvh", display: "flex", overflow: "hidden", background: "var(--cream-50)" }}>
            <style>{SCOPED_CSS}</style>

            {/* Mobile-only backdrop: tap to close the overlay sidebar. */}
            {isMobile && sidebarOpen && (
                <div onClick={() => setSidebarOpen(false)} style={{ position: "fixed", inset: 0, zIndex: 40, background: "rgba(7,53,31,.45)" }} />
            )}

            {/* ============ SIDEBAR ============ */}
            <aside
                className="cscroll-d"
                style={isMobile
                    ? { position: "fixed", top: 0, left: 0, bottom: 0, zIndex: 50, width: 280, flex: "0 0 auto", background: "linear-gradient(180deg,#0F4B2E,#07351F)", color: "var(--cream-50)", display: "flex", flexDirection: "column", overflow: "hidden", transform: sidebarOpen ? "translateX(0)" : "translateX(-100%)", transition: "transform .22s ease", boxShadow: sidebarOpen ? "var(--shadow-md)" : "none" }
                    : { width: sidebarOpen ? 280 : 0, flex: "0 0 auto", background: "linear-gradient(180deg,#0F4B2E,#07351F)", color: "var(--cream-50)", display: "flex", flexDirection: "column", transition: "width .22s ease", overflow: "hidden", position: "relative" }}
            >
                <div aria-hidden="true" style={{ position: "absolute", inset: 0, backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='56' height='56' viewBox='0 0 56 56' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M28 3L50 28L28 53L6 28Z' fill='none' stroke='rgba(251,250,246,0.04)' stroke-width='1'/%3E%3C/svg%3E\")", backgroundSize: "56px", pointerEvents: "none" }} />
                <div style={{ position: "relative", display: "flex", flexDirection: "column", height: "100%", width: 280 }}>
                    {/* brand row */}
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 18px 14px" }}>
                        <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10 }}>
                            <svg width="28" height="28" viewBox="-16 -16 32 32" aria-hidden="true"><path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke="var(--gold-500)" strokeWidth="2.6" strokeLinejoin="round" /><path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke="var(--cream-50)" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                            <div style={{ fontSize: 18, fontWeight: 800, letterSpacing: "-0.02em", color: "#fff" }}>Halal<span style={{ color: "var(--gold-500)" }}>One</span></div>
                        </Link>
                        <button onClick={() => setSidebarOpen(false)} aria-label="Collapse sidebar" title="Collapse" style={{ border: "none", background: "transparent", cursor: "pointer", color: "color-mix(in srgb,var(--cream-50) 70%,transparent)", padding: 4, display: "flex" }}>
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.8" /><path d="M9 4v16" stroke="currentColor" strokeWidth="1.8" /></svg>
                        </button>
                    </div>

                    {/* new chat */}
                    <div style={{ padding: "2px 16px 12px" }}>
                        <button onClick={handleNewChat} style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 9, padding: 12, borderRadius: 12, border: "none", background: "var(--gold-500)", color: "var(--green-900)", cursor: "pointer", fontFamily: "var(--font)", fontSize: 14, fontWeight: 800, letterSpacing: "-0.01em" }}>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" /></svg>
                            New Chat
                        </button>
                    </div>

                    {/* search */}
                    <div style={{ padding: "0 16px 14px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 9, background: "rgba(251,250,246,.1)", border: "1px solid rgba(251,250,246,.16)", borderRadius: 11, padding: "10px 13px" }}>
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="11" cy="11" r="8" stroke="color-mix(in srgb,var(--cream-50) 70%,transparent)" strokeWidth="2" /><path d="m21 21-4.35-4.35" stroke="color-mix(in srgb,var(--cream-50) 70%,transparent)" strokeWidth="2" strokeLinecap="round" /></svg>
                            <input
                                ref={sessionSearchRef}
                                type="text"
                                value={sessionQuery}
                                onChange={(e) => { setSessionQuery(e.target.value); setIsTextPresentSessionSearch(e.target.value.length > 0) }}
                                placeholder="Search chats"
                                style={{ flex: 1, minWidth: 0, border: "none", outline: "none", background: "transparent", fontFamily: "var(--font)", fontSize: 13, color: "#fff" }}
                            />
                            <span style={{ fontSize: 10, fontWeight: 700, color: "color-mix(in srgb,var(--cream-50) 45%,transparent)", border: "1px solid rgba(251,250,246,.2)", borderRadius: 5, padding: "1px 5px" }}>Ctrl+K</span>
                        </div>
                    </div>

                    {/* history */}
                    <div className="cscroll-d" style={{ flex: 1, overflowY: "auto", padding: "2px 8px 12px" }}>
                        {sessions.length === 0 && (
                            <div style={{ padding: "24px 14px", textAlign: "center", fontSize: 12.5, color: "color-mix(in srgb,var(--cream-50) 55%,transparent)", lineHeight: 1.6 }}>
                                No chats yet. Start your first conversation with HalalOne.
                            </div>
                        )}
                        {Object.entries(groupedSessions).map(([label, items]) => items.length === 0 ? null : (
                            <div key={label} style={{ marginBottom: 8 }}>
                                <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: ".1em", textTransform: "uppercase", color: "var(--gold-500)", padding: "10px 10px 6px" }}>{label}</div>
                                {items.map((item) => {
                                    const active = item.session_id === threadId
                                    return (
                                        <div key={item.session_id} style={{ display: "flex", alignItems: "center", gap: 4, borderRadius: 9, background: active ? "rgba(251,250,246,.12)" : "transparent" }}>
                                            <button
                                                onClick={() => handleSelectSession(item.session_id)}
                                                title={item.description || item.title}
                                                style={{ flex: 1, minWidth: 0, textAlign: "left", border: "none", background: "transparent", cursor: "pointer", fontFamily: "var(--font)", fontSize: 13, color: active ? "#fff" : "color-mix(in srgb,var(--cream-50) 82%,transparent)", padding: "9px 10px", borderRadius: 9, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
                                            >
                                                {item.description || item.title}
                                            </button>
                                            {confirmDeleteId === item.session_id ? (
                                                <div style={{ display: "flex", gap: 2, paddingRight: 6 }}>
                                                    <button onClick={() => handleDeleteSession(item.session_id)} aria-label="Confirm delete" style={{ border: "none", background: "transparent", cursor: "pointer", color: "#ff8a80", display: "flex", padding: 2 }}>
                                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                                                    </button>
                                                    <button onClick={() => setConfirmDeleteId(null)} aria-label="Cancel delete" style={{ border: "none", background: "transparent", cursor: "pointer", color: "color-mix(in srgb,var(--cream-50) 55%,transparent)", display: "flex", padding: 2 }}>
                                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                                                    </button>
                                                </div>
                                            ) : (
                                                <button onClick={() => setConfirmDeleteId(item.session_id)} aria-label="Delete session" style={{ border: "none", background: "transparent", cursor: "pointer", color: "color-mix(in srgb,var(--cream-50) 45%,transparent)", display: "flex", padding: 2, marginRight: 6 }}>
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /><path d="M10 11v6M14 11v6" /></svg>
                                                </button>
                                            )}
                                        </div>
                                    )
                                })}
                            </div>
                        ))}
                    </div>

                    {/* user */}
                    <div style={{ borderTop: "1px solid rgba(251,250,246,.14)", padding: "12px 14px", display: "flex", alignItems: "center", gap: 11 }}>
                        <SidebarAvatar url={profile.avatarUrl} initials={initials} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 13, fontWeight: 700, color: "#fff", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{profile.name || "User"}</div>
                            <div style={{ fontSize: 11, color: "color-mix(in srgb,var(--cream-50) 55%,transparent)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{profile.email}</div>
                        </div>
                        <button onClick={handleSignOut} aria-label="Sign out" style={{ border: "none", background: "transparent", cursor: "pointer", color: "color-mix(in srgb,var(--cream-50) 65%,transparent)", padding: 4, display: "flex" }}>
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                        </button>
                    </div>
                </div>
            </aside>

            {/* ============ MAIN ============ */}
            <main style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", position: "relative" }}>
                {/* top bar */}
                <div style={{ flex: "0 0 auto", display: "flex", alignItems: "center", gap: 12, padding: "12px 20px", position: "relative", zIndex: 5 }}>
                    {!sidebarOpen && (
                        <button onClick={() => setSidebarOpen(true)} aria-label="Expand sidebar" style={{ border: "1px solid var(--border)", background: "#fff", cursor: "pointer", color: "var(--green-800)", padding: 7, borderRadius: 9, display: "flex", boxShadow: "var(--shadow-sm)" }}>
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.8" /><path d="M9 4v16" stroke="currentColor" strokeWidth="1.8" /></svg>
                        </button>
                    )}
                    <Link href="/" style={{ display: "flex", alignItems: "center", gap: 7, border: "1px solid var(--border)", background: "#fff", borderRadius: 10, padding: "7px 13px", fontSize: 13, fontWeight: 700, color: "var(--green-800)", boxShadow: "var(--shadow-sm)" }}>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M3 11l9-8 9 8M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                        Home
                    </Link>
                    <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
                        <AnimatePresence>
                            {showDisconnected && (
                                <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} style={{ display: "flex", alignItems: "center", gap: 8, background: "var(--danger)", color: "#fff", borderRadius: 999, padding: "7px 16px", fontSize: 12.5, fontWeight: 700, boxShadow: "var(--shadow-md)" }}>
                                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#fff", animation: "hoc-pulse 1.1s ease-in-out infinite" }} />
                                    Connection lost — trying to reconnect…
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, border: "1px solid var(--border)", background: "#fff", borderRadius: 10, padding: "6px 12px", boxShadow: "var(--shadow-sm)" }}>
                        <svg width="18" height="18" viewBox="-16 -16 32 32" aria-hidden="true"><path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke="var(--gold-500)" strokeWidth="2.8" strokeLinejoin="round" /><path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke="var(--green-800)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                        <div style={{ fontSize: 14, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--green-900)" }}>Halal<span style={{ color: "var(--gold-600)" }}>One</span></div>
                    </div>
                </div>

                {/* conversation / greeting */}
                {historyLoading && !hasMessages ? (
                    <div className="cscroll" style={{ flex: 1, overflowY: "auto", padding: "8px 20px 20px" }}>{messagesSkeleton}</div>
                ) : !hasMessages && !loading ? (
                    <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", position: "relative", padding: 20 }}>
                        <div aria-hidden="true" style={{ position: "absolute", width: 640, height: 640, borderRadius: "50%", background: "radial-gradient(circle at 50% 45%,color-mix(in srgb,var(--green-700) 20%,transparent),color-mix(in srgb,var(--gold-500) 12%,transparent) 42%,transparent 68%)", filter: "blur(18px)" }} />
                        <div style={{ position: "relative", textAlign: "center" }}>
                            <div style={{ fontSize: "clamp(30px,4vw,44px)", fontWeight: 800, letterSpacing: "-0.02em", color: "var(--green-700)", lineHeight: 1.1 }}>Salam {firstName},</div>
                            <div style={{ fontSize: "clamp(30px,4vw,44px)", fontWeight: 800, letterSpacing: "-0.02em", color: "var(--green-900)", lineHeight: 1.15 }}>How can I assist you today?</div>
                            <div style={{ fontSize: 14, color: "var(--muted)", marginTop: 16, maxWidth: 440, lineHeight: 1.6, marginLeft: "auto", marginRight: "auto" }}>Ask about any product, dish, ingredient or E-number — I&apos;ll check its halal status and cite the sources.</div>
                        </div>
                    </div>
                ) : (
                    <div className="cscroll" style={{ flex: 1, overflowY: "auto", padding: "8px 20px 20px" }}>
                        <div style={{ maxWidth: 760, margin: "0 auto", display: "flex", flexDirection: "column", gap: 22 }}>
                            {messages.map((msg) => (
                                msg.role === "user" ? (
                                    <div key={msg.id} style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
                                        {(msg.imageDataUrl || msg.imageUrl) && (
                                            <img src={msg.imageDataUrl || msg.imageUrl} alt="" style={{ width: 144, height: 144, borderRadius: 16, objectFit: "cover" }} />
                                        )}
                                        {msg.content && <UserBubble content={msg.content} />}
                                    </div>
                                ) : (
                                    <div key={msg.id} style={{ alignSelf: "stretch", animation: "hoc-fade .3s ease both" }}>
                                        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                                            <div style={{ flex: "0 0 auto", width: 32, height: 32, borderRadius: 9, background: "linear-gradient(150deg,#0F4B2E,#07351F)", display: "flex", alignItems: "center", justifyContent: "center", marginTop: 2 }}>
                                                <svg width="18" height="18" viewBox="-16 -16 32 32" aria-hidden="true"><path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke="var(--gold-500)" strokeWidth="2.8" strokeLinejoin="round" /><path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke="var(--cream-50)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                                            </div>
                                            <div style={{ flex: 1, minWidth: 0 }}>
                                                {msg.content && (
                                                    <div style={{ fontSize: 14.5, lineHeight: 1.65, color: "var(--ink)" }}>
                                                        <Markdown textContent={msg.content} theme="light" />
                                                    </div>
                                                )}
                                                {msg.products && msg.products.length > 0 && (
                                                    <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 14 }}>
                                                        {msg.products.map((product) => (
                                                            <ProductCard key={product.canonical_id} product={product} onOpen={() => setSelectedProduct(product)} />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )
                            ))}

                            {loading && loadingIndicator}

                            <div ref={messagesEndRef} />
                        </div>
                    </div>
                )}

                {/* composer */}
                <div style={{ flex: "0 0 auto", padding: "8px 20px 18px" }}>{composer}</div>
            </main>

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
                    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }} style={{ position: "fixed", bottom: 24, left: "50%", transform: "translateX(-50%)", zIndex: 70, padding: "8px 16px", borderRadius: 10, background: "var(--green-800)", color: "#fff", fontSize: 13, fontWeight: 700, boxShadow: "var(--shadow-md)", maxWidth: "90%", textAlign: "center" }}>
                        {compaction.message ?? "History is being compacted, please wait…"}
                    </motion.div>
                )}
            </AnimatePresence>

            <AnimatePresence>
                {toast && (
                    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }} style={{ position: "fixed", bottom: 24, left: "50%", transform: "translateX(-50%)", zIndex: 70, padding: "8px 16px", borderRadius: 10, background: "var(--gold-600)", color: "#fff", fontSize: 13, fontWeight: 700, boxShadow: "var(--shadow-md)", maxWidth: "90%", textAlign: "center" }}>
                        {toast}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

const promptChips = [
    { id: "1", icon: <FlaskIcon className="fill-current w-4 h-4" />, text: "Is E120 halal?" },
    { id: "2", icon: <CookieIcon className="fill-current w-4 h-4" />, text: "What is the halal status of haribo?" },
    { id: "3", icon: <DessertIcon className="fill-current w-4 h-4" />, text: "Is creme brule halal?" },
    { id: "4", icon: <CoffeeIcon className="fill-current w-4 h-4" />, text: "Is Barzula Turkish coffee halal?" },
]

// Sidebar avatar. Uses an <img> with referrerPolicy="no-referrer" — Google
// (lh3.googleusercontent.com) avatars often 403 when a referrer is sent, which a
// CSS background-image can't suppress. Falls back to the initials on empty URL
// or a load error.
function SidebarAvatar({ url, initials }: { url: string; initials: string }) {
    const [failed, setFailed] = useState(false)
    const box: CSSProperties = { flex: "0 0 auto", width: 34, height: 34, borderRadius: 10 }
    if (url && !failed) {
        return (
            <img
                src={url}
                alt=""
                referrerPolicy="no-referrer"
                onError={() => setFailed(true)}
                style={{ ...box, objectFit: "cover" }}
            />
        )
    }
    return (
        <div style={{ ...box, background: "var(--gold-500)", color: "var(--green-900)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 14 }}>{initials}</div>
    )
}

function UserBubble({ content }: { content: string }) {
    const ref = useRef<HTMLDivElement>(null)
    const [multiLine, setMultiLine] = useState(false)

    useLayoutEffect(() => {
        const el = ref.current
        if (!el) return
        const check = () => setMultiLine(el.scrollHeight > 48)
        check()
        const ro = new ResizeObserver(check)
        ro.observe(el)
        return () => ro.disconnect()
    }, [content])

    return (
        <div
            ref={ref}
            style={{
                maxWidth: "80%",
                background: "color-mix(in srgb,var(--green-700) 9%,transparent)",
                border: "1px solid color-mix(in srgb,var(--green-700) 20%,transparent)",
                color: "var(--green-900)",
                borderRadius: multiLine ? "16px 16px 4px 16px" : 999,
                padding: multiLine ? "12px 16px" : "10px 18px",
                fontSize: 14.5,
                lineHeight: 1.55,
                whiteSpace: "pre-wrap",
                overflowWrap: "break-word",
                animation: "hoc-fade .25s ease both",
            }}
        >
            {content}
        </div>
    )
}

// Sources pill for a grounded field: shows the favicons; clicking it opens a
// popover listing every source as a normal link (each opens on its own click, so
// no popup blocker is triggered). Clicking a favicon opens that one source too.
// `description` is optional: the backend grounding citations currently carry
// only url + title, so it renders only if/when the backend starts sending one.
type Citation = { url: string; title?: string; description?: string }
function SourcesPill({ sites }: { sites: Citation[] }) {
    const [open, setOpen] = useState(false)
    const ref = useRef<HTMLDivElement>(null)
    // Small delay on close so moving the pointer across the gap into the popover
    // doesn't dismiss it.
    const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
    const cancelClose = () => { if (closeTimer.current) { clearTimeout(closeTimer.current); closeTimer.current = null } }
    const scheduleClose = () => { cancelClose(); closeTimer.current = setTimeout(() => setOpen(false), 140) }

    useEffect(() => () => cancelClose(), [])

    // Touch/outside-click fallback (no hover on touch devices).
    useEffect(() => {
        if (!open) return
        const onDown = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
        const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false) }
        document.addEventListener("mousedown", onDown)
        document.addEventListener("keydown", onKey)
        return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey) }
    }, [open])

    return (
        <div
            ref={ref}
            style={{ position: "relative", flex: "0 0 auto" }}
            onMouseEnter={() => { cancelClose(); setOpen(true) }}
            onMouseLeave={scheduleClose}
        >
            <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setOpen(o => !o) }}
                title={sites.length > 1 ? `View ${sites.length} sources` : "View source"}
                style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "3px 9px", borderRadius: 7, border: "1px solid var(--border)", background: "var(--cream-100)", cursor: "pointer", fontFamily: "inherit" }}
            >
                <span style={{ fontSize: 11, color: "var(--muted)" }}>{sites.length > 1 ? "Sources" : "Source"}</span>
                <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
                    {sites.map((c, ci) => (
                        <img key={ci} src={faviconOf(c.url)} alt="" loading="lazy" style={{ width: 14, height: 14, borderRadius: "50%", objectFit: "cover", background: "#fff" }} />
                    ))}
                </div>
            </button>

            {open && (
                <div
                    onClick={(e) => e.stopPropagation()}
                    onMouseEnter={cancelClose}
                    onMouseLeave={scheduleClose}
                    style={{ position: "absolute", top: "calc(100% + 6px)", right: 0, zIndex: 20, minWidth: 220, maxWidth: 300, background: "#fff", border: "1px solid var(--border)", borderRadius: 10, boxShadow: "var(--shadow-md)", overflow: "hidden", padding: 4 }}
                >
                    {sites.map((c, ci) => (
                        <a
                            key={ci}
                            href={c.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={() => setOpen(false)}
                            title={c.title || c.url}
                            style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "8px 10px", borderRadius: 7, textDecoration: "none" }}
                            onMouseEnter={(e) => { e.currentTarget.style.background = "var(--cream-100)" }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent" }}
                        >
                            <img src={faviconOf(c.url)} alt="" loading="lazy" style={{ width: 16, height: 16, borderRadius: "50%", objectFit: "cover", background: "#fff", flex: "0 0 auto", marginTop: 1 }} />
                            <span style={{ minWidth: 0 }}>
                                <span style={{ display: "block", fontSize: 12, color: "var(--green-900)", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.title || hostOf(c.url)}</span>
                                {c.description && (
                                    <span style={{ display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", fontSize: 11, lineHeight: 1.4, color: "var(--muted)", marginTop: 2 }}>{c.description}</span>
                                )}
                            </span>
                        </a>
                    ))}
                </div>
            )}
        </div>
    )
}

// Inline product result card (HalalOne styling). Preserves the unverified /
// grounding-citation behaviour from the original; click opens the full modal.
// Status tag styling (rail + top-right pill), covering the four halal states.
// Web-sourced results carry a real status, so the pill always shows it — the
// unverified/web provenance is conveyed separately by the grounding line below.
const statusStyle = (raw: string) => {
    // Collapse repeated letters so spelling variants normalize to one form
    // (e.g. "haraam" -> "haram", "halaal" -> "halal", "mushbooh" -> "mushboh").
    const s = (raw ?? "").toLowerCase().replace(/(.)\1+/g, "$1")
    if (s.includes("halal")) return { label: "Halal", rail: "var(--green-700)", fg: "var(--green-700)", dot: "var(--green-700)", bg: "color-mix(in srgb,var(--green-700) 12%,transparent)", border: "color-mix(in srgb,var(--green-700) 30%,transparent)" }
    if (s.includes("haram")) return { label: "Haram", rail: "var(--danger)", fg: "var(--danger)", dot: "var(--danger)", bg: "color-mix(in srgb,var(--danger) 12%,transparent)", border: "color-mix(in srgb,var(--danger) 30%,transparent)" }
    if (s.includes("mushbo") || s.includes("doubt") || s.includes("depend")) return { label: "Mushbooh", rail: "var(--gold-500)", fg: "var(--gold-600)", dot: "var(--gold-500)", bg: "color-mix(in srgb,var(--gold-500) 16%,transparent)", border: "color-mix(in srgb,var(--gold-500) 40%,transparent)" }
    return { label: "Unknown", rail: "var(--muted)", fg: "var(--muted)", dot: "var(--muted)", bg: "color-mix(in srgb,var(--muted) 12%,transparent)", border: "color-mix(in srgb,var(--muted) 30%,transparent)" }
}

function ProductCard({ product, onOpen }: { product: Product; onOpen: () => void }) {
    const status = product.halal_status ?? ""
    const st = statusStyle(status)
    const cats = [product.category_l1, product.category_l2].filter(Boolean) as string[]
    return (
        <div
            role="button"
            tabIndex={0}
            onClick={onOpen}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen() } }}
            style={{ background: "#fff", border: "1px solid var(--border)", borderLeftWidth: 4, borderLeftColor: st.rail, borderRadius: 14, padding: "16px 18px", boxShadow: "var(--shadow-sm)", cursor: "pointer" }}
        >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 14 }}>
                <div style={{ fontSize: 15, fontWeight: 800, color: "var(--green-900)", lineHeight: 1.3, textTransform: "capitalize" }}>{product.norm_name}</div>
                {/* Halal-status tag — shown for every result (verified or web-sourced). */}
                <span style={{ flex: "0 0 auto", display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 11px", borderRadius: 999, fontSize: 10.5, fontWeight: 800, background: st.bg, color: st.fg, border: `1px solid ${st.border}` }}>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: st.dot }} />{st.label}
                </span>
            </div>

            {cats.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
                    {cats.map((c, i) => (
                        <span key={i} style={{ padding: "3px 10px", borderRadius: 8, fontSize: 10.5, fontWeight: 700, background: "var(--cream-100)", color: "var(--muted)", border: "1px solid var(--border)" }}>{c}</span>
                    ))}
                </div>
            )}

            {product.companies && product.companies.length > 0 && (
                <div style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 10, lineHeight: 1.5 }}>
                    {product.companies.map(c => c.charAt(0).toUpperCase() + c.slice(1).toLowerCase()).join(" · ")}
                </div>
            )}

            {product.cert_bodies && product.cert_bodies.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6, marginTop: 10 }}>
                    <span style={{ fontSize: 11, color: "var(--muted)" }}>Certified by</span>
                    {product.cert_bodies.map((b, i) => (
                        <span key={i} style={{ fontSize: 11, fontWeight: 700, color: "var(--green-700)", background: "color-mix(in srgb,var(--green-700) 8%,transparent)", border: "1px solid color-mix(in srgb,var(--green-700) 22%,transparent)", padding: "2px 9px", borderRadius: 7 }}>{b}</span>
                    ))}
                </div>
            )}

            {product.verified !== false && (
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--cream-100)", fontSize: 11, fontWeight: 700, color: "var(--green-700)" }}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" /></svg>
                    Verified · Sourced from database
                </div>
            )}

            {product.verified === false && product.grounding && product.grounding.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--cream-100)" }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: "var(--gold-600)" }}>Unverified · sourced from web</span>
                    {product.grounding.map((g, gi) => {
                        const value = formatFieldValue(product[g.field as keyof Product])
                        if (!value) return null
                        const sites = Array.from(new Map(g.citations.map(c => [hostOf(c.url), c])).values())
                        return (
                            <div key={gi} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
                                <p style={{ margin: 0, fontSize: 12, lineHeight: 1.4, minWidth: 0 }}>
                                    <span style={{ color: "var(--muted)" }}>{FIELD_LABELS[g.field] ?? g.field}: </span>
                                    <span style={{ color: "var(--green-900)", fontWeight: 700 }}>{value}</span>
                                </p>
                                {sites.length > 0 && <SourcesPill sites={sites} />}
                            </div>
                        )
                    })}
                </div>
            )}

            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 12, fontSize: 11.5, fontWeight: 700, color: "var(--gold-600)" }}>
                Expand full product card
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </div>
        </div>
    )
}
