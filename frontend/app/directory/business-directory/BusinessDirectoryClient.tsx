"use client"

import { Fragment, useMemo, useState, type CSSProperties } from "react"
import Link from "next/link"
import { BUSINESSES, type Business } from "./data"

// Scoped palette + base rules ported from the design's :root, namespaced under
// .bizdir-root so nothing leaks into the rest of the app.
const SCOPED_CSS = `
.bizdir-root{
  --green-900:#07351F; --green-800:#0F4B2E; --green-700:#196B24; --green-100:#D9DED8;
  --gold-600:#B7902F; --gold-500:#C9A248; --gold-200:#EBDFC0;
  --cream-50:#FBFAF6; --cream-100:#F7F4EC;
  --ink:#222222; --muted:#657269; --danger:#B23A2E; --border:#D9DED8;
  --shadow-sm:0 2px 8px color-mix(in srgb,#07351F 8%,transparent);
  --mono:var(--font-geist-mono),ui-monospace,SFMono-Regular,Menlo,monospace;
  --font:var(--font-plus-jakarta-sans),ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-family:var(--font);background:var(--cream-50);color:var(--ink);
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;min-height:100vh;
}
.bizdir-root *{box-sizing:border-box;}
.bizdir-root a{color:var(--green-800);text-decoration:none;transition:color .13s ease;}
.bizdir-root a:hover{color:var(--gold-600);}
.bizdir-root ::selection{background:var(--gold-200);color:var(--green-900);}
.bizdir-root input::placeholder{color:var(--muted);}
`

// Per-type accent colours from the design's TYPE_COLOR map.
const TYPE_COLOR: Record<string, string> = {
  Manufacturer: "#0F4B2E",
  Pharmaceutical: "#6D4AA6",
  Cosmetics: "#B0567F",
  "Food Service": "#B7902F",
  Retail: "#196B24",
  Logistics: "#3B6E8F",
  Finance: "#1F6F5C",
  "Certification Body": "#B23A2E",
  "Ingredient Supplier": "#8A6D2F",
}
const tc = (t: string) => TYPE_COLOR[t] ?? "#0F4B2E"

const kicker: CSSProperties = {
  fontSize: 10,
  fontWeight: 800,
  textTransform: "uppercase",
  letterSpacing: ".12em",
  color: "var(--gold-600)",
}
const th: CSSProperties = {
  textAlign: "left",
  padding: "12px 12px",
  fontSize: 10.5,
  fontWeight: 800,
  letterSpacing: ".08em",
  textTransform: "uppercase",
  color: "var(--gold-200)",
}

type Tab = { id: string; label: string; n: number; active: boolean }

export default function BusinessDirectoryClient() {
  const all = BUSINESSES
  const [query, setQuery] = useState("")
  const [type, setType] = useState("ALL")
  const [region, setRegion] = useState("ALL")
  const [trust, setTrust] = useState("ALL")
  const [open, setOpen] = useState<Record<string, boolean>>({})

  const {
    typeTabs,
    regionTabs,
    trustTabs,
    filtered,
    stats,
    countLabel,
    isFiltered,
  } = useMemo(() => {
    const q = query.trim().toLowerCase()

    const types = [...new Set(all.map((i) => i.type))].sort(
      (a, b) => all.filter((i) => i.type === b).length - all.filter((i) => i.type === a).length,
    )
    const typeTabs: Tab[] = [{ id: "ALL", label: "All types", n: all.length, active: type === "ALL" }].concat(
      types.map((t) => ({ id: t, label: t, n: all.filter((i) => i.type === t).length, active: type === t })),
    )

    const regions = [...new Set(all.map((i) => i.region))].filter(Boolean).sort()
    const regionTabs: Tab[] = [{ id: "ALL", label: "All regions", n: all.length, active: region === "ALL" }].concat(
      regions.map((r) => ({ id: r, label: r, n: all.filter((i) => i.region === r).length, active: region === r })),
    )

    const trusts = [...new Set(all.map((i) => i.trust))].filter(Boolean)
    const trustTabs: Tab[] = [{ id: "ALL", label: "All", n: all.length, active: trust === "ALL" }].concat(
      trusts.map((t) => ({ id: t, label: t, n: all.filter((i) => i.trust === t).length, active: trust === t })),
    )

    const filtered = all.filter(
      (i) =>
        (type === "ALL" || i.type === type) &&
        (region === "ALL" || i.region === region) &&
        (trust === "ALL" || i.trust === trust) &&
        (!q || JSON.stringify(i).toLowerCase().includes(q)),
    )

    const stats = [
      { value: all.length, label: "Businesses listed", accent: "var(--green-800)" },
      { value: all.filter((i) => i.trust === "Verified").length, label: "Verified listings", accent: "var(--green-700)" },
      { value: types.length, label: "Business types", accent: "var(--gold-500)" },
      { value: [...new Set(all.map((i) => i.country))].filter(Boolean).length, label: "Countries represented", accent: "var(--green-800)" },
    ]

    const isFiltered = type !== "ALL" || region !== "ALL" || trust !== "ALL" || !!q
    const countLabel = isFiltered
      ? `Showing ${filtered.length} of ${all.length} businesses`
      : `Showing all ${all.length} businesses`

    return { typeTabs, regionTabs, trustTabs, filtered, stats, countLabel, isFiltered }
  }, [all, query, type, region, trust])

  const typePill = (setFn: (id: string) => void, t: Tab): CSSProperties =>
    t.active
      ? { padding: "6px 12px", borderRadius: 8, border: "1px solid var(--green-800)", background: "var(--green-800)", color: "#fff", cursor: "pointer", fontFamily: "var(--font)", fontSize: 11, fontWeight: 700 }
      : { padding: "6px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "#fff", color: "var(--muted)", cursor: "pointer", fontFamily: "var(--font)", fontSize: 11, fontWeight: 600 }

  const regionPill = (t: Tab): CSSProperties =>
    t.active
      ? { padding: "6px 11px", borderRadius: 999, border: "1px solid var(--green-700)", background: "color-mix(in srgb,var(--green-700) 12%,transparent)", color: "var(--green-800)", cursor: "pointer", fontFamily: "var(--font)", fontSize: 11, fontWeight: 700 }
      : { padding: "6px 11px", borderRadius: 999, border: "1px solid var(--border)", background: "#fff", color: "var(--muted)", cursor: "pointer", fontFamily: "var(--font)", fontSize: 11, fontWeight: 600 }

  const trustPill = (t: Tab): CSSProperties =>
    t.active
      ? { padding: "6px 11px", borderRadius: 999, border: "1px solid var(--gold-600)", background: "var(--gold-500)", color: "var(--green-900)", cursor: "pointer", fontFamily: "var(--font)", fontSize: 11, fontWeight: 700 }
      : { padding: "6px 11px", borderRadius: 999, border: "1px solid var(--border)", background: "#fff", color: "var(--muted)", cursor: "pointer", fontFamily: "var(--font)", fontSize: 11, fontWeight: 600 }

  return (
    <div className="bizdir-root">
      <style>{SCOPED_CSS}</style>

      {/* HEADER */}
      <header style={{ position: "sticky", top: 0, zIndex: 40, background: "color-mix(in srgb,var(--cream-50) 88%,transparent)", backdropFilter: "blur(10px)", borderBottom: "1px solid var(--border)" }}>
        <div style={{ maxWidth: 1240, margin: "0 auto", padding: "12px 24px", display: "flex", alignItems: "center", gap: 16 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <svg width="30" height="30" viewBox="-16 -16 32 32" aria-hidden="true">
              <path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke="var(--gold-500)" strokeWidth="2.6" strokeLinejoin="round" />
              <path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke="var(--green-800)" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <div style={{ fontSize: 19, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--green-900)" }}>
              Halal<span style={{ color: "var(--gold-600)" }}>One</span>
            </div>
          </Link>
          <div style={{ width: 1, height: 22, background: "var(--border)" }} />
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--muted)" }}>Verified Business Directory</div>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 18 }}>
            <span style={{ ...kicker, letterSpacing: ".1em" }} className="hidden-sm">Module 8 · Directory</span>
            <Link href="/" style={{ fontSize: 13, fontWeight: 700, color: "var(--green-800)" }}>Back to platform ↗</Link>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section style={{ background: "linear-gradient(160deg,#0F4B2E,#07351F)", color: "var(--cream-50)", position: "relative", overflow: "hidden" }}>
        <div aria-hidden="true" style={{ position: "absolute", inset: 0, backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M30 3L54 30L30 57L6 30Z' fill='none' stroke='rgba(251,250,246,0.05)' stroke-width='1'/%3E%3C/svg%3E\")", backgroundSize: "60px" }} />
        <div style={{ position: "relative", maxWidth: 1240, margin: "0 auto", padding: "52px 24px 58px", display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-end", gap: 32 }}>
          <div style={{ maxWidth: 640 }}>
            <div style={{ ...kicker, letterSpacing: ".14em", color: "var(--gold-500)" }}>Regulatory Intelligence · Directory</div>
            <h1 style={{ margin: "16px 0 0", fontSize: "clamp(28px,3.6vw,42px)", lineHeight: 1.07, fontWeight: 800, letterSpacing: "-0.025em", color: "#fff", textWrap: "balance" }}>
              The verified global halal business directory.
            </h1>
            <p style={{ margin: "15px 0 0", fontSize: 16, lineHeight: 1.6, color: "color-mix(in srgb,var(--cream-50) 74%,transparent)", maxWidth: 560 }}>
              Manufacturers, exporters, food service, ingredient suppliers, pharma, cosmetics, retail, finance, logistics and certification bodies — with certifier, export markets and verification status.
            </p>
            <p style={{ margin: "14px 0 0", fontSize: 12.5, color: "color-mix(in srgb,var(--cream-50) 55%,transparent)" }}>
              ICCD Technology Team · Content reference — confirm certification directly with each business.
            </p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 60, fontWeight: 800, lineHeight: 1, letterSpacing: "-0.03em", color: "#fff" }}>{all.length}</div>
            <div style={{ ...kicker, letterSpacing: ".14em", color: "var(--gold-500)", marginTop: 6 }}>Businesses listed</div>
          </div>
        </div>
      </section>

      <div style={{ maxWidth: 1240, margin: "0 auto", padding: "0 24px 72px" }}>
        {/* STAT CARDS */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginTop: -28, position: "relative", zIndex: 10 }} className="bizdir-stats">
          {stats.map((s) => (
            <div key={s.label} style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: 14, padding: "16px 18px", boxShadow: "var(--shadow-sm)", borderTop: `3px solid ${s.accent}` }}>
              <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--green-900)", lineHeight: 1 }}>{s.value}</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--muted)", marginTop: 7 }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* FILTER PANEL */}
        <div style={{ position: "sticky", top: 63, zIndex: 30, marginTop: 20, background: "color-mix(in srgb,var(--cream-50) 90%,transparent)", backdropFilter: "blur(8px)", padding: "12px 0" }}>
          <div style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: 16, padding: "14px 16px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, background: "var(--cream-100)", border: "1px solid var(--border)", borderRadius: 12, padding: "11px 15px" }}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="11" cy="11" r="8" stroke="#657269" strokeWidth="2" /><path d="m21 21-4.35-4.35" stroke="#657269" strokeWidth="2" strokeLinecap="round" /></svg>
              <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search business, country, brand, certifier, product…" style={{ flex: 1, border: "none", outline: "none", background: "transparent", fontFamily: "var(--font)", fontSize: 14, color: "var(--green-900)" }} />
              {query.length > 0 && (
                <button onClick={() => setQuery("")} style={{ border: "none", background: "transparent", cursor: "pointer", color: "var(--muted)", fontSize: 15, lineHeight: 1, padding: "2px 4px" }}>✕</button>
              )}
            </div>

            <div style={{ ...kicker, margin: "13px 2px 7px" }}>Business type</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {typeTabs.map((t) => (
                <button key={t.id} onClick={() => setType(t.id)} style={typePill(setType, t)}>
                  {t.label} <span style={{ opacity: t.active ? 0.6 : 0.55 }}>{t.n}</span>
                </button>
              ))}
            </div>

            <div style={{ display: "flex", gap: 22, flexWrap: "wrap", marginTop: 13 }}>
              <div style={{ flex: 1, minWidth: 240 }}>
                <div style={{ ...kicker, margin: "0 2px 7px" }}>Region</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {regionTabs.map((t) => (
                    <button key={t.id} onClick={() => setRegion(t.id)} style={regionPill(t)}>
                      {t.label} <span style={{ opacity: t.active ? 0.6 : 0.55 }}>{t.n}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <div style={{ ...kicker, margin: "0 2px 7px" }}>Trust</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {trustTabs.map((t) => (
                    <button key={t.id} onClick={() => setTrust(t.id)} style={trustPill(t)}>
                      {t.label} <span style={{ opacity: t.active ? 0.7 : 0.55 }}>{t.n}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div style={{ fontSize: 12.5, color: "var(--muted)", margin: "6px 2px 12px" }}>{countLabel}</div>

        {/* TABLE */}
        <div style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: 16, overflow: "hidden", boxShadow: "var(--shadow-sm)" }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 720 }}>
              <thead>
                <tr style={{ background: "var(--green-800)" }}>
                  <th style={{ ...th, padding: "12px 16px" }}>Business</th>
                  <th style={th}>Type</th>
                  <th style={th}>Certifier</th>
                  <th style={th}>Export markets</th>
                  <th style={th}>Trust</th>
                  <th style={{ width: 40 }} />
                </tr>
              </thead>
              <tbody>
                {filtered.map((r, idx) => {
                  const isOpen = !!open[r.id]
                  const col = tc(r.type)
                  const rowBg = isOpen ? "var(--cream-100)" : idx % 2 ? "color-mix(in srgb,var(--cream-100) 40%,transparent)" : "#fff"
                  const toggle = () => setOpen((s) => ({ ...s, [r.id]: !s[r.id] }))
                  return (
                    <Fragment key={r.id}>
                      <tr onClick={toggle} style={{ borderTop: "1px solid var(--cream-100)", cursor: "pointer", background: rowBg }}>
                        <td style={{ padding: "12px 16px", verticalAlign: "top", maxWidth: 280 }}>
                          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--green-900)", lineHeight: 1.3 }}>{r.name}</div>
                          <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>{r.location}</div>
                        </td>
                        <td style={{ padding: "12px 12px", verticalAlign: "top" }}>
                          <span style={{ display: "inline-block", padding: "3px 9px", borderRadius: 999, fontSize: 10, fontWeight: 700, background: `color-mix(in srgb,${col} 12%,transparent)`, color: col, border: `1px solid color-mix(in srgb,${col} 30%,transparent)`, whiteSpace: "nowrap" }}>{r.type}</span>
                        </td>
                        <td style={{ padding: "12px 12px", verticalAlign: "top", fontSize: 12, fontWeight: 700, color: "var(--green-800)" }}>{r.certBody}</td>
                        <td style={{ padding: "12px 12px", verticalAlign: "top", fontSize: 11.5, color: "var(--ink)", maxWidth: 200, lineHeight: 1.4 }}>{r.exportMarkets}</td>
                        <td style={{ padding: "12px 12px", verticalAlign: "top" }}>
                          {r.trust === "Verified" ? (
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "3px 9px", borderRadius: 999, fontSize: 10, fontWeight: 800, background: "color-mix(in srgb,var(--green-700) 12%,transparent)", color: "var(--green-700)", border: "1px solid color-mix(in srgb,var(--green-700) 30%,transparent)" }}>✓ Verified</span>
                          ) : (
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "3px 9px", borderRadius: 999, fontSize: 10, fontWeight: 800, background: "color-mix(in srgb,var(--gold-500) 16%,transparent)", color: "var(--gold-600)", border: "1px solid color-mix(in srgb,var(--gold-500) 38%,transparent)" }}>Self-declared</span>
                          )}
                        </td>
                        <td style={{ padding: "12px 12px", textAlign: "center", color: "var(--muted)", fontSize: 12 }}>{isOpen ? "▲" : "▾"}</td>
                      </tr>
                      {isOpen && (
                        <tr style={{ background: "var(--cream-100)" }}>
                          <td colSpan={6} style={{ padding: "0 16px 18px" }}>
                            <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20, paddingTop: 14 }} className="bizdir-detail">
                              <div>
                                <div style={{ ...kicker, marginBottom: 5 }}>About</div>
                                <div style={{ fontSize: 13, color: "var(--ink)", lineHeight: 1.6 }}>{r.notes}</div>
                                <div style={{ ...kicker, margin: "14px 0 6px" }}>Key categories</div>
                                <div style={{ fontSize: 12.5, color: "var(--ink)", lineHeight: 1.5 }}>{r.categories}</div>
                              </div>
                              <div>
                                <div style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: 10, padding: "12px 14px" }}>
                                  <DetailRow label="Directory ID" value={r.id} mono />
                                  <DetailRow label="Country" value={r.country} top />
                                  <DetailRow label="Region" value={r.region} top />
                                  <DetailRow label="Certifier" value={r.certBody} top green />
                                </div>
                                {r.url && (
                                  <a href={r.url} target="_blank" rel="noopener noreferrer" style={{ display: "inline-block", marginTop: 12, fontSize: 12.5, fontWeight: 700 }}>{r.urlLabel} ↗</a>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
          {all.length > 0 && filtered.length === 0 && (
            <div style={{ textAlign: "center", padding: "50px 20px", color: "var(--muted)" }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: "var(--green-900)" }}>No businesses match your filters.</div>
              <div style={{ fontSize: 13, marginTop: 6 }}>Try a different term or reset the type, region and trust filters.</div>
            </div>
          )}
        </div>
      </div>

      {/* FOOTER */}
      <footer style={{ background: "linear-gradient(160deg,#0F4B2E,#07351F)", color: "var(--cream-50)" }}>
        <div style={{ maxWidth: 1240, margin: "0 auto", padding: "38px 24px", display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
            <svg width="28" height="28" viewBox="-16 -16 32 32" aria-hidden="true">
              <path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke="var(--gold-500)" strokeWidth="2.6" strokeLinejoin="round" />
              <path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke="var(--cream-50)" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <div>
              <div style={{ fontSize: 16, fontWeight: 800, letterSpacing: "-0.02em", color: "#fff" }}>Halal<span style={{ color: "var(--gold-500)" }}>One</span></div>
              <div style={{ fontSize: 11, color: "color-mix(in srgb,var(--cream-50) 60%,transparent)" }}>Verified Business Directory · Module 8</div>
            </div>
          </div>
          <div style={{ fontSize: 11.5, color: "color-mix(in srgb,var(--cream-50) 60%,transparent)", maxWidth: 540, lineHeight: 1.6, textAlign: "right" }}>
            &quot;Verified&quot; reflects ICCD&apos;s review at listing time; &quot;self-declared&quot; entries are unconfirmed. Certification scope and validity change — always confirm current status directly with the business or its certifier.
          </div>
        </div>
      </footer>

      {/* Responsive tweaks that can't be inline */}
      <style>{`
        @media (max-width: 720px){
          .bizdir-stats{grid-template-columns:repeat(2,1fr) !important;}
          .bizdir-detail{grid-template-columns:1fr !important;}
        }
      `}</style>
    </div>
  )
}

function DetailRow({ label, value, mono, top, green }: { label: string; value: string; mono?: boolean; top?: boolean; green?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, padding: "5px 0", fontSize: 12, borderTop: top ? "1px solid var(--cream-100)" : undefined }}>
      <span style={{ color: "var(--muted)", fontWeight: 600 }}>{label}</span>
      <span style={{ fontFamily: mono ? "var(--mono)" : undefined, fontWeight: 700, color: green ? "var(--green-800)" : "var(--green-900)" }}>{value}</span>
    </div>
  )
}
