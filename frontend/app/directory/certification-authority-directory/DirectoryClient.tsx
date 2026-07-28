"use client"

import { useMemo, useState } from "react"
import AuthorityCard from "./AuthorityCard"
import AuthorityModal from "./AuthorityModal"
import { AUTHORITIES, REGIONS, type Authority, type Region } from "./authorities"
import { dotFor, searchable, typeGroup, type TypeGroup } from "./logic"

type RegionFilter = Region | "ALL"
type TypeFilter = TypeGroup | "ALL"

/** Tiling hex outline behind the hero. Not expressible as a Tailwind utility. */
const HERO_PATTERN =
  "url(\"data:image/svg+xml,%3Csvg width='72' height='82' viewBox='0 0 72 82' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M36 1L70 20.5V60.5L36 80L2 60.5V20.5Z' fill='none' stroke='rgba(255,255,255,0.045)' stroke-width='1.4'/%3E%3C/svg%3E\")"

const TYPE_FILTERS: { key: TypeFilter; label: string }[] = [
  { key: "ALL", label: "All types" },
  { key: "Government", label: "Government" },
  { key: "NGO", label: "NGO / Religious" },
  { key: "Standards", label: "Standards" },
]

export default function DirectoryClient() {
  const [query, setQuery] = useState("")
  const [region, setRegion] = useState<RegionFilter>("ALL")
  const [type, setType] = useState<TypeFilter>("ALL")
  const [selected, setSelected] = useState<Authority | null>(null)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return AUTHORITIES.filter((a) => {
      const rOk = region === "ALL" || a.region === region
      const tOk = type === "ALL" || typeGroup(a.type) === type
      const sOk = !q || searchable(a).includes(q)
      return rOk && tOk && sOk
    })
  }, [query, region, type])

  // Counts describe the whole dataset, not the current filter — so the pills
  // read as "how much is behind this filter", which is what the design shows.
  const regionCounts = useMemo(() => {
    const counts = {} as Record<Region, number>
    for (const r of REGIONS) counts[r] = 0
    for (const a of AUTHORITIES) counts[a.region] += 1
    return counts
  }, [])

  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const a of AUTHORITIES) {
      const g = typeGroup(a.type)
      counts[g] = (counts[g] ?? 0) + 1
    }
    return counts
  }, [])

  // Counts every authority whose free-text type mentions "Government",
  // regardless of which bucket typeGroup() files it under. Per the design.
  const statGov = useMemo(
    () => AUTHORITIES.filter((a) => /Government/i.test(a.type)).length,
    []
  )

  const resetAll = () => {
    setQuery("")
    setRegion("ALL")
    setType("ALL")
  }

  const regionPills: { key: RegionFilter; label: string; count: number; dot: string }[] = [
    { key: "ALL", label: "All regions", count: AUTHORITIES.length, dot: "#C9A248" },
    ...REGIONS.map((r) => ({ key: r as RegionFilter, label: r, count: regionCounts[r], dot: dotFor(r) })),
  ]

  return (
    <>
      {/* HERO */}
      <section className="relative overflow-hidden bg-[radial-gradient(120%_140%_at_82%_0%,#12583A_0%,#0F4B2E_45%,#0C3826_100%)] px-5 pt-12 pb-[118px] text-white sm:px-6 sm:pt-[66px] md:px-10">
        <div
          className="absolute inset-0 opacity-90"
          style={{ backgroundImage: HERO_PATTERN, backgroundSize: "72px 82px" }}
        />
        <div className="absolute top-[-70px] right-[-90px] h-[340px] w-[340px] rounded-full bg-[radial-gradient(circle,rgba(201,162,72,.22),transparent_68%)]" />

        <div className="relative mx-auto max-w-[1240px]">
          {/* The label is ~330px at its design tracking — wider than a 360px
              viewport once the hero's padding is counted. Tighten the tracking
              and let it wrap on the narrowest screens. */}
          <div className="mb-[26px] inline-flex max-w-full items-center gap-[9px] rounded-full border border-ho-gold/40 bg-ho-gold/10 py-[6px] pr-[13px] pl-[10px]">
            <span className="h-[7px] w-[7px] flex-none rounded-full bg-ho-gold" />
            <span className="plus-jakarta-sans-600 text-[11px] tracking-[.08em] uppercase text-ho-gold-pale sm:text-[12px] sm:tracking-[.13em] sm:whitespace-nowrap">
              Certification Authority Directory
            </span>
          </div>

          <h1 className="plus-jakarta-sans-800 m-0 mb-5 max-w-[820px] text-[30px] leading-[1.04] tracking-[-.03em] text-balance sm:text-4xl md:text-[52px]">
            Every halal certification authority, in one trusted place.
          </h1>
          <p className="plus-jakarta-sans-400 m-0 mb-[34px] max-w-[620px] text-[16px] leading-[1.55] text-ho-mint sm:text-[18px]">
            A verified reference directory of the world&apos;s leading halal
            certification bodies — their standards, product scope, international
            recognition and verification portals, across nine regions.
          </p>

          <div className="flex max-w-[600px] items-center rounded-[14px] bg-white p-[7px] pl-[18px] shadow-[0_18px_44px_-18px_rgba(6,32,20,.6)]">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="flex-none" aria-hidden>
              <circle cx="11" cy="11" r="7.5" stroke="#8A968F" strokeWidth="2" />
              <path d="m21 21-4-4" stroke="#8A968F" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search authorities, countries, standards…"
              aria-label="Search authorities"
              className="min-w-0 flex-1 border-none bg-transparent px-3 py-[11px] font-[inherit] text-[15.5px] text-ho-ink outline-none"
            />
            <button
              type="button"
              onClick={() => setQuery("")}
              className="plus-jakarta-sans-600 flex-none cursor-pointer rounded-[9px] border-none bg-ho-green px-5 py-[11px] text-[14px] text-white transition-colors hover:bg-ho-green-dk"
            >
              Clear
            </button>
          </div>

          <div className="mt-11 flex flex-wrap gap-x-8 gap-y-6 sm:gap-10">
            <Stat value={String(AUTHORITIES.length)} label="Authorities" />
            <Divider />
            <Stat value="9" label="Regions" />
            <Divider />
            <Stat value={String(statGov)} label="Government bodies" />
            <Divider />
            <Stat value="500K+" label="Certified records" />
          </div>
        </div>
      </section>

      {/* TOOLBAR */}
      {/* Sticks directly below the header, whose height differs between mobile
          (hamburger) and desktop (nav) — hence the responsive offset. */}
      <div className="sticky top-[73px] z-30 mt-[-46px] border-b border-ho-green/8 bg-ho-bg/94 backdrop-blur-sm md:top-[71px]">
        <div className="mx-auto max-w-[1240px] px-5 sm:px-6 md:px-10">
          <div className="ho-scroll flex gap-2 overflow-x-auto pt-[15px] pb-[13px]">
            {regionPills.map((pill) => {
              const active = region === pill.key
              return (
                <button
                  key={pill.key}
                  type="button"
                  onClick={() => setRegion(pill.key)}
                  aria-pressed={active}
                  className={`plus-jakarta-sans-600 inline-flex flex-none cursor-pointer items-center gap-2 rounded-[9px] border px-[14px] py-2 text-[13px] transition-all duration-150 ${
                    active
                      ? "border-ho-green bg-ho-green text-white"
                      : "border-ho-green/14 bg-white text-ho-slate hover:border-ho-green/30"
                  }`}
                >
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: pill.dot }}
                  />
                  {pill.label}
                  <span className="plus-jakarta-sans-500 text-[11.5px] opacity-60">
                    {pill.count}
                  </span>
                </button>
              )
            })}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pb-[13px]">
            <div className="flex flex-wrap gap-[6px]">
              {TYPE_FILTERS.map((tf) => {
                const active = type === tf.key
                const label =
                  tf.key === "ALL" ? tf.label : `${tf.label} (${typeCounts[tf.key] ?? 0})`
                return (
                  <button
                    key={tf.key}
                    type="button"
                    onClick={() => setType(tf.key)}
                    aria-pressed={active}
                    className={`plus-jakarta-sans-600 cursor-pointer rounded-lg border px-[13px] py-[6px] text-[12.5px] transition-all duration-150 ${
                      active
                        ? "border-ho-green-lt bg-ho-green-lt text-white"
                        : "border-ho-green/16 bg-transparent text-ho-muted hover:border-ho-green/30"
                    }`}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
            <div className="plus-jakarta-sans-500 text-[13px] text-ho-muted-2">
              Showing {filtered.length} of {AUTHORITIES.length} authorities
            </div>
          </div>
        </div>
      </div>

      {/* GRID */}
      <main className="mx-auto max-w-[1240px] px-5 pt-[30px] pb-20 sm:px-6 md:px-10">
        {filtered.length > 0 ? (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(min(346px,100%),1fr))] gap-5">
            {filtered.map((a) => (
              <AuthorityCard key={a.num} authority={a} onOpen={setSelected} />
            ))}
          </div>
        ) : (
          <div className="px-5 py-[70px] text-center text-ho-muted-3">
            <div className="mx-auto mb-[18px] flex h-[62px] w-14 items-center justify-center bg-ho-tint [clip-path:polygon(50%_0,100%_27%,100%_73%,50%_100%,0_73%,0_27%)]">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden>
                <circle cx="11" cy="11" r="7" stroke="#9AA69E" strokeWidth="2" />
                <path d="m21 21-4-4" stroke="#9AA69E" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </div>
            <div className="plus-jakarta-sans-700 mb-[6px] text-[17px] text-ho-ink-3">
              No authorities found
            </div>
            <div className="text-[14px]">
              Try a different search term or region filter.
            </div>
            <button
              type="button"
              onClick={resetAll}
              className="plus-jakarta-sans-600 mt-[18px] cursor-pointer rounded-[9px] border-none bg-ho-green px-5 py-[10px] text-[13.5px] text-white transition-colors hover:bg-ho-green-dk"
            >
              Clear filters
            </button>
          </div>
        )}
      </main>

      {selected && (
        <AuthorityModal authority={selected} onClose={() => setSelected(null)} />
      )}
    </>
  )
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <div className="plus-jakarta-sans-800 text-[34px] leading-none tracking-[-.02em]">
        {value}
      </div>
      <div className="plus-jakarta-sans-500 mt-[3px] text-[13px] text-ho-mint-2">
        {label}
      </div>
    </div>
  )
}

// Hidden once the stats wrap — a stray vertical rule at the start of a wrapped
// row reads as noise rather than a separator.
const Divider = () => <div className="hidden w-px bg-white/14 sm:block" />
