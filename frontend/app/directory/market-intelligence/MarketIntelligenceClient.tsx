"use client"

import { useMemo, useState, type CSSProperties } from "react"
import Link from "next/link"
import { bigStats, timeline, countries, sectors, trends, corridors } from "./data"

const SCOPED_CSS = `
.mktintel-root{
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
.mktintel-root *{box-sizing:border-box;}
.mktintel-root a{color:var(--green-800);text-decoration:none;transition:color .13s ease;}
.mktintel-root a:hover{color:var(--gold-600);}
.mktintel-root ::selection{background:var(--gold-200);color:var(--green-900);}
.mktintel-root input::placeholder{color:var(--muted);}
@media (max-width:900px){ .mktintel-grid4{grid-template-columns:repeat(2,1fr) !important;} .mktintel-grid3{grid-template-columns:1fr !important;} }
@media (max-width:600px){ .mktintel-grid4{grid-template-columns:1fr !important;} }
`

const kicker: CSSProperties = { fontSize: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: ".12em", color: "var(--gold-600)" }
const th: CSSProperties = { textAlign: "left", padding: "12px 12px", fontSize: 10.5, fontWeight: 800, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--gold-200)" }
const h2: CSSProperties = { fontSize: 19, fontWeight: 800, letterSpacing: "-0.015em", color: "var(--green-900)", margin: 0 }

function maturityStyle(m: string) {
  const t = (m || "").toLowerCase()
  if (t.includes("mature")) return { bg: "color-mix(in srgb,var(--green-700) 12%,transparent)", fg: "var(--green-700)", border: "color-mix(in srgb,var(--green-700) 30%,transparent)" }
  if (t.includes("emerging")) return { bg: "color-mix(in srgb,var(--gold-500) 16%,transparent)", fg: "var(--gold-600)", border: "color-mix(in srgb,var(--gold-500) 38%,transparent)" }
  return { bg: "color-mix(in srgb,var(--green-800) 10%,transparent)", fg: "var(--green-800)", border: "color-mix(in srgb,var(--green-800) 26%,transparent)" }
}

export default function MarketIntelligenceClient() {
  const [query, setQuery] = useState("")
  const [region, setRegion] = useState("ALL")

  const maxTimeline = useMemo(() => Math.max(1, ...timeline.map((t) => parseFloat(t.v.replace(/,/g, "")) || 0)), [])

  const { regionTabs, filteredCountries, countryCountLabel } = useMemo(() => {
    const q = query.trim().toLowerCase()
    const regions = [...new Set(countries.map((c) => c.region))]
    const regionTabs = [{ id: "ALL", label: "All regions", n: countries.length }].concat(
      regions.map((r) => ({ id: r, label: r, n: countries.filter((c) => c.region === r).length })),
    ).map((t) => ({ ...t, active: region === t.id }))

    const filteredCountries = countries.filter((c) =>
      (region === "ALL" || c.region === region) &&
      (!q || `${c.name} ${c.region} ${c.cats} ${c.role}`.toLowerCase().includes(q)),
    )
    const isFiltered = region !== "ALL" || !!q
    const countryCountLabel = isFiltered ? `${filteredCountries.length} of ${countries.length} countries` : `${countries.length} countries ranked by market size`
    return { regionTabs, filteredCountries, countryCountLabel }
  }, [query, region])

  return (
    <div className="mktintel-root">
      <style>{SCOPED_CSS}</style>

      {/* HEADER */}
      <header style={{ position: "sticky", top: 0, zIndex: 40, background: "color-mix(in srgb,var(--cream-50) 88%,transparent)", backdropFilter: "blur(10px)", borderBottom: "1px solid var(--border)" }}>
        <div style={{ maxWidth: 1240, margin: "0 auto", padding: "12px 24px", display: "flex", alignItems: "center", gap: 16 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <svg width="30" height="30" viewBox="-16 -16 32 32" aria-hidden="true"><path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke="var(--gold-500)" strokeWidth="2.6" strokeLinejoin="round" /><path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke="var(--green-800)" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
            <div style={{ fontSize: 19, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--green-900)" }}>Halal<span style={{ color: "var(--gold-600)" }}>One</span></div>
          </Link>
          <div style={{ width: 1, height: 22, background: "var(--border)" }} />
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--muted)" }}>Halal Market Intelligence</div>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 14 }}>
            <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--green-900)", background: "var(--gold-500)", padding: "3px 9px", borderRadius: 999 }}>Premium</span>
            <span style={{ ...kicker, letterSpacing: ".1em" }}>Module 5</span>
            <Link href="/" style={{ fontSize: 13, fontWeight: 700, color: "var(--green-800)" }}>Back to platform ↗</Link>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section style={{ background: "linear-gradient(160deg,#0F4B2E,#07351F)", color: "var(--cream-50)", position: "relative", overflow: "hidden" }}>
        <div aria-hidden="true" style={{ position: "absolute", inset: 0, backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M30 3L54 30L30 57L6 30Z' fill='none' stroke='rgba(251,250,246,0.05)' stroke-width='1'/%3E%3C/svg%3E\")", backgroundSize: "60px" }} />
        <div style={{ position: "relative", maxWidth: 1240, margin: "0 auto", padding: "52px 24px 58px", display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-end", gap: 32 }}>
          <div style={{ maxWidth: 660 }}>
            <div style={{ ...kicker, letterSpacing: ".14em", color: "var(--gold-500)" }}>Regulatory Intelligence · Market · Premium</div>
            <h1 style={{ margin: "16px 0 0", fontSize: "clamp(28px,3.6vw,42px)", lineHeight: 1.07, fontWeight: 800, letterSpacing: "-0.025em", color: "#fff", textWrap: "balance" }}>The global halal economy, measured.</h1>
            <p style={{ margin: "15px 0 0", fontSize: 16, lineHeight: 1.6, color: "color-mix(in srgb,var(--cream-50) 74%,transparent)", maxWidth: 580 }}>Market size, country profiles, sector analysis, trade corridors and the trends shaping a USD 2.1 trillion economy — synthesised into one intelligence brief.</p>
            <p style={{ margin: "14px 0 0", fontSize: 12, color: "color-mix(in srgb,var(--cream-50) 52%,transparent)" }}>Sources: State of Global Islamic Economy Report 2024/25 · ITC · OIC Statistical Commission · ICCD Research.</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 60, fontWeight: 800, lineHeight: 1, letterSpacing: "-0.03em", color: "#fff" }}>$2.1T</div>
            <div style={{ ...kicker, letterSpacing: ".14em", color: "var(--gold-500)", marginTop: 6 }}>Global market · 2025</div>
          </div>
        </div>
      </section>

      <div style={{ maxWidth: 1240, margin: "0 auto", padding: "0 24px 72px" }}>
        {/* BIG STATS */}
        <div className="mktintel-grid4" style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginTop: -28, position: "relative", zIndex: 10 }}>
          {bigStats.map((s) => (
            <div key={s.l} style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: 14, padding: "18px 18px", boxShadow: "var(--shadow-sm)", borderTop: "3px solid var(--gold-500)" }}>
              <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--green-900)", lineHeight: 1 }}>{s.v}</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--green-800)", marginTop: 8, lineHeight: 1.35 }}>{s.l}</div>
              <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 5, lineHeight: 1.45 }}>{s.n}</div>
            </div>
          ))}
        </div>

        {/* MARKET SIZE TIMELINE */}
        <section style={{ marginTop: 30 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 14 }}>
            <h2 style={h2}>Market size trajectory</h2>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>USD billions · 2022–2029</span>
          </div>
          <div style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: 16, padding: "22px 24px 18px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", alignItems: "flex-end", gap: 12, height: 200 }}>
              {timeline.map((t) => {
                const val = parseFloat(t.v.replace(/,/g, "")) || 0
                const pct = Math.round((val / maxTimeline) * 100)
                const forecast = /fcst/i.test(t.f ?? "")
                const barBg = t.est ? "linear-gradient(180deg,#196B24,#0F4B2E)" : forecast ? "color-mix(in srgb,var(--gold-500) 42%,transparent)" : "color-mix(in srgb,var(--green-700) 30%,transparent)"
                const valColor = t.est ? "var(--green-800)" : forecast ? "var(--gold-600)" : "var(--green-900)"
                const yearColor = t.est ? "var(--green-800)" : "var(--muted)"
                const flagColor = t.est ? "rgba(255,255,255,.9)" : "var(--gold-600)"
                return (
                  <div key={t.y} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", height: "100%", justifyContent: "flex-end", gap: 8 }}>
                    <div style={{ fontSize: 12, fontWeight: 800, fontFamily: "var(--mono)", color: valColor }}>{t.v}</div>
                    <div style={{ width: "100%", borderRadius: "8px 8px 0 0", height: `${pct}%`, background: barBg, transition: "height .4s ease", position: "relative" }}>
                      {t.f && <div style={{ position: "absolute", top: 6, left: "50%", transform: "translateX(-50%)", fontSize: 8, fontWeight: 800, letterSpacing: ".06em", color: flagColor, whiteSpace: "nowrap" }}>{t.f}</div>}
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: yearColor }}>{t.y}</div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        {/* COUNTRY TABLE */}
        <section style={{ marginTop: 30 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 12, marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
              <h2 style={h2}>Country market profiles</h2>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>{countryCountLabel}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, background: "#fff", border: "1px solid var(--border)", borderRadius: 10, padding: "8px 12px", boxShadow: "var(--shadow-sm)" }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="11" cy="11" r="8" stroke="#657269" strokeWidth="2" /><path d="m21 21-4.35-4.35" stroke="#657269" strokeWidth="2" strokeLinecap="round" /></svg>
              <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search country…" style={{ border: "none", outline: "none", background: "transparent", fontFamily: "var(--font)", fontSize: 13, color: "var(--green-900)", width: 150 }} />
            </div>
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
            {regionTabs.map((t) => (
              <button key={t.id} onClick={() => setRegion(t.id)} style={t.active
                ? { padding: "6px 13px", borderRadius: 999, border: "1px solid var(--green-800)", background: "var(--green-800)", color: "#fff", cursor: "pointer", fontFamily: "var(--font)", fontSize: 11.5, fontWeight: 700 }
                : { padding: "6px 13px", borderRadius: 999, border: "1px solid var(--border)", background: "#fff", color: "var(--muted)", cursor: "pointer", fontFamily: "var(--font)", fontSize: 11.5, fontWeight: 700 }}>
                {t.label} <span style={{ opacity: t.active ? 0.6 : 0.55 }}>{t.n}</span>
              </button>
            ))}
          </div>
          <div style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: 16, overflow: "hidden", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 940 }}>
                <thead>
                  <tr style={{ background: "var(--green-800)" }}>
                    <th style={{ ...th, padding: "12px 16px" }}>Country</th>
                    <th style={th}>Market size</th>
                    <th style={th}>YoY</th>
                    <th style={th}>Muslim pop.</th>
                    <th style={th}>Per-capita</th>
                    <th style={th}>Maturity</th>
                    <th style={th}>Role &amp; top categories</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCountries.map((c, idx) => {
                    const ms = maturityStyle(c.maturity)
                    const rowBg = idx % 2 ? "color-mix(in srgb,var(--cream-100) 40%,transparent)" : "#fff"
                    return (
                      <tr key={c.name} style={{ borderTop: "1px solid var(--cream-100)", background: rowBg }}>
                        <td style={{ padding: "12px 16px", verticalAlign: "top" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                            <span style={{ fontSize: 20 }}>{c.flag}</span>
                            <div>
                              <div style={{ fontSize: 13, fontWeight: 700, color: "var(--green-900)" }}>{c.name}</div>
                              <div style={{ fontSize: 10, color: "var(--muted)" }}>{c.region}</div>
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: "12px 12px", verticalAlign: "top", minWidth: 130 }}>
                          <div style={{ fontSize: 13, fontWeight: 800, color: "var(--green-900)", fontFamily: "var(--mono)" }}>{c.size}</div>
                          <div style={{ height: 5, background: "var(--cream-100)", borderRadius: 4, overflow: "hidden", marginTop: 5 }}><div style={{ height: "100%", width: `${c.bar}%`, background: "var(--green-700)", borderRadius: 4 }} /></div>
                        </td>
                        <td style={{ padding: "12px 12px", verticalAlign: "top", fontSize: 12.5, fontWeight: 700, color: "var(--green-700)", fontFamily: "var(--mono)" }}>{c.yoy}</td>
                        <td style={{ padding: "12px 12px", verticalAlign: "top" }}><div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--green-900)" }}>{c.muslim}</div><div style={{ fontSize: 10, color: "var(--muted)" }}>{c.muslimPct}</div></td>
                        <td style={{ padding: "12px 12px", verticalAlign: "top", fontSize: 12.5, fontWeight: 700, color: "var(--ink)", fontFamily: "var(--mono)" }}>{c.perCap}</td>
                        <td style={{ padding: "12px 12px", verticalAlign: "top" }}><span style={{ display: "inline-block", padding: "3px 10px", borderRadius: 999, fontSize: 10, fontWeight: 800, background: ms.bg, color: ms.fg, border: `1px solid ${ms.border}`, whiteSpace: "nowrap" }}>{c.maturity}</span></td>
                        <td style={{ padding: "12px 12px", verticalAlign: "top", maxWidth: 220 }}><div style={{ fontSize: 11, fontWeight: 700, color: "var(--green-800)", lineHeight: 1.4 }}>{c.role}</div><div style={{ fontSize: 10.5, color: "var(--muted)", marginTop: 3, lineHeight: 1.4 }}>{c.cats}</div></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {filteredCountries.length === 0 && (
              <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--muted)", fontSize: 13 }}>No countries match your search.</div>
            )}
          </div>
        </section>

        {/* SECTORS */}
        <section style={{ marginTop: 34 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 14 }}>
            <h2 style={h2}>Sector analysis</h2>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>Six pillars of the halal economy</span>
          </div>
          <div className="mktintel-grid3" style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
            {sectors.map((s) => (
              <div key={s.name} style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: 16, overflow: "hidden", boxShadow: "var(--shadow-sm)", borderTop: "4px solid var(--green-700)" }}>
                <div style={{ padding: "18px 18px 16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                    <div style={{ fontSize: 15, fontWeight: 800, color: "var(--green-900)", letterSpacing: "-0.01em" }}>{s.name}</div>
                    <div style={{ textAlign: "right", flex: "0 0 auto" }}>
                      <div style={{ fontSize: 16, fontWeight: 800, color: "var(--green-700)", fontFamily: "var(--mono)" }}>{s.size}</div>
                      <div style={{ fontSize: 10, color: "var(--muted)", marginTop: 1 }}>{s.pctOfMkt}</div>
                    </div>
                  </div>
                  <div style={{ height: 8, background: "var(--cream-100)", borderRadius: 4, margin: "12px 0 8px", overflow: "hidden" }}><div style={{ height: 8, width: `${s.bar}%`, background: "var(--green-700)", borderRadius: 4 }} /></div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--muted)", marginBottom: 14 }}>
                    <span>CAGR <b style={{ color: "var(--gold-600)" }}>{s.cagr}</b></span>
                    <span>2024–2029</span>
                  </div>
                  <div style={{ ...kicker, fontSize: 9.5, marginBottom: 4 }}>Top markets</div>
                  <div style={{ fontSize: 11.5, color: "var(--ink)", marginBottom: 11, lineHeight: 1.4 }}>{s.topMarkets}</div>
                  <div style={{ ...kicker, fontSize: 9.5, marginBottom: 4 }}>Key players</div>
                  <div style={{ fontSize: 11.5, color: "var(--ink)", marginBottom: 12, lineHeight: 1.4 }}>{s.keyPlayers}</div>
                  <div style={{ background: "var(--cream-100)", border: "1px solid var(--border)", borderRadius: 10, padding: "11px 13px", fontSize: 11.5, color: "var(--ink)", lineHeight: 1.6 }}>{s.note}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* TRENDS */}
        <section style={{ marginTop: 34 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 14 }}>
            <h2 style={h2}>Trends shaping the market</h2>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>Eight forces to watch</span>
          </div>
          <div className="mktintel-grid4" style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
            {trends.map((t) => (
              <div key={t.title} style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: 16, padding: 18, boxShadow: "var(--shadow-sm)" }}>
                <div style={{ width: 38, height: 38, borderRadius: 11, background: "color-mix(in srgb,var(--gold-500) 16%,transparent)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>{t.icon}</div>
                <div style={{ fontSize: 13.5, fontWeight: 800, color: "var(--green-900)", lineHeight: 1.3, margin: "12px 0 8px" }}>{t.title}</div>
                <div style={{ fontSize: 11.5, color: "var(--ink)", lineHeight: 1.6 }}>{t.desc}</div>
              </div>
            ))}
          </div>
        </section>

        {/* TRADE CORRIDORS */}
        <section style={{ marginTop: 34 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 14 }}>
            <h2 style={h2}>Major trade corridors</h2>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>Top halal trade flows by value</span>
          </div>
          <div style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: 16, overflow: "hidden", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 900 }}>
                <thead>
                  <tr style={{ background: "var(--green-800)" }}>
                    <th style={{ ...th, padding: "12px 16px" }}>Corridor</th>
                    <th style={th}>Category</th>
                    <th style={th}>Annual value</th>
                    <th style={th}>YoY</th>
                    <th style={th}>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {corridors.map((c, idx) => (
                    <tr key={`${c.from}-${c.to}`} style={{ borderTop: "1px solid var(--cream-100)", background: idx % 2 ? "color-mix(in srgb,var(--cream-100) 40%,transparent)" : "#fff" }}>
                      <td style={{ padding: "12px 16px", verticalAlign: "top" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 7, flexWrap: "wrap" }}>
                          <span style={{ fontSize: 12.5, fontWeight: 800, color: "var(--green-800)" }}>{c.from}</span>
                          <svg width="18" height="10" viewBox="0 0 22 12" fill="none" aria-hidden="true"><path d="M0 6h18M14 1l5 5-5 5" stroke="var(--gold-500)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                          <span style={{ fontSize: 12.5, fontWeight: 800, color: "var(--green-900)" }}>{c.to}</span>
                        </div>
                        <div style={{ fontSize: 10.5, color: "var(--muted)", marginTop: 3 }}>Players: {c.players}</div>
                      </td>
                      <td style={{ padding: "12px 12px", verticalAlign: "top" }}><span style={{ display: "inline-block", padding: "3px 10px", borderRadius: 999, fontSize: 10.5, fontWeight: 700, background: "var(--cream-100)", color: "var(--muted)", border: "1px solid var(--border)" }}>{c.category}</span></td>
                      <td style={{ padding: "12px 12px", verticalAlign: "top", fontSize: 14, fontWeight: 800, color: "var(--green-900)", fontFamily: "var(--mono)" }}>{c.value}</td>
                      <td style={{ padding: "12px 12px", verticalAlign: "top", fontSize: 12.5, fontWeight: 800, color: "var(--green-700)", fontFamily: "var(--mono)" }}>{c.yoy}</td>
                      <td style={{ padding: "12px 12px", verticalAlign: "top", maxWidth: 320, fontSize: 11.5, color: "var(--ink)", lineHeight: 1.55 }}>{c.notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>

      {/* FOOTER */}
      <footer style={{ background: "linear-gradient(160deg,#0F4B2E,#07351F)", color: "var(--cream-50)" }}>
        <div style={{ maxWidth: 1240, margin: "0 auto", padding: "38px 24px", display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
            <svg width="28" height="28" viewBox="-16 -16 32 32" aria-hidden="true"><path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke="var(--gold-500)" strokeWidth="2.6" strokeLinejoin="round" /><path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke="var(--cream-50)" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
            <div>
              <div style={{ fontSize: 16, fontWeight: 800, letterSpacing: "-0.02em", color: "#fff" }}>Halal<span style={{ color: "var(--gold-500)" }}>One</span></div>
              <div style={{ fontSize: 11, color: "color-mix(in srgb,var(--cream-50) 60%,transparent)" }}>Halal Market Intelligence · Module 5</div>
            </div>
          </div>
          <div style={{ fontSize: 11.5, color: "color-mix(in srgb,var(--cream-50) 60%,transparent)", maxWidth: 540, lineHeight: 1.6, textAlign: "right" }}>Market figures are aggregated third-party estimates for orientation and planning, not investment advice. Verify against primary sources before commercial decisions.</div>
        </div>
      </footer>
    </div>
  )
}
