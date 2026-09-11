"use client"

import { useEffect, useRef } from "react"
import { motion } from "framer-motion"

type Theme = "light" | "dark"

type Props = {
    theme: Theme
    onProceedToUpload: () => void
    onFileSelected?: (file: File) => void
    onClose: () => void
}

export default function ImageUploadGuidanceDialog({
    theme,
    onProceedToUpload,
    onFileSelected,
    onClose,
}: Props) {
    const isLight = theme === "light"
    const fileInputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose()
        }
        document.addEventListener("keydown", onKey)
        document.body.style.overflow = "hidden"
        return () => {
            document.removeEventListener("keydown", onKey)
            document.body.style.overflow = ""
        }
    }, [onClose])

    const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file && file.type.startsWith("image/")) {
            if (onFileSelected) {
                onFileSelected(file)
            } else {
                onProceedToUpload()
            }
        }
    }

    const overlayBg = isLight ? "bg-black/50" : "bg-black/70"
    const dialogBg = isLight ? "bg-white border-black/10 text-black" : "bg-[#0c0c0c] border-white/10 text-white"
    const dividerCls = isLight ? "border-black/8" : "border-white/8"
    const sublabelCls = isLight ? "text-black/40" : "text-white/40"
    const cardHighlight = isLight ? "bg-emerald-50 border-emerald-200/80" : "bg-emerald-950/20 border-emerald-500/20"
    const cardWarning = isLight ? "bg-amber-50/70 border-amber-200/70" : "bg-amber-950/20 border-amber-500/20"

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4">
            {/* Backdrop */}
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

            {/* Hidden file input */}
            <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFileInputChange}
            />

            {/* Modal Dialog */}
            <motion.div
                role="dialog"
                aria-modal="true"
                aria-label="Product Image Upload Guidelines"
                initial={{ opacity: 0, scale: 0.96, y: 12 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96, y: 8 }}
                transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                className={`relative w-full max-w-lg max-h-[92vh] flex flex-col rounded-2xl border shadow-2xl overflow-hidden ${dialogBg}`}
            >
                {/* Header */}
                <div className={`px-5 py-4 flex items-center justify-between border-b ${dividerCls}`}>
                    <div className="flex items-center gap-x-2.5">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${isLight ? "bg-black/5 text-black" : "bg-white/10 text-white"}`}>
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                        </div>
                        <div>
                            <h2 className="switzer-600 text-base leading-tight">Product Image Guidelines</h2>
                            <p className={`switzer-400 text-xs ${sublabelCls}`}>Best practices for accurate AI verification</p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Close dialog"
                        className={`w-7 h-7 rounded-full flex items-center justify-center transition-colors text-sm ${isLight ? "hover:bg-black/5 text-black/50 hover:text-black" : "hover:bg-white/10 text-white/50 hover:text-white"}`}
                    >
                        ✕
                    </button>
                </div>

                {/* Scrollable Content */}
                <div className="px-5 py-4 overflow-y-auto flex flex-col gap-y-4">
                    {/* Guidance Notice Banner */}
                    <div className={`p-3.5 rounded-xl border flex items-start gap-x-3 ${cardHighlight}`}>
                        <div className="shrink-0 mt-0.5 text-emerald-600 dark:text-emerald-400">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <p className="switzer-400 text-xs sm:text-sm leading-relaxed text-emerald-950 dark:text-emerald-100">
                            <span className="switzer-600">For highest accuracy and best extraction results:</span> Please upload a <span className="switzer-600 underline decoration-emerald-500/50">clear, well-lit, front-side photo</span> of the product packaging where the name & brand are clearly visible.
                        </p>
                    </div>

                    {/* Visual Product Examples */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <span className={`switzer-500 text-xs tracking-wider uppercase ${sublabelCls}`}>
                                Example Comparison
                            </span>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {/* Recommended: Front & Clear */}
                            <div className={`p-3 rounded-xl border flex flex-col gap-y-2.5 ${cardHighlight}`}>
                                <div className="flex items-center justify-between">
                                    <span className="inline-flex items-center gap-x-1 px-2 py-0.5 rounded-full text-[11px] switzer-600 bg-emerald-600 text-white">
                                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                        </svg>
                                        Recommended
                                    </span>
                                    <span className="switzer-400 text-[11px] text-emerald-700 dark:text-emerald-300">Front Side</span>
                                </div>

                                {/* Recommended Product Photo */}
                                <div className={`relative h-32 rounded-lg overflow-hidden border border-emerald-500/30 flex items-center justify-center ${isLight ? "bg-white" : "bg-black/40"}`}>
                                    <img
                                        src="/images/good_product_example.jpg"
                                        alt="Recommended front product example"
                                        className="w-full h-full object-contain p-1"
                                    />
                                    <div className="absolute bottom-1.5 right-2 px-1.5 py-0.5 rounded text-[10px] switzer-600 bg-emerald-600 text-white shadow-sm flex items-center gap-x-1">
                                        ✓ Front Side & Clear
                                    </div>
                                </div>

                                <ul className="text-[11px] switzer-400 space-y-1 text-emerald-900 dark:text-emerald-200">
                                    <li className="flex items-center gap-x-1.5">
                                        <span className="text-emerald-600 font-bold">•</span> Front-facing packaging
                                    </li>
                                    <li className="flex items-center gap-x-1.5">
                                        <span className="text-emerald-600 font-bold">•</span> Crisp text & visible brand
                                    </li>
                                    <li className="flex items-center gap-x-1.5">
                                        <span className="text-emerald-600 font-bold">•</span> Even lighting without glare
                                    </li>
                                </ul>
                            </div>

                            {/* Avoid: Back side / Blurry */}
                            <div className={`p-3 rounded-xl border flex flex-col gap-y-2.5 ${cardWarning}`}>
                                <div className="flex items-center justify-between">
                                    <span className="inline-flex items-center gap-x-1 px-2 py-0.5 rounded-full text-[11px] switzer-600 bg-amber-600 text-white">
                                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                        Avoid
                                    </span>
                                    <span className="switzer-400 text-[11px] text-amber-700 dark:text-amber-300">Back Side / Angled</span>
                                </div>

                                {/* Avoid Product Photo */}
                                <div className={`relative h-32 rounded-lg overflow-hidden border border-amber-500/30 flex items-center justify-center ${isLight ? "bg-white" : "bg-black/40"}`}>
                                    <img
                                        src="/images/back_product_example.jpg"
                                        alt="Avoid back product example"
                                        className="w-full h-full object-contain p-1 opacity-80"
                                    />
                                    <div className="absolute bottom-1.5 right-2 px-1.5 py-0.5 rounded text-[10px] switzer-600 bg-amber-600 text-white shadow-sm flex items-center gap-x-1">
                                        ✗ Back / Non-Front View
                                    </div>
                                </div>

                                <ul className="text-[11px] switzer-400 space-y-1 text-amber-900 dark:text-amber-200">
                                    <li className="flex items-center gap-x-1.5">
                                        <span className="text-amber-600 font-bold">•</span> Back or plain sides without title
                                    </li>
                                    <li className="flex items-center gap-x-1.5">
                                        <span className="text-amber-600 font-bold">•</span> Blurry, dark, or out of focus
                                    </li>
                                    <li className="flex items-center gap-x-1.5">
                                        <span className="text-amber-600 font-bold">•</span> Severe angle or cropped text
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer Actions */}
                <div className={`px-5 py-3.5 flex items-center justify-end gap-x-3 border-t ${dividerCls} ${isLight ? "bg-black/[0.02]" : "bg-white/[0.02]"}`}>
                    <button
                        type="button"
                        onClick={onClose}
                        className={`px-4 py-2 rounded-xl text-xs sm:text-sm switzer-400 transition-colors ${isLight
                            ? "text-black/60 hover:text-black hover:bg-black/5"
                            : "text-white/60 hover:text-white hover:bg-white/5"
                            }`}
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        onClick={() => {
                            if (fileInputRef.current) {
                                fileInputRef.current.click()
                            } else {
                                onProceedToUpload()
                            }
                        }}
                        className={`px-5 py-2 rounded-xl text-xs sm:text-sm switzer-500 flex items-center gap-x-2 transition-all shadow-sm ${isLight
                            ? "bg-black text-white hover:bg-black/85 active:scale-[0.98]"
                            : "bg-white text-black hover:bg-white/90 active:scale-[0.98]"
                            }`}
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                        </svg>
                        Upload Image
                    </button>
                </div>
            </motion.div>
        </div>
    )
}
