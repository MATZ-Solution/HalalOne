"use client"

import { useEffect, useRef } from "react"
import type { Theme } from "@/components/markdown/Markdown"

const SCANNER_ELEMENT_ID = "halalify-qr-scanner"

type Props = {
    onDetected: (query: string) => void
    onClose: () => void
    theme: Theme
}

export default function QRBarcodeScanner({ onDetected, onClose, theme }: Props) {
    const onDetectedRef = useRef(onDetected)
    onDetectedRef.current = onDetected

    const isLight = theme === "light"

    useEffect(() => {
        let mounted = true
        let scanner: import("html5-qrcode").Html5Qrcode | null = null
        let hasDetected = false

        import("html5-qrcode").then(({ Html5Qrcode }) => {
            if (!mounted) return

            scanner = new Html5Qrcode(SCANNER_ELEMENT_ID)

            scanner
                .start(
                    { facingMode: "environment" },
                    { fps: 10, qrbox: { width: 220, height: 220 } },
                    (decodedText: string, decodedResult: any) => {
                        if (hasDetected) return
                        hasDetected = true

                        const formatName: string =
                            decodedResult?.result?.format?.formatName ?? ""
                        const isQR = formatName === "QR_CODE"
                        const query = isQR
                            ? decodedText.trim()
                            : `Is the product with barcode ${decodedText.trim()} halal?`

                        scanner!
                            .stop()
                            .catch(() => {})
                            .finally(() => {
                                scanner?.clear()
                                onDetectedRef.current(query)
                            })
                    },
                    () => {}
                )
                .catch((err: Error) => console.error("Scanner start error:", err))
        })

        return () => {
            mounted = false
            if (scanner) {
                scanner.stop().catch(() => {}).finally(() => scanner?.clear())
            }
        }
    }, [])

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div
                className="absolute inset-0 bg-black/50 backdrop-blur-sm"
                onClick={onClose}
            />

            <div
                className={`relative z-10 w-[90vw] max-w-sm rounded-2xl overflow-hidden shadow-2xl border ${
                    isLight
                        ? "bg-white border-black/10"
                        : "bg-neutral-950 border-white/10"
                }`}
            >
                <div className="flex items-center justify-between px-4 pt-4 pb-2">
                    <p className={`switzer-500 text-sm ${isLight ? "text-black" : "text-white"}`}>
                        Scan QR or Barcode
                    </p>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Close scanner"
                        className={`w-6 h-6 flex items-center justify-center rounded-full transition-colors ${
                            isLight
                                ? "text-black/40 hover:text-black hover:bg-black/5"
                                : "text-white/40 hover:text-white hover:bg-white/10"
                        }`}
                    >
                        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden>
                            <path
                                d="M1 1L9 9M9 1L1 9"
                                stroke="currentColor"
                                strokeWidth="1.5"
                                strokeLinecap="round"
                            />
                        </svg>
                    </button>
                </div>

                <div id={SCANNER_ELEMENT_ID} className="w-full" />

                <p className={`text-xs text-center px-4 py-3 switzer-400 ${
                    isLight ? "text-black/40" : "text-white/40"
                }`}>
                    Point camera at a QR code or barcode
                </p>
            </div>
        </div>
    )
}
