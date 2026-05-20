"use client"
import useWebsocket from "@/hooks/useWebsocket"
import SendIcon from "../icons/send_icon.svg"
import ImageIcon from "../icons/image_icon.svg"
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

const THEME_STORAGE_KEY = "halalify-theme"

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
    const [theme, setTheme] = useState<Theme>("dark")
    const [textPresent, setTextPresent] = useState(false)
    const [attachedImage, setAttachedImage] = useState<AttachedImage | null>(null)
    const [results, setResults] = useState<Product[] | null>(null)
    const [agentResponse, setAgentResponse] = useState<string | null>(null)
    const [loading, setLoading] = useState(false)
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)

    const isLight = theme === "light"
    const canSend = textPresent || !!attachedImage
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
        return () => {
            if (attachedImage) URL.revokeObjectURL(attachedImage.previewUrl)
        }
    }, [attachedImage])

    useEffect(() => {
        if (!lastMessage) return
        try {
            const data = JSON.parse(lastMessage)
            if (data.type === "results") {
                setResults(data.documents)
                setAgentResponse(data.response ?? null)
                setLoading(false)
            }
        } catch { }
    }, [messageCount])

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

    const handleSend = () => {
        const text = inputRef.current?.textContent?.trim() || ""

        if (attachedImage) {
            sendMessage(
                JSON.stringify({
                    type: "image",
                    ...(text ? { message: text } : {}),
                    base64: attachedImage.base64,
                    mime_type: attachedImage.mimeType,
                })
            )
            URL.revokeObjectURL(attachedImage.previewUrl)
            setAttachedImage(null)
        } else {
            if (!text) return
            sendMessage(JSON.stringify({ type: "prompt", message: text }))
        }

        if (inputRef.current) inputRef.current.textContent = ""
        setTextPresent(false)
        setLoading(true)
        setResults(null)
        setAgentResponse(null)
        setSelectedProduct(null)
    }

    return (
        <div className={`w-screen min-h-screen transition-colors duration-300 ${isLight ? "bg-white" : "bg-black"}`}>
            <ThemeToggle theme={theme} onToggle={toggleTheme} />

            <div className="flex justify-center pt-[20vh]">
                <div className="w-[80%] md:w-[60%] lg:w-[50%] flex flex-col gap-y-6 pb-16">

                    <div>
                        <p className={`text-6xl tracking-tighter switzer-500 ${isLight ? "text-black" : "text-white"}`}>
                            Halalify
                        </p>
                        <div className="rounded-sm switzer-500 text-white text-xs bg-green-600 px-2 h-4 w-max">
                            <p>Check Halal Status</p>
                        </div>
                    </div>

                    <div className={`relative flex flex-col gap-y-2 w-full p-2 rounded-lg border ${isLight ? "border-black/30" : "border-white/30"}`}>
                        <div className="flex gap-x-2 items-end w-full">
                            <motion.div className="flex flex-col flex-1 min-w-0 gap-y-2">
                                <div className="relative">
                                    {!textPresent && !attachedImage && (
                                        <span className={`absolute left-0 top-0 switzer-400 pointer-events-none ${isLight ? "text-black/40" : "text-white/40"}`}>
                                            Is Kebabjees Crunchy Burger halal?
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
                                            const text = inputRef.current?.textContent?.trim() || ""
                                            setTextPresent(text.length > 0)
                                        }}
                                        onPaste={(e) => {
                                            e.preventDefault()
                                            const text = e.clipboardData.getData("text/plain")
                                            document.execCommand("insertText", false, text)
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
                                                className={`absolute -top-1.5 -right-1.5 w-5 h-5 flex items-center justify-center rounded-full border transition-colors ${
                                                    isLight
                                                        ? "bg-white/90 border-black/20 text-black/70 hover:text-black hover:bg-black/10"
                                                        : "bg-black/90 border-white/20 text-white/70 hover:text-white hover:bg-white/10"
                                                }`}
                                            >
                                                <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
                                                    <path
                                                        d="M1 1L9 9M9 1L1 9"
                                                        stroke="currentColor"
                                                        strokeWidth="1.5"
                                                        strokeLinecap="round"
                                                    />
                                                </svg>
                                            </button>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </motion.div>

                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                className="hidden"
                                onChange={handleImageSelect}
                            />
                            <button
                                type="button"
                                onClick={() => fileInputRef.current?.click()}
                                aria-label="Upload image"
                                className={`shrink-0 w-6 h-6 transition-colors cursor-pointer ${
                                    isLight ? "text-black/40 hover:text-black" : "text-white/40 hover:text-white/80"
                                }`}
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

                    {loading && (
                        <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: [0.3, 0.7, 0.3] }}
                            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                            className={`switzer-400 text-sm ${isLight ? "text-black/40" : "text-white/40"}`}
                        >
                            Searching relevant products...
                        </motion.p>
                    )}

                    <AnimatePresence>
                        {!loading && agentResponse && (
                            <motion.div
                                initial={{ opacity: 0, y: 4 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                transition={{ duration: 0.3 }}
                                className={`switzer-400 text-sm leading-relaxed ${isLight ? "text-black/60" : "text-white/60"}`}
                            >
                                <Markdown textContent={agentResponse} theme={theme} />
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <AnimatePresence>
                        {!loading && results && results.length > 0 && (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="flex flex-col gap-y-2"
                            >
                                {results.map((product, i) => (
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
                                        className={`relative group rounded-xl p-4 flex flex-col gap-y-3 transition-all duration-200 overflow-hidden cursor-pointer focus:outline-none ${
                                            isLight
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
                                                        <span
                                                            key={j}
                                                            className={`text-xs switzer-400 px-2 py-0.5 rounded-md border ${
                                                                isLight
                                                                    ? "text-black/40 bg-black/5 border-black/8"
                                                                    : "text-white/40 bg-white/5 border-white/8"
                                                            }`}
                                                        >
                                                            {cat}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}

                                            {product.companies && product.companies.length > 0 && (
                                                <p className={`text-sm switzer-400 leading-relaxed ${isLight ? "text-black/70" : "text-white/70"}`}>
                                                    {product.companies?.map(company =>
                                                        company.charAt(0).toUpperCase() + company.slice(1).toLowerCase()
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
                            </motion.div>
                        )}
                    </AnimatePresence>

                </div>
            </div>

            <ProductDetailModal
                product={selectedProduct}
                onClose={() => setSelectedProduct(null)}
            />
        </div>
    )
}
