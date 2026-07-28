"use client"

import type { Authority } from "./authorities"
import {
  codeOf,
  codeSize,
  dotFor,
  recText,
  segs,
  shortValidity,
  typeGroup,
  typeStyle,
} from "./logic"

const HEX_CLIP =
  "[clip-path:polygon(50%_0,100%_27%,100%_73%,50%_100%,0_73%,0_27%)]"

export default function AuthorityCard({
  authority,
  onOpen,
}: {
  authority: Authority
  onOpen: (a: Authority) => void
}) {
  const a = authority
  const group = typeGroup(a.type)
  const ts = typeStyle(group)
  const code = codeOf(a.name)
  const scopeTags = segs(a.scope).slice(0, 4)

  // `min-w-0` is load-bearing: grid items default to min-width:auto, so without
  // it a long unbreakable tag (e.g. BPJPH's 84-char scope) pushes the card —
  // and with it the whole page — wider than the viewport.
  return (
    <button
      type="button"
      onClick={() => onOpen(a)}
      aria-label={`View details for ${a.name}`}
      className="animate-ho-rise relative flex min-w-0 cursor-pointer flex-col gap-[15px] rounded-[18px] border border-ho-green/10 bg-white p-5 pb-[18px] text-left transition-[transform,box-shadow,border-color] duration-180 hover:-translate-y-1 hover:border-ho-gold/65 hover:shadow-[0_20px_40px_-22px_rgba(12,56,38,.4)] sm:p-[22px] sm:pb-[18px]"
    >
      <div
        className="absolute top-[18px] right-[18px] rounded-[20px] px-[9px] py-1 text-[10.5px] font-bold tracking-[.03em] whitespace-nowrap"
        style={{ background: ts.bg, color: ts.fg }}
      >
        {ts.label}
      </div>

      <div className="flex items-center gap-[13px]">
        <div
          className={`flex h-14 w-[52px] flex-none items-center justify-center bg-linear-[155deg,#155B3C,#0D3D2A] ${HEX_CLIP}`}
        >
          <span
            className={`${codeSize(code)} plus-jakarta-sans-800 leading-none tracking-[-.02em] text-ho-gold-lt`}
          >
            {code}
          </span>
        </div>
        <div className="min-w-0 pr-14">
          <div className="plus-jakarta-sans-700 truncate text-[17.5px] leading-[1.15] tracking-[-.02em] text-ho-ink-2">
            {a.name}
          </div>
          <div className="mt-[5px] flex items-center gap-[7px]">
            <span
              className="h-2 w-2 flex-none rounded-full"
              style={{ background: dotFor(a.region) }}
            />
            <span className="plus-jakarta-sans-600 text-[12.5px] text-ho-slate">
              {a.country}
            </span>
            <span className="text-[11.5px] text-ho-faint-2">·</span>
            <span className="plus-jakarta-sans-500 text-[12px] text-ho-faint">
              {a.region}
            </span>
          </div>
        </div>
      </div>

      <p className="m-0 line-clamp-2 min-h-[37px] text-[12.5px] leading-normal text-ho-muted-3">
        {a.fullName}
      </p>

      <div className="flex gap-[10px] border-y border-ho-green/9 py-[13px]">
        <div className="flex-1">
          <div className="plus-jakarta-sans-700 mb-[3px] text-[10px] tracking-[.06em] uppercase text-ho-faint-2">
            Est.
          </div>
          <div className="plus-jakarta-sans-700 text-[13.5px] text-ho-ink-3">
            {a.est}
          </div>
        </div>
        <div className="flex-1 border-l border-ho-green/9 pl-[10px]">
          <div className="plus-jakarta-sans-700 mb-[3px] text-[10px] tracking-[.06em] uppercase text-ho-faint-2">
            Records
          </div>
          <div className="plus-jakarta-sans-700 text-[13.5px] text-ho-gold-dk">
            {a.records}
          </div>
        </div>
        <div className="flex-[1.2] border-l border-ho-green/9 pl-[10px]">
          <div className="plus-jakarta-sans-700 mb-[3px] text-[10px] tracking-[.06em] uppercase text-ho-faint-2">
            Validity
          </div>
          <div className="plus-jakarta-sans-700 truncate text-[13.5px] text-ho-ink-3">
            {shortValidity(a.validity)}
          </div>
        </div>
      </div>

      <div className="flex min-h-[23px] flex-wrap gap-[6px]">
        {/* No whitespace-nowrap: most scopes are short "·"-separated words, but
            a few (BPJPH, GSO) are one long sentence and must be allowed to wrap. */}
        {scopeTags.map((tag) => (
          <span
            key={tag}
            className="plus-jakarta-sans-600 max-w-full rounded-[7px] border border-ho-green/8 bg-ho-tint px-[9px] py-[3px] text-[11px] text-[#3E5B4B]"
          >
            {tag}
          </span>
        ))}
      </div>

      <div className="mt-[2px] flex items-center justify-between">
        <div className="plus-jakarta-sans-600 flex items-center gap-[7px] text-[12px] text-ho-muted-3">
          <span className="h-[14px] w-[14px] flex-none rounded-full border-[1.6px] border-ho-gold" />
          {recText(a, group)}
        </div>
        <div className="plus-jakarta-sans-700 flex items-center gap-[5px] text-[12.5px] text-ho-green">
          Details
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path
              d="M5 12h14M13 6l6 6-6 6"
              stroke="#0F4B2E"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>
    </button>
  )
}
