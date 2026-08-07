"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { createClient } from "@/utils/supabase/client"

type Theme = "light" | "dark"

type AttachedImage = {
    previewUrl: string
    base64: string
    mimeType: string
}

type FieldValue = string | string[]

type Field = {
    key: string
    value: FieldValue
    isCustom: boolean
}

type Props = {
    image: AttachedImage
    theme: Theme
    onConfirm: (fields: Record<string, FieldValue>, message: string, imageDataUrl: string) => void
    onClose: () => void
}

const FIELD_LABELS: Record<string, string> = {
    norm_name: "Product Name",
    companies: "Companies",
    cert_bodies: "Certification Bodies",
    typical_uses: "Typical Uses",
    marketplace: "Marketplace",
    category_l1: "Category",
    category_l2: "Subcategory",
    halal_status: "Halal Status",
    sold_in: "Sold In",
    cert_numbers: "Cert. Numbers",
    health_info: "Health Info",
    fda_numbers: "FDA Numbers",
    barcodes: "Barcodes",
}

const LIST_FIELD_KEYS = new Set([
    "companies", "cert_bodies", "typical_uses", "marketplace",
    "sold_in", "cert_numbers", "health_info", "fda_numbers", "barcodes",
])

const KNOWN_FIELD_ORDER = [
    "norm_name", "companies", "cert_bodies", "typical_uses", "marketplace",
    "category_l1", "category_l2", "halal_status", "sold_in", "cert_numbers",
    "health_info", "fda_numbers", "barcodes",
]

function fieldLabel(key: string): string {
    return FIELD_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())
}

function isListType(key: string, value: FieldValue): boolean {
    return LIST_FIELD_KEYS.has(key) || Array.isArray(value)
}

function getBackendHttpUrl(): string {
    const wsUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"
    return wsUrl
}

// If extraction hasn't returned within this window, abort the request and tell
// the user instead of leaving the dialog spinning indefinitely.
const EXTRACTION_TIMEOUT_MS = 30_000

function buildInitialFields(extracted: Record<string, unknown>): Field[] {
    const fields: Field[] = []
    const seen = new Set<string>()

    for (const key of KNOWN_FIELD_ORDER) {
        seen.add(key)
        const raw = extracted[key]
        if (Array.isArray(raw)) {
            fields.push({ key, value: raw.filter((v): v is string => typeof v === "string"), isCustom: false })
        } else if (typeof raw === "string") {
            fields.push({ key, value: raw, isCustom: false })
        } else {
            fields.push({ key, value: LIST_FIELD_KEYS.has(key) ? [] : "", isCustom: false })
        }
    }

    for (const key of Object.keys(extracted)) {
        if (seen.has(key) || key === "error") continue
        const raw = extracted[key]
        if (Array.isArray(raw)) {
            fields.push({ key, value: raw.filter((v): v is string => typeof v === "string"), isCustom: false })
        } else if (typeof raw === "string") {
            fields.push({ key, value: raw, isCustom: false })
        }
    }

    return fields
}

function StringInput({
    value, onChange, placeholder, isLight,
}: {
    value: string
    onChange: (v: string) => void
    placeholder?: string
    isLight: boolean
}) {
    return (
        <input
            type="text"
            value={value}
            onChange={e => onChange(e.target.value)}
            placeholder={placeholder}
            className={`w-full px-2 py-1 rounded text-sm switzer-400 border focus:outline-none transition-colors ${isLight
                    ? "bg-black/4 border-black/10 text-black placeholder:text-black/25 focus:border-black/25"
                    : "bg-white/4 border-white/10 text-white placeholder:text-white/25 focus:border-white/25"
                }`}
        />
    )
}

function ListInput({
    values, onChange, isLight,
}: {
    values: string[]
    onChange: (v: string[]) => void
    isLight: boolean
}) {
    const [draft, setDraft] = useState("")

    const add = () => {
        const t = draft.trim()
        if (t) { onChange([...values, t]); setDraft("") }
    }

    return (
        <div className="flex flex-col gap-y-1.5">
            {values.length > 0 && (
                <div className="flex flex-wrap gap-1">
                    {values.map((v, i) => (
                        <span
                            key={i}
                            className={`flex items-center gap-x-1 text-xs switzer-400 px-2 py-0.5 rounded-full border ${isLight
                                    ? "bg-black/5 border-black/10 text-black/70"
                                    : "bg-white/5 border-white/10 text-white/70"
                                }`}
                        >
                            {v}
                            <button
                                type="button"
                                onClick={() => onChange(values.filter((_, j) => j !== i))}
                                className={`leading-none ml-0.5 transition-colors ${isLight ? "hover:text-red-500" : "hover:text-red-400"}`}
                                aria-label={`Remove ${v}`}
                            >
                                ×
                            </button>
                        </span>
                    ))}
                </div>
            )}
            <div className="flex gap-x-1.5">
                <input
                    type="text"
                    value={draft}
                    onChange={e => setDraft(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && (e.preventDefault(), add())}
                    placeholder="Add item…"
                    className={`flex-1 px-2 py-0.5 rounded text-xs switzer-400 border focus:outline-none transition-colors ${isLight
                            ? "bg-black/4 border-black/10 text-black/70 placeholder:text-black/25 focus:border-black/25"
                            : "bg-white/4 border-white/10 text-white/70 placeholder:text-white/25 focus:border-white/25"
                        }`}
                />
                <button
                    type="button"
                    onClick={add}
                    className={`px-2 py-0.5 rounded text-xs switzer-400 border transition-colors ${isLight
                            ? "border-black/10 text-black/40 hover:text-black hover:border-black/25"
                            : "border-white/10 text-white/40 hover:text-white hover:border-white/25"
                        }`}
                >
                    +
                </button>
            </div>
        </div>
    )
}

export default function ImageExtractionDialog({ image, theme, onConfirm, onClose }: Props) {
    const isLight = theme === "light"
    const [fields, setFields] = useState<Field[]>([])
    const [loading, setLoading] = useState(true)
    const [extractionError, setExtractionError] = useState<string | null>(null)
    const [message, setMessage] = useState("")
    const [newFieldKey, setNewFieldKey] = useState("")
    const [addingField, setAddingField] = useState(false)
    // Set when the extraction exceeds EXTRACTION_TIMEOUT_MS: the request is
    // aborted and the dialog switches to a "timed out" state.
    const [timedOut, setTimedOut] = useState(false)

    useEffect(() => {
        const controller = new AbortController()
        // Distinguish an abort caused by our own timeout from one caused by the
        // effect cleanup (unmount / prop change), which must stay silent.
        let didTimeout = false
        const timeoutId = setTimeout(() => {
            didTimeout = true
            controller.abort()
        }, EXTRACTION_TIMEOUT_MS)

        ;(async () => {
            const supabase = createClient()
            const { data: { session } } = await supabase.auth.getSession()
            const token = session?.access_token ?? ""
            try {
                const r = await fetch(`${getBackendHttpUrl()}/extract-image`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({ base64: image.base64, mime_type: image.mimeType }),
                    signal: controller.signal,
                })
                clearTimeout(timeoutId)
                if (!r.ok) throw new Error(`HTTP ${r.status}`)
                const data = await r.json() as { fields: Record<string, unknown> }
                setFields(buildInitialFields(data.fields ?? {}))
                setLoading(false)
            } catch (err) {
                clearTimeout(timeoutId)
                if ((err as Error).name === "AbortError") {
                    // Timed out → inform the user; the request is already cancelled.
                    if (didTimeout) {
                        setTimedOut(true)
                        setLoading(false)
                    }
                    // Otherwise it was a cleanup abort — stay silent.
                    return
                }
                setExtractionError("Could not extract information from this image. You can fill in the fields manually.")
                setFields(buildInitialFields({}))
                setLoading(false)
            }
        })()

        return () => {
            clearTimeout(timeoutId)
            controller.abort()
        }
    }, [image.base64, image.mimeType])

    useEffect(() => {
        const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
        document.addEventListener("keydown", onKey)
        document.body.style.overflow = "hidden"
        return () => {
            document.removeEventListener("keydown", onKey)
            document.body.style.overflow = ""
        }
    }, [onClose])

    const updateField = (idx: number, value: FieldValue) => {
        setFields(prev => prev.map((f, i) => i === idx ? { ...f, value } : f))
    }

    const removeField = (idx: number) => {
        setFields(prev => prev.filter((_, i) => i !== idx))
    }

    const addCustomField = () => {
        const key = newFieldKey.trim().replace(/\s+/g, "_").toLowerCase()
        if (!key) return
        setFields(prev => [...prev, { key, value: "", isCustom: true }])
        setNewFieldKey("")
        setAddingField(false)
    }

    // Leave the timed-out state and drop into the empty manual-entry form.
    const handleManualEntry = () => {
        setFields(buildInitialFields({}))
        setExtractionError("Enter the product details manually below.")
        setTimedOut(false)
    }

    const handleConfirm = () => {
        const out: Record<string, FieldValue> = {}
        for (const f of fields) {
            if (Array.isArray(f.value)) {
                if (f.value.length > 0) out[f.key] = f.value
            } else if (f.value.trim()) {
                out[f.key] = f.value.trim()
            }
        }
        const imageDataUrl = `data:${image.mimeType};base64,${image.base64}`
        onConfirm(out, message.trim(), imageDataUrl)
    }

    const hasContent = fields.some(f =>
        Array.isArray(f.value) ? f.value.length > 0 : f.value.trim().length > 0
    ) || message.trim().length > 0

    const overlayBg = isLight ? "bg-black/50" : "bg-black/70"
    const dialogBg = isLight ? "bg-white border-black/10" : "bg-[#0c0c0c] border-white/10"
    const dividerCls = isLight ? "border-black/8" : "border-white/8"
    const labelCls = isLight ? "text-black/50" : "text-white/50"
    const sublabelCls = isLight ? "text-black/30" : "text-white/30"
    const headingCls = isLight ? "text-black" : "text-white"

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.button
                type="button"
                aria-label="Close"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                onClick={onClose}
                className={`absolute inset-0 ${overlayBg} backdrop-blur-sm cursor-default`}
            />

            <motion.div
                role="dialog"
                aria-modal="true"
                aria-label="Product Image Analysis"
                initial={{ opacity: 0, scale: 0.96, y: 12 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96, y: 8 }}
                transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                className={`relative w-full max-w-lg max-h-[85vh] flex flex-col rounded-2xl border shadow-2xl overflow-hidden ${dialogBg}`}
            >
                {/* Header */}
                <div className={`flex items-center justify-between px-5 pt-5 pb-4 border-b shrink-0 ${dividerCls}`}>
                    <div className="flex items-center gap-x-3 min-w-0">
                        <img
                            src={image.previewUrl}
                            alt="Uploaded product"
                            className="w-10 h-10 rounded-lg object-cover shrink-0"
                        />
                        <div className="min-w-0">
                            <h2 className={`switzer-500 text-sm ${headingCls}`}>
                                Product Image Analysis
                            </h2>
                            <p className={`switzer-400 text-xs mt-0.5 ${sublabelCls}`}>
                                {loading
                                    ? "Extracting product information…"
                                    : timedOut
                                        ? "Analysis timed out"
                                        : extractionError
                                            ? "Manual entry"
                                            : "Review and edit the extracted fields"}
                            </p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Close"
                        className={`shrink-0 w-8 h-8 flex items-center justify-center rounded-lg transition-colors ${isLight
                                ? "text-black/40 hover:text-black hover:bg-black/6"
                                : "text-white/40 hover:text-white hover:bg-white/6"
                            }`}
                    >
                        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                            <path d="M1 1L11 11M11 1L1 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                        </svg>
                    </button>
                </div>

                {/* Scrollable body */}
                <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-y-4">
                    {loading ? (
                        <div className="flex flex-col gap-y-4">
                            {Array.from({ length: 6 }).map((_, i) => (
                                <div key={i} className="flex flex-col gap-y-1.5">
                                    <div className={`h-3 w-20 rounded-sm animate-pulse ${isLight ? "bg-black/8" : "bg-white/8"}`} />
                                    <div className={`h-7 w-full rounded animate-pulse ${isLight ? "bg-black/5" : "bg-white/5"}`} />
                                </div>
                            ))}
                        </div>
                    ) : timedOut ? (
                        <div className="flex flex-col items-center text-center gap-y-3 py-8">
                            <div className={`w-11 h-11 rounded-full flex items-center justify-center ${isLight ? "bg-black/5" : "bg-white/5"}`}>
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className={isLight ? "text-black/50" : "text-white/50"} aria-hidden="true">
                                    <circle cx="12" cy="12" r="9" />
                                    <path d="M12 7v5l3 2" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            </div>
                            <p className={`text-sm switzer-500 ${headingCls}`}>Image analysis timed out</p>
                            <p className={`text-xs switzer-400 max-w-xs ${sublabelCls}`}>
                                We couldn&apos;t read this image in time, so the request was cancelled. Try again with a clearer photo, or fill in the fields yourself.
                            </p>
                            <div className="flex items-center gap-x-2 mt-1">
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className={`px-3 py-1.5 rounded-lg text-sm switzer-400 transition-colors ${isLight
                                            ? "text-black/50 hover:text-black hover:bg-black/5"
                                            : "text-white/50 hover:text-white hover:bg-white/5"
                                        }`}
                                >
                                    Close
                                </button>
                                <button
                                    type="button"
                                    onClick={handleManualEntry}
                                    className={`px-4 py-1.5 rounded-lg text-sm switzer-500 transition-colors ${isLight
                                            ? "bg-black text-white hover:bg-black/80"
                                            : "bg-white text-black hover:bg-white/85"
                                        }`}
                                >
                                    Fill in the fields manually
                                </button>
                            </div>
                        </div>
                    ) : (
                        <>
                            {extractionError && (
                                <p className={`text-xs switzer-400 px-3 py-2 rounded-lg border ${isLight
                                        ? "text-black/50 border-black/8 bg-black/3"
                                        : "text-white/50 border-white/8 bg-white/3"
                                    }`}>
                                    {extractionError}
                                </p>
                            )}

                            <div className="flex flex-col gap-y-3">
                                {fields.map((field, idx) => (
                                    <div key={`${field.key}-${idx}`} className="flex flex-col gap-y-1">
                                        <div className="flex items-center justify-between">
                                            <label className={`text-xs switzer-500 ${labelCls}`}>
                                                {fieldLabel(field.key)}
                                            </label>
                                            {field.isCustom && (
                                                <button
                                                    type="button"
                                                    onClick={() => removeField(idx)}
                                                    className={`text-xs switzer-400 transition-colors ${isLight ? "text-black/25 hover:text-red-500" : "text-white/25 hover:text-red-400"
                                                        }`}
                                                >
                                                    Remove
                                                </button>
                                            )}
                                        </div>
                                        {isListType(field.key, field.value) ? (
                                            <ListInput
                                                values={Array.isArray(field.value) ? field.value : field.value ? [field.value] : []}
                                                onChange={v => updateField(idx, v)}
                                                isLight={isLight}
                                            />
                                        ) : (
                                            <StringInput
                                                value={typeof field.value === "string" ? field.value : ""}
                                                onChange={v => updateField(idx, v)}
                                                placeholder="Not detected"
                                                isLight={isLight}
                                            />
                                        )}
                                    </div>
                                ))}
                            </div>

                            {/* Add custom field */}
                            <AnimatePresence mode="wait">
                                {addingField ? (
                                    <motion.div
                                        key="adding"
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: "auto" }}
                                        exit={{ opacity: 0, height: 0 }}
                                        className="overflow-hidden"
                                    >
                                        <div className="flex gap-x-2 pt-1">
                                            <input
                                                type="text"
                                                value={newFieldKey}
                                                onChange={e => setNewFieldKey(e.target.value)}
                                                onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addCustomField())}
                                                placeholder="Field name"
                                                autoFocus
                                                className={`flex-1 px-2 py-1 rounded text-sm switzer-400 border focus:outline-none transition-colors ${isLight
                                                        ? "bg-black/4 border-black/10 text-black placeholder:text-black/25 focus:border-black/25"
                                                        : "bg-white/4 border-white/10 text-white placeholder:text-white/25 focus:border-white/25"
                                                    }`}
                                            />
                                            <button
                                                type="button"
                                                onClick={addCustomField}
                                                className={`px-3 py-1 rounded text-sm switzer-500 transition-colors ${isLight
                                                        ? "bg-black/8 text-black hover:bg-black/12"
                                                        : "bg-white/8 text-white hover:bg-white/12"
                                                    }`}
                                            >
                                                Add
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => { setAddingField(false); setNewFieldKey("") }}
                                                className={`px-2 py-1 rounded text-sm switzer-400 transition-colors ${isLight ? "text-black/40 hover:text-black" : "text-white/40 hover:text-white"
                                                    }`}
                                            >
                                                Cancel
                                            </button>
                                        </div>
                                    </motion.div>
                                ) : (
                                    <motion.button
                                        key="add-btn"
                                        type="button"
                                        onClick={() => setAddingField(true)}
                                        className={`flex items-center gap-x-1.5 text-xs switzer-400 transition-colors w-max ${isLight
                                                ? "text-black/35 hover:text-black/70"
                                                : "text-white/35 hover:text-white/70"
                                            }`}
                                    >
                                        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
                                            <path d="M5 1V9M1 5H9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                                        </svg>
                                        Add custom field
                                    </motion.button>
                                )}
                            </AnimatePresence>
                        </>
                    )}
                </div>

                {/* Footer: message + actions */}
                {!loading && !timedOut && (
                    <div className={`shrink-0 border-t px-5 pt-4 pb-5 flex flex-col gap-y-3 ${dividerCls}`}>
                        <div className="flex flex-col gap-y-1">
                            <label className={`text-xs switzer-500 ${labelCls}`}>
                                Message{" "}
                                <span className={`switzer-400 ${sublabelCls}`}>(optional)</span>
                            </label>
                            <textarea
                                value={message}
                                onChange={e => setMessage(e.target.value)}
                                onKeyDown={e => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault()
                                        if (hasContent) handleConfirm()
                                    }
                                }}
                                rows={2}
                                placeholder="Is this product halal?"
                                className={`w-full px-2 py-1.5 rounded text-sm switzer-400 border focus:outline-none resize-none transition-colors ${isLight
                                        ? "bg-black/4 border-black/10 text-black placeholder:text-black/25 focus:border-black/25"
                                        : "bg-white/4 border-white/10 text-white placeholder:text-white/25 focus:border-white/25"
                                    }`}
                            />
                        </div>

                        <div className="flex items-center justify-end gap-x-2">
                            <button
                                type="button"
                                onClick={onClose}
                                className={`px-3 py-1.5 rounded-lg text-sm switzer-400 transition-colors ${isLight
                                        ? "text-black/50 hover:text-black hover:bg-black/5"
                                        : "text-white/50 hover:text-white hover:bg-white/5"
                                    }`}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={handleConfirm}
                                disabled={!hasContent}
                                className={`px-4 py-1.5 rounded-lg text-sm switzer-500 transition-colors ${hasContent
                                        ? isLight
                                            ? "bg-black text-white hover:bg-black/80"
                                            : "bg-white text-black hover:bg-white/85"
                                        : isLight
                                            ? "bg-black/10 text-black/30 cursor-not-allowed"
                                            : "bg-white/10 text-white/30 cursor-not-allowed"
                                    }`}
                            >
                                Confirm &amp; Search
                            </button>
                        </div>
                    </div>
                )}
            </motion.div>
        </div>
    )
}
