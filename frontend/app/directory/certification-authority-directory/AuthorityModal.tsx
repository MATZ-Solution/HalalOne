"use client"

import { useEffect } from "react"
import type { Authority } from "./authorities"
import { codeOf, codeSize, dotFor, segs, typeGroup, typeStyle } from "./logic"

const HEX_CLIP =
  "[clip-path:polygon(50%_0,100%_27%,100%_73%,50%_100%,0_73%,0_27%)]"

const Label = ({ children }: { children: React.ReactNode }) => (
  <div className="plus-jakarta-sans-700 mb-1 text-[10.5px] tracking-[.07em] uppercase text-ho-faint-2">
    {children}
  </div>
)

export default function AuthorityModal({
  authority,
  onClose,
}: {
  authority: Authority
  onClose: () => void
}) {
  // Freeze the page behind the modal and allow Escape to close it — same
  // treatment as the app's other overlay (components/HamburgerMenu.tsx).
  useEffect(() => {
    const previous = document.body.style.overflow
    document.body.style.overflow = "hidden"
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    window.addEventListener("keydown", onKey)
    return () => {
      document.body.style.overflow = previous
      window.removeEventListener("keydown", onKey)
    }
  }, [onClose])

  const a = authority
  const group = typeGroup(a.type)
  const ts = typeStyle(group)
  const code = codeOf(a.name)
  const hasUrl = Boolean(a.href && a.urlText)

  return (
    <div
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`${a.name} details`}
      className="fixed inset-0 z-80 flex items-start justify-center overflow-y-auto bg-[rgba(9,32,21,.55)] px-5 py-10 backdrop-blur-[4px]"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="animate-ho-pop my-auto w-full max-w-[640px] overflow-hidden rounded-[22px] bg-ho-bg shadow-[0_40px_90px_-30px_rgba(6,28,18,.7)]"
      >
        <div className="relative bg-[radial-gradient(120%_160%_at_85%_0,#155B3C,#0C3826)] px-5 pt-[26px] pb-6 text-white sm:px-7">
          <button
            type="button"
            onClick={onClose}
            aria-label="Close details"
            className="absolute top-5 right-5 flex h-[34px] w-[34px] cursor-pointer items-center justify-center rounded-[9px] border-none bg-white/12 text-[17px] text-white transition-colors hover:bg-white/20"
          >
            ✕
          </button>
          <div className="flex items-center gap-[15px]">
            <div
              className={`flex h-16 w-[58px] flex-none items-center justify-center border border-ho-gold/40 bg-ho-gold/16 ${HEX_CLIP}`}
            >
              <span
                className={`${codeSize(code)} plus-jakarta-sans-800 tracking-[-.02em] text-ho-gold-lt`}
              >
                {code}
              </span>
            </div>
            <div className="min-w-0 pr-10">
              {/* Full type string, which runs long ("Government (Accreditation &
                  Standards Body)") — must wrap rather than push the panel wide. */}
              <div
                className="plus-jakarta-sans-700 mb-2 inline-block rounded-[20px] px-[9px] py-[3px] text-[10.5px] tracking-[.03em]"
                style={{ background: ts.bg, color: ts.fg }}
              >
                {a.type}
              </div>
              <div className="plus-jakarta-sans-800 text-xl leading-[1.1] tracking-[-.02em] sm:text-[23px]">
                {a.name}
              </div>
              <div className="mt-1 text-[13px] leading-[1.4] text-ho-mint">
                {a.fullName}
              </div>
            </div>
          </div>
        </div>

        <div className="px-5 pt-6 pb-7 sm:px-7">
          <div className="mb-[22px] grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
            <div>
              <Label>Country / Region</Label>
              <div className="plus-jakarta-sans-600 flex items-center gap-[7px] text-[14px] text-ho-ink-3">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ background: dotFor(a.region) }}
                />
                {a.country} · {a.region}
              </div>
            </div>
            <div>
              <Label>Established</Label>
              <div className="plus-jakarta-sans-600 text-[14px] text-ho-ink-3">
                {a.est}
              </div>
            </div>
            <div>
              <Label>Certificate validity</Label>
              <div className="plus-jakarta-sans-600 text-[14px] text-ho-ink-3">
                {a.validity}
              </div>
            </div>
            <div>
              <Label>Est. records in DB</Label>
              <div className="plus-jakarta-sans-700 text-[14px] text-ho-gold-dk">
                {a.records}
              </div>
            </div>
          </div>

          <div className="mb-5">
            <Label>Halal standard</Label>
            <div className="rounded-[10px] border border-ho-green/8 bg-ho-tint-2 px-[13px] py-[11px] text-[13.5px] leading-[1.5] text-[#33413A]">
              {a.standard}
            </div>
          </div>

          <div className="mb-5">
            <Label>Product scope</Label>
            <div className="flex flex-wrap gap-[7px]">
              {segs(a.scope).map((tag) => (
                <span
                  key={tag}
                  className="plus-jakarta-sans-600 max-w-full rounded-lg border border-ho-green/10 bg-ho-tint px-[11px] py-[5px] text-[12px] text-[#3E5B4B]"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <div className="mb-5">
            <Label>Recognised by</Label>
            <div className="flex flex-wrap gap-[7px]">
              {/* Several of these are full sentences (HMC's runs to 93 chars),
                  so they must wrap. */}
              {segs(a.recognised).map((rg) => (
                <span
                  key={rg}
                  className="plus-jakarta-sans-500 max-w-full rounded-lg border border-ho-gold/35 bg-[#FBF3DE] px-[11px] py-[5px] text-[12px] text-[#5A4A16]"
                >
                  {rg}
                </span>
              ))}
            </div>
          </div>

          <div className="mb-[22px]">
            <Label>Notes</Label>
            <p className="m-0 text-[13.5px] leading-[1.62] text-[#4A574F]">
              {a.notes}
            </p>
          </div>

          {hasUrl ? (
            <a
              href={a.href}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between gap-3 rounded-xl bg-ho-green px-[18px] py-[14px] text-white no-underline transition-colors hover:bg-ho-green-dk"
            >
              <span>
                <span className="plus-jakarta-sans-600 block text-[11px] tracking-[.04em] text-ho-mint-2">
                  VERIFICATION PORTAL
                </span>
                <span className="plus-jakarta-sans-600 mt-[2px] block wrap-anywhere text-[13.5px] text-white">
                  {a.urlText}
                </span>
              </span>
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                className="flex-none"
                aria-hidden
              >
                <path
                  d="M7 17 17 7M9 7h8v8"
                  stroke="#C9A248"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </a>
          ) : (
            <div className="plus-jakarta-sans-500 flex items-center gap-[10px] rounded-xl border border-dashed border-ho-green/20 bg-ho-tint-2 px-[18px] py-[14px] text-[13px] text-ho-muted-3">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                className="flex-none"
                aria-hidden
              >
                <path
                  d="M12 8v5m0 3h.01M12 3l9 16H3z"
                  stroke="#9AA69E"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              No public verification portal — verify directly with the authority.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
