"use client"

import { useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import type { Product } from "@/types/product"
import { statusAccent } from "@/utils/halalStatus"
import ProductDetailContent from "./ProductDetailContent"

type ProductDetailModalProps = {
    product: Product | null
    onClose: () => void
}

export default function ProductDetailModal({ product, onClose }: ProductDetailModalProps) {
    useEffect(() => {
        if (!product) return

        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose()
        }

        document.addEventListener("keydown", handleKeyDown)
        document.body.style.overflow = "hidden"

        return () => {
            document.removeEventListener("keydown", handleKeyDown)
            document.body.style.overflow = ""
        }
    }, [product, onClose])

    return (
        <AnimatePresence>
            {product && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
                    <motion.button
                        type="button"
                        aria-label="Close dialog"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        onClick={onClose}
                        className="absolute inset-0 bg-black/70 backdrop-blur-sm cursor-default"
                    />

                    <motion.div
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="product-detail-title"
                        initial={{ opacity: 0, scale: 0.96, y: 12 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.96, y: 8 }}
                        transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                        className="relative w-[80%] max-w-[600px] max-h-[70vh] flex flex-col rounded-2xl border border-white/10 bg-[#0c0c0c] shadow-2xl shadow-black/60 overflow-hidden"
                    >
                        <div
                            className={`absolute left-0 top-0 bottom-0 w-[3px] ${statusAccent(product.halal_status ?? "")}`}
                        />

                        <div className="flex items-start justify-between gap-x-4 pl-5 pr-4 pt-5 pb-3 border-b border-white/6 shrink-0">
                            <h2
                                id="product-detail-title"
                                className="text-base sm:text-lg text-white switzer-500 capitalize leading-snug pr-2"
                            >
                                {product.norm_name}
                            </h2>
                            <button
                                type="button"
                                onClick={onClose}
                                aria-label="Close"
                                className="shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-white/40 hover:text-white cursor-pointer hover:bg-white/6 transition-colors"
                            >
                                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                                    <path
                                        d="M1 1L13 13M13 1L1 13"
                                        stroke="currentColor"
                                        strokeWidth="1.5"
                                        strokeLinecap="round"
                                    />
                                </svg>
                            </button>
                        </div>

                        <div className="overflow-y-auto scrollbar-thin-dark pl-5 pr-4 py-4">
                            <ProductDetailContent product={product} />
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    )
}
