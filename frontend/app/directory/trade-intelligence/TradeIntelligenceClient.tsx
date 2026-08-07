"use client"

import { useMemo, useState, type CSSProperties } from "react"
import Link from "next/link"
import { TRADEFLOWS } from "./data"

const SCOPED_CSS = `
.trade-root{
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
.trade-root *{box-sizing:border-box;}
.trade-root a{color:var(--green-800);text-decoration:none;transition:color .13s ease;}
.trade-root a:hover{color:var(--gold-600);}
.trade-root ::selection{background:var(--gold-200);color:var(--green-900);}
.trade-root input::placeholder{color:var(--muted);}
@keyframes trade-fade{from{opacity:0;transform:translateY(6px);}to{opacity:1;transform:none;}}
@media (max-width:760px){
  .trade-stats{grid-template-columns:repeat(2,1fr) !important;}
  .trade-card{grid-template-columns:auto 1fr !important;}
  .trade-metrics{grid-column:1 / -1 !important;border-left:none !important;border-top:1px solid var(--cream-100) !important;flex-direction:row !important;}
}
`

const kicker: CSSProperties = { fontSize: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: ".12em", color: "var(--gold-600)" }

function scoreStyle(n: number) {
  if (n >= 9) return { bg: "linear-gradient(160deg,#196B24,#0F4B2E)", label: "Prime" }
  if (n >= 8) return { bg: "linear-gradient(160deg,#0F4B2E,#07351F)", label: "Strong" }
  if (n >= 7) return { bg: "linear-gradient(160deg,#B7902F,#8A6D2F)", label: "Solid" }
  return { bg: "linear-gradient(160deg,#8A6D2F,#6b5426)", label: "Emerging" }
}
const parseVal = (v: string) => parseFloat(String(v).replace(/[^0-9.]/g, "")) || 0

export default function TradeIntelligenceClient() {
  const all = TRADEFLOWS
  const [query, setQuery] = useState("")
  const [from, setFrom] = useState("ALL")
  const [sort, setSort] = useState<"score" | "value">("score")

  const { fromTabs, filtered, stats, countLabel } = useMemo(() => {
    const q = query.trim().toLowerCase()

    const froms = [...new Set(all.map((i) => i.exporter))]
      .filter(Boolean)
      .sort((a, b) => all.filter((i) => i.exporter === b).length - all.filter((i) => i.exporter === a).length)
    const fromTabs = [{ id: "ALL", label: "All exporters", n: all.length }].concat(
      froms.map((f) => ({ id: f, label: f, n: all.filter((i) => i.exporter === f).length })),
    ).map((t) => ({ ...t, active: from === t.id }))

    let filtered = all.filter(
      (i) => (from === "ALL" || i.exporter === from) && (!q || JSON.stringify(i).toLowerCase().includes(q)),
    )
    filtered = filtered
      .slice()
      .sort((a, b) => (sort === "value" ? parseVal(b.value) - parseVal(a.value) : (b.score || 0) - (a.score || 0)))

    const avg = all.length ? (all.reduce((s, i) => s + (i.score || 0), 0) / all.length).toFixed(1) : "0"
    const stats = [
      { value: all.length, label: "Trade corridors mapped", accent: "var(--green-800)" },
      { value: froms.length, label: "Exporting countries", accent: "var(--green-700)" },
      { value: all.filter((i) => (i.score || 0) >= 9).length, label: "Prime opportunities (9+)", accent: "var(--gold-500)" },
      { value: avg, label: "Average opportunity score", accent: "var(--green-800)" },
    ]

    const isFiltered = from !== "ALL" || !!q
    const countLabel = isFiltered ? `Showing ${filtered.length} of ${all.length} corridors` : `Showing all ${all.length} corridors`

    return { fromTabs, filtered, stats, countLabel }
  }, [all, query, from, sort])

  const sortTabs = [
    { id: "score" as const, label: "Top opportunity" },
    { id: "value" as const, label: "Highest value" },
  ]

  return (
    <div className="trade-root">
      <style>{SCOPED_CSS}</style>

      {/* HEADER */}
      <header style={{ position: "sticky", top: 0, zIndex: 40, background: "color-mix(in srgb,var(--cream-50) 88%,transparent)", backdropFilter: "blur(10px)", borderBottom: "1px solid var(--border)" }}>
        <div style={{ maxWidth: 1240, margin: "0 auto", padding: "12px 24px", display: "flex", alignItems: "center", gap: 16 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <svg width="30" height="30" viewBox="-16 -16 32 32" aria-hidden="true">
              <path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke="var(--gold-500)" strokeWidth="2.6" strokeLinejoin="round" />
              <path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke="var(--green-800)" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <div style={{ fontSize: 19, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--green-900)" }}>Halal<span style={{ color: "var(--gold-600)" }}>One</span></div>
          </Link>
          <div style={{ width: 1, height: 22, background: "var(--border)" }} />
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--muted)" }}>Trade &amp; Opportunity Intelligence</div>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 14 }}>
            <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--green-900)", background: "var(--gold-500)", padding: "3px 9px", borderRadius: 999 }}>Premium</span>
            <span style={{ ...kicker, letterSpacing: ".1em" }}>Module 7</span>
            <Link href="/" style={{ fontSize: 13, fontWeight: 700, color: "var(--green-800)" }}>Back to platform ↗</Link>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section style={{ background: "linear-gradient(160deg,#0F4B2E,#07351F)", color: "var(--cream-50)", position: "relative", overflow: "hidden" }}>
        <div aria-hidden="true" style={{ position: "absolute", inset: 0, backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M30 3L54 30L30 57L6 30Z' fill='none' stroke='rgba(251,250,246,0.05)' stroke-width='1'/%3E%3C/svg%3E\")", backgroundSize: "60px" }} />
        <div style={{ position: "relative", maxWidth: 1240, margin: "0 auto", padding: "52px 24px 58px", display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-end", gap: 32 }}>
          <div style={{ maxWidth: 660 }}>
            <div style={{ ...kicker, letterSpacing: ".14em", color: "var(--gold-500)" }}>Regulatory Intelligence · Trade · Premium</div>
            <h1 style={{ margin: "16px 0 0", fontSize: "clamp(28px,3.6vw,42px)", lineHeight: 1.07, fontWeight: 800, letterSpacing: "-0.025em", color: "#fff", textWrap: "balance" }}>Halal trade flows and market opportunity, scored.</h1>
            <p style={{ margin: "15px 0 0", fontSize: 16, lineHeight: 1.6, color: "color-mix(in srgb,var(--cream-50) 74%,transparent)", maxWidth: 580 }}>Exporter-to-importer corridors with annual value, growth, the certification that unlocks access, and an opportunity score — to find where halal demand is outpacing supply.</p>
            <p style={{ margin: "14px 0 0", fontSize: 12, color: "color-mix(in srgb,var(--cream-50) 52%,transparent)" }}>Sources: UN COMTRADE · ITC · OIC Statistics · ABIEC · MAPA · DFAT · ICCD analysis.</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 60, fontWeight: 800, lineHeight: 1, letterSpacing: "-0.03em", color: "#fff" }}>{all.length}</div>
            <div style={{ ...kicker, letterSpacing: ".14em", color: "var(--gold-500)", marginTop: 6 }}>Trade corridors</div>
          </div>
        </div>
      </section>

      <div style={{ maxWidth: 1240, margin: "0 auto", padding: "0 24px 72px" }}>
        {/* STATS */}
        <div className="trade-stats" style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginTop: -28, position: "relative", zIndex: 10 }}>
          {stats.map((s) => (
            <div key={s.label} style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: 14, padding: "16px 18px", boxShadow: "var(--shadow-sm)", borderTop: `3px solid ${s.accent}` }}>
              <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--green-900)", lineHeight: 1 }}>{s.value}</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--muted)", marginTop: 7 }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* CONTROLS */}
        <div style={{ position: "sticky", top: 63, zIndex: 30, marginTop: 20, background: "color-mix(in srgb,var(--cream-50) 90%,transparent)", backdropFilter: "blur(8px)", padding: "12px 0" }}>
          <div style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: 16, padding: "14px 16px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, background: "var(--cream-100)", border: "1px solid var(--border)", borderRadius: 12, padding: "11px 15px" }}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="11" cy="11" r="8" stroke="#657269" strokeWidth="2" /><path d="m21 21-4.35-4.35" stroke="#657269" strokeWidth="2" strokeLinecap="round" /></svg>
              <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search exporter, importer, product, certifier…" style={{ flex: 1, border: "none", outline: "none", background: "transparent", fontFamily: "var(--font)", fontSize: 14, color: "var(--green-900)" }} />
              {query.length > 0 && <button onClick={() => setQuery("")} style={{ border: "none", background: "transparent", cursor: "pointer", color: "var(--muted)", fontSize: 15, lineHeight: 1, padding: "2px 4px" }}>✕</button>}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 16, flexWrap: "wrap", marginTop: 13 }}>
              <div style={{ flex: 1, minWidth: 260 }}>
                <div style={{ ...kicker, margin: "0 2px 7px" }}>Exporting country</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {fromTabs.map((t) => (
                    <button key={t.id} onClick={() => setFrom(t.id)} style={t.active
                      ? { padding: "6px 12px", borderRadius: 8, border: "1px solid var(--green-800)", background: "var(--green-800)", color: "#fff", cursor: "pointer", fontFamily: "var(--font)", fontSize: 11, fontWeight: 700 }
                      : { padding: "6px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "#fff", color: "var(--muted)", cursor: "pointer", fontFamily: "var(--font)", fontSize: 11, fontWeight: 600 }}>
                      {t.label} <span style={{ opacity: t.active ? 0.6 : 0.55 }}>{t.n}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                {sortTabs.map((t) => (
                  <button key={t.id} onClick={() => setSort(t.id)} style={sort === t.id
                    ? { padding: "7px 13px", borderRadius: 999, border: "1px solid var(--gold-600)", background: "var(--gold-500)", color: "var(--green-900)", cursor: "pointer", fontFamily: "var(--font)", fontSize: 11, fontWeight: 700 }
                    : { padding: "7px 13px", borderRadius: 999, border: "1px solid var(--border)", background: "#fff", color: "var(--muted)", cursor: "pointer", fontFamily: "var(--font)", fontSize: 11, fontWeight: 600 }}>
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div style={{ fontSize: 12.5, color: "var(--muted)", margin: "6px 2px 12px" }}>{countLabel}</div>

        {/* CORRIDOR CARDS */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {filtered.map((c) => {
            const ss = scoreStyle(c.score || 0)
            const up = /^\+/.test(c.yoy || "")
            return (
              <article key={c.id} className="trade-card" style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: 16, boxShadow: "var(--shadow-sm)", overflow: "hidden", animation: "trade-fade .3s ease both", display: "grid", gridTemplateColumns: "auto 1fr auto", alignItems: "stretch" }}>
                {/* score rail */}
                <div style={{ width: 74, background: ss.bg, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: "#fff", padding: "14px 8px" }}>
                  <div style={{ fontSize: 24, fontWeight: 800, lineHeight: 1 }}>{c.score}</div>
                  <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: ".08em", opacity: 0.85, marginTop: 2 }}>/ 10</div>
                  <div style={{ fontSize: 8.5, fontWeight: 700, letterSpacing: ".06em", textTransform: "uppercase", marginTop: 8, textAlign: "center", opacity: 0.9 }}>{ss.label}</div>
                </div>
                {/* middle */}
                <div style={{ padding: "15px 20px", minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 15, fontWeight: 800, color: "var(--green-800)" }}>{c.exporter}</span>
                    <svg width="22" height="12" viewBox="0 0 22 12" fill="none" aria-hidden="true"><path d="M0 6h18M14 1l5 5-5 5" stroke="var(--gold-500)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    <span style={{ fontSize: 15, fontWeight: 800, color: "var(--green-900)" }}>{c.importer}</span>
                    <span style={{ padding: "3px 10px", borderRadius: 999, fontSize: 10, fontWeight: 700, background: "var(--cream-100)", color: "var(--muted)", border: "1px solid var(--border)" }}>{c.category}</span>
                  </div>
                  <p style={{ fontSize: 12.5, color: "var(--ink)", lineHeight: 1.55, margin: "9px 0 0" }}>{c.notes}</p>
                  <div style={{ display: "flex", gap: 7, marginTop: 11, flexWrap: "wrap" }}>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, fontWeight: 700, color: "var(--green-800)", background: "color-mix(in srgb,var(--green-700) 9%,transparent)", border: "1px solid color-mix(in srgb,var(--green-700) 24%,transparent)", padding: "4px 10px", borderRadius: 999 }}>Certifier · {c.certBody}</span>
                  </div>
                </div>
                {/* metrics */}
                <div className="trade-metrics" style={{ padding: "15px 22px", background: "color-mix(in srgb,var(--cream-100) 55%,transparent)", borderLeft: "1px solid var(--cream-100)", display: "flex", flexDirection: "column", justifyContent: "center", gap: 10, minWidth: 150 }}>
                  <div>
                    <div style={{ fontSize: 9.5, fontWeight: 800, textTransform: "uppercase", letterSpacing: ".1em", color: "var(--gold-600)" }}>Annual value</div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: "var(--green-900)", fontFamily: "var(--mono)", letterSpacing: "-0.02em", marginTop: 2 }}>{c.value}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 9.5, fontWeight: 800, textTransform: "uppercase", letterSpacing: ".1em", color: "var(--gold-600)" }}>YoY growth</div>
                    <div style={{ fontSize: 15, fontWeight: 800, color: up ? "var(--green-700)" : "var(--danger)", fontFamily: "var(--mono)", marginTop: 2 }}>{c.yoy}</div>
                  </div>
                </div>
              </article>
            )
          })}
        </div>

        {all.length > 0 && filtered.length === 0 && (
          <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--muted)" }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: "var(--green-900)" }}>No trade corridors match your filters.</div>
            <div style={{ fontSize: 13, marginTop: 6 }}>Try a different term or reset the exporter filter.</div>
          </div>
        )}
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
              <div style={{ fontSize: 11, color: "color-mix(in srgb,var(--cream-50) 60%,transparent)" }}>Trade &amp; Opportunity Intelligence · Module 7</div>
            </div>
          </div>
          <div style={{ fontSize: 11.5, color: "color-mix(in srgb,var(--cream-50) 60%,transparent)", maxWidth: 540, lineHeight: 1.6, textAlign: "right" }}>Opportunity scores are ICCD analytical estimates from public trade data, not guarantees. Verify tariffs, certification recognition and market-access requirements before committing to any corridor.</div>
        </div>
      </footer>
    </div>
  )
}
