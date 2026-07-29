"use client"

import { useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import Link from "next/link"

import Button from "@/components/halalone/Button"
import Card from "@/components/halalone/Card"
import Badge from "@/components/halalone/Badge"
import Logo from "@/components/halalone/Logo"
import Icon from "@/components/halalone/Icon"
import SearchBar from "@/components/halalone/SearchBar"

import {
  heroStats, certAuthorities, suggestedPrompts, aiCapabilities, products,
  repoFilters, repoData, trending, scanSteps, scanIngredients, mobileFeatures,
  kpis, growthBars, regions, trustPillars, socials, footerCols,
} from "./data"

import "./landing.css"

// Where every primary call-to-action leads: the chat/dashboard.
const APP = "/chat"

// The two directory routes.
const CERT_DIR = "/directory/certification-authority-directory"
const REG_INTEL = "/directory/regulatory-intelligence"

// Real destinations for footer link labels; anything unmapped stays a "#" stub.
const FOOTER_ROUTES: Record<string, string> = {
  "AI Assistant": APP,
  "Repository": CERT_DIR,
  "OCR Scanner": APP,
  "Standards": REG_INTEL,
  "Certification lookup": CERT_DIR,
}

const overline = { fontSize: 11, fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase" as const, color: "var(--gold-600)" }
const h2Style = { margin: "14px 0 0", fontSize: "clamp(30px, 3.6vw, 44px)", lineHeight: 1.1, fontWeight: 800, letterSpacing: "-0.022em", color: "var(--text-heading)" }
const sectionInner = { maxWidth: 1200, margin: "0 auto", padding: "96px 32px" }

type BadgeVariant = "verified" | "warning" | "danger"

// Passed from the server page: present when the visitor is signed in, so the
// nav can show their profile and the CTAs can go straight to the app.
type Profile = { name: string; email: string; avatarUrl: string }

export default function Landing({ profile = null }: { profile?: Profile | null }) {
  const rootRef = useRef<HTMLDivElement>(null)
  const router = useRouter()

  // "Get started" goes straight to the app when already signed in; otherwise to
  // login, carrying ?next=/chat so the user lands on the chat after signing in.
  const START = profile ? APP : "/login?next=/chat"
  const firstName = profile?.name ? profile.name.split(" ")[0] : ""

  // Scroll-reveal — mirrors the original IntersectionObserver behaviour.
  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    const els = root.querySelectorAll<HTMLElement>("[data-reveal]")
    if (!("IntersectionObserver" in window)) {
      els.forEach((e) => e.classList.add("is-in"))
      return
    }
    const io = new IntersectionObserver(
      (entries) => entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target) } }),
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" },
    )
    els.forEach((e) => io.observe(e))
    return () => io.disconnect()
  }, [])

  const goToApp = () => router.push(APP)

  return (
    <div ref={rootRef} className="hl-root">
      <div style={{ minHeight: "100vh", background: "var(--cream-50)", overflowX: "hidden" }}>

        {/* ============ NAV ============ */}
        <header style={{ position: "sticky", top: 0, zIndex: 50, background: "color-mix(in srgb, var(--cream-50) 82%, transparent)", backdropFilter: "saturate(1.4) blur(14px)", WebkitBackdropFilter: "saturate(1.4) blur(14px)", borderBottom: "1px solid var(--border-subtle)" }}>
          <nav style={{ maxWidth: 1200, margin: "0 auto", height: 68, padding: "0 32px", display: "flex", alignItems: "center", gap: 20 }}>
            <a href="#top" style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Logo size={24} />
            </a>
            <div className="hl-navcenter" style={{ display: "flex", alignItems: "center", gap: 2, marginLeft: 18 }}>
              <a className="hl-navlink" href="#ai">AI Assistant</a>
              <a className="hl-navlink" href="#repository">Repository</a>
              <Link className="hl-navlink" href={CERT_DIR}>Directory</Link>
              <Link className="hl-navlink" href={REG_INTEL}>Regulatory</Link>
              <a className="hl-navlink" href="#scanner">Scanner</a>
              <a className="hl-navlink" href="#mobile">Mobile</a>
              <a className="hl-navlink" href="#trust">Trust</a>
            </div>
            <div className="hl-nav-actions" style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
              <button className="hl-hide-sm" aria-label="Search" style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 38, height: 38, borderRadius: "var(--radius-pill)", border: "1px solid var(--border-subtle)", background: "var(--white)", cursor: "pointer" }}>
                <Icon name="search" size={18} color="var(--charcoal-600)" />
              </button>
              <button className="hl-hide-sm" aria-label="Language" style={{ display: "inline-flex", alignItems: "center", gap: 5, height: 38, padding: "0 12px", borderRadius: "var(--radius-pill)", border: "1px solid var(--border-subtle)", background: "var(--white)", cursor: "pointer", fontFamily: "var(--font-sans)", fontSize: 13, fontWeight: 700, color: "var(--charcoal-600)" }}>
                <Icon name="globe" size={16} color="var(--charcoal-600)" />
                EN
              </button>
              {profile ? (
                <>
                  <Button size="sm" href={APP}>Open dashboard</Button>
                  <Link href={APP} aria-label="Open the app" style={{ display: "inline-flex", alignItems: "center", gap: 9 }}>
                    {profile.avatarUrl ? (
                      <span style={{ width: 34, height: 34, borderRadius: "50%", backgroundImage: `url(${profile.avatarUrl})`, backgroundSize: "cover", backgroundPosition: "center", border: "1px solid var(--border-subtle)", flex: "0 0 auto" }} />
                    ) : (
                      <span style={{ width: 34, height: 34, borderRadius: "50%", background: "var(--green-800)", color: "var(--white)", display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 14, flex: "0 0 auto" }}>{(profile.name || "U").charAt(0).toUpperCase()}</span>
                    )}
                    <span className="hl-hide-sm" style={{ fontSize: 14, fontWeight: 700, color: "var(--green-900)", letterSpacing: "-0.01em" }}>{firstName}</span>
                  </Link>
                </>
              ) : (
                <>
                  <Link className="hl-navlink hl-hide-sm" href="/login" style={{ color: "var(--green-900)" }}>Sign in</Link>
                  <Button size="sm" href={START}>Get started</Button>
                </>
              )}
            </div>
          </nav>
        </header>

        {/* ============ HERO ============ */}
        <section id="top" className="hl-on-dark" style={{ position: "relative", background: "radial-gradient(120% 120% at 80% -10%, #12583a 0%, var(--green-800) 42%, var(--green-900) 100%)", color: "var(--cream-50)", overflow: "hidden" }}>
          <div aria-hidden="true" style={{ position: "absolute", inset: 0, backgroundImage: "radial-gradient(color-mix(in srgb, var(--cream-50) 6%, transparent) 1px, transparent 1px)", backgroundSize: "26px 26px", opacity: 0.5 }} />
          <div aria-hidden="true" style={{ position: "absolute", top: -140, right: -120, width: 520, height: 520, borderRadius: "var(--radius-pill)", background: "radial-gradient(circle, color-mix(in srgb, var(--gold-500) 22%, transparent) 0%, transparent 68%)" }} />
          <div className="hl-hero-grid" style={{ position: "relative", maxWidth: 1200, margin: "0 auto", padding: "84px 32px 76px", display: "grid", gridTemplateColumns: "1.05fr 0.95fr", gap: 56, alignItems: "center" }}>
            <div>
              <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 14px", borderRadius: "var(--radius-pill)", border: "1px solid var(--border-on-dark)", background: "color-mix(in srgb, var(--cream-50) 8%, transparent)", fontSize: 11, fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--gold-500)" }}>
                Islamic Chamber of Commerce &amp; Development
              </div>
              <h1 style={{ margin: "22px 0 0", fontSize: "clamp(38px, 5.2vw, 62px)", lineHeight: 1.04, fontWeight: 800, letterSpacing: "-0.025em", color: "var(--white)", textWrap: "balance" }}>
                The world&rsquo;s most advanced AI&#8209;powered Halal ecosystem.
              </h1>
              <p style={{ margin: "22px 0 0", maxWidth: 540, fontSize: 18, lineHeight: 1.6, color: "var(--text-on-dark-muted)" }}>
                Verify products, decode ingredients, and search the global Halal repository — with AI that explains every answer and cites its sources. One platform. Every halal answer.
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 30 }}>
                <Button variant="gold" size="lg" href={START}>Get started</Button>
                <Button variant="secondary" size="lg" href="#ai" style={{ color: "var(--cream-50)", borderColor: "var(--border-on-dark)" }}>See the AI in action</Button>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 32, marginTop: 44, paddingTop: 30, borderTop: "1px solid var(--border-on-dark)" }}>
                {heroStats.map((s) => (
                  <div key={s.label}>
                    <div style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--white)" }}>{s.value}</div>
                    <div style={{ marginTop: 3, fontSize: 12.5, fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase", color: "var(--text-on-dark-muted)" }}>{s.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Interactive AI verification card */}
            <div style={{ position: "relative" }}>
              <div style={{ position: "absolute", inset: -18, borderRadius: 32, background: "radial-gradient(circle at 30% 0%, color-mix(in srgb, var(--gold-500) 16%, transparent), transparent 70%)" }} />
              <div style={{ position: "relative", background: "var(--white)", color: "var(--text-body)", borderRadius: "var(--radius-xl)", boxShadow: "0 30px 80px rgba(3, 30, 18, .45)", padding: 22, border: "1px solid var(--border-subtle)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 9, paddingBottom: 14, borderBottom: "1px solid var(--border-subtle)" }}>
                  <div style={{ width: 28, height: 28, borderRadius: 8, background: "var(--green-800)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Icon name="sparkles" size={16} color="var(--gold-500)" />
                  </div>
                  <div style={{ fontWeight: 800, fontSize: 14, color: "var(--green-900)", letterSpacing: "-0.01em" }}>Halal One Assistant</div>
                  <span style={{ marginLeft: "auto", fontSize: 11, fontWeight: 700, color: "var(--green-700)", display: "inline-flex", alignItems: "center", gap: 5 }}>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--green-700)", animation: "hl-pulse 2s var(--ease-standard) infinite" }} />Online
                  </span>
                </div>
                <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
                  <div style={{ background: "var(--cream-100)", border: "1px solid var(--border-subtle)", borderRadius: "16px 16px 4px 16px", padding: "10px 14px", fontSize: 14, maxWidth: "78%" }}>Is the emulsifier E471 halal?</div>
                </div>
                <div style={{ marginTop: 14, background: "color-mix(in srgb, var(--green-800) 5%, var(--white))", border: "1px solid var(--border-subtle)", borderRadius: "16px 16px 16px 4px", padding: 14 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                    <Badge variant="warning">Depends on source</Badge>
                  </div>
                  <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: "var(--text-body)" }}>E471 (mono&#8209; and diglycerides) is halal when plant&#8209;derived, but requires verification when the source is animal fat. Always confirm certification.</p>
                  <div style={{ marginTop: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, fontWeight: 700, color: "var(--text-muted)", marginBottom: 6 }}><span>Confidence</span><span style={{ color: "var(--green-800)" }}>94%</span></div>
                    <div style={{ height: 7, borderRadius: 999, background: "var(--green-100)", overflow: "hidden" }}><div style={{ width: "94%", height: "100%", borderRadius: 999, background: "linear-gradient(90deg, var(--green-700), var(--gold-500))" }} /></div>
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 14 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", display: "inline-flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 999, background: "var(--cream-100)", border: "1px solid var(--border-subtle)" }}>
                      <Icon name="file-text" size={12} color="var(--green-800)" />JAKIM Standard MS1500
                    </span>
                    <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", display: "inline-flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 999, background: "var(--cream-100)", border: "1px solid var(--border-subtle)" }}>
                      <Icon name="database" size={12} color="var(--green-800)" />Ingredient Repository
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ============ CERT AUTHORITY STRIP ============ */}
        <section style={{ background: "var(--white)", borderBottom: "1px solid var(--border-subtle)" }}>
          <div style={{ maxWidth: 1200, margin: "0 auto", padding: "30px 32px", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "14px 28px" }}>
            <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--text-muted)" }}>Trusted across leading certification authorities</span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginLeft: "auto" }}>
              {certAuthorities.map((c) => (
                <span key={c} className="hl-chip" style={{ fontSize: 13, fontWeight: 700, color: "var(--green-900)", padding: "7px 14px", borderRadius: "var(--radius-pill)", background: "var(--cream-100)", border: "1px solid var(--border-subtle)" }}>{c}</span>
              ))}
            </div>
          </div>
        </section>

        {/* ============ AI ASSISTANT ============ */}
        <section id="ai" style={{ background: "var(--cream-50)" }}>
          <div style={sectionInner}>
            <div data-reveal="" style={{ maxWidth: 720 }}>
              <div style={{ ...overline, color: "var(--gold-600)" }}>Halal AI Assistant</div>
              <h2 style={h2Style}>Ask anything halal — and understand exactly why.</h2>
              <p style={{ margin: "16px 0 0", fontSize: 18, lineHeight: 1.6, color: "var(--text-muted)" }}>Not a chatbot. An intelligence layer over the global repository that verifies products, decodes ingredients, and cites every source behind its answer.</p>
            </div>

            <div className="hl-split" data-reveal="" style={{ marginTop: 44, display: "grid", gridTemplateColumns: "1.15fr 0.85fr", gap: 24, alignItems: "start" }}>
              <Card padded={false} style={{ overflow: "hidden" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "16px 22px", borderBottom: "1px solid var(--border-subtle)", background: "var(--cream-100)" }}>
                  <div style={{ width: 30, height: 30, borderRadius: 9, background: "var(--green-800)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Icon name="sparkles" size={17} color="var(--gold-500)" />
                  </div>
                  <div style={{ fontWeight: 800, fontSize: 15, color: "var(--green-900)" }}>Conversation</div>
                  <span style={{ marginLeft: "auto", fontSize: 12, fontWeight: 700, color: "var(--text-muted)" }}>Grounded in 2.4M verified records</span>
                </div>
                <div style={{ padding: 22, display: "flex", flexDirection: "column", gap: 14 }}>
                  <div style={{ alignSelf: "flex-end", maxWidth: "82%", background: "var(--cream-100)", border: "1px solid var(--border-subtle)", borderRadius: "16px 16px 4px 16px", padding: "11px 15px", fontSize: 14.5 }}>Is this product halal? MILO Activ&#8209;Go, certificate JAKIM/2024/8821.</div>
                  <div style={{ alignSelf: "flex-start", maxWidth: "92%", background: "var(--white)", border: "1px solid var(--border-subtle)", borderRadius: "16px 16px 16px 4px", padding: 16, boxShadow: "var(--shadow-sm)" }}>
                    <div style={{ marginBottom: 10 }}><Badge variant="verified">Halal — verified</Badge></div>
                    <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.62, color: "var(--text-body)" }}>Certificate <strong>JAKIM/2024/8821</strong> is active and valid through March 2026. All 14 ingredients cross&#8209;reference cleanly against the repository; no flagged additives.</p>
                    <div style={{ marginTop: 14, display: "flex", flexWrap: "wrap", gap: 7 }}>
                      <span style={{ fontSize: 11.5, fontWeight: 700, color: "var(--green-800)", display: "inline-flex", alignItems: "center", gap: 5, padding: "5px 11px", borderRadius: 999, background: "color-mix(in srgb, var(--green-700) 12%, transparent)" }}>
                        <Icon name="badge-check" size={13} color="var(--green-800)" />Certificate verified
                      </span>
                      <span style={{ fontSize: 11.5, fontWeight: 700, color: "var(--text-muted)", display: "inline-flex", alignItems: "center", gap: 5, padding: "5px 11px", borderRadius: 999, background: "var(--cream-100)", border: "1px solid var(--border-subtle)" }}>14 ingredients checked</span>
                    </div>
                  </div>
                </div>
                <div style={{ padding: "0 22px 20px" }}>
                  <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 10 }}>Suggested prompts</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {suggestedPrompts.map((q) => (
                      <button key={q} className="hl-chip" onClick={goToApp} style={{ fontSize: 13, fontWeight: 600, color: "var(--green-900)", padding: "8px 14px", borderRadius: "var(--radius-pill)", background: "var(--white)", border: "1px solid var(--border-subtle)", cursor: "pointer", textAlign: "left" }}>{q}</button>
                    ))}
                  </div>
                </div>
              </Card>

              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {aiCapabilities.map((cap) => (
                  <Card key={cap.title} interactive>
                    <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                      <div style={{ flex: "0 0 auto", width: 40, height: 40, borderRadius: 11, background: "color-mix(in srgb, var(--green-800) 8%, transparent)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <Icon name={cap.icon} size={20} color="var(--green-800)" />
                      </div>
                      <div>
                        <div style={{ fontWeight: 800, fontSize: 15.5, color: "var(--green-900)", letterSpacing: "-0.01em" }}>{cap.title}</div>
                        <p style={{ margin: "4px 0 0", fontSize: 13.5, lineHeight: 1.55, color: "var(--text-muted)" }}>{cap.desc}</p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ============ PRODUCT INTELLIGENCE ============ */}
        <section id="intelligence" style={{ background: "var(--white)", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={sectionInner}>
            <div data-reveal="" style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", justifyContent: "space-between", gap: 20 }}>
              <div style={{ maxWidth: 640 }}>
                <div style={overline}>Product Intelligence</div>
                <h2 style={h2Style}>Every product, verified and explained.</h2>
              </div>
              <p style={{ maxWidth: 340, fontSize: 15, lineHeight: 1.6, color: "var(--text-muted)" }}>Certification status, country of origin, ingredient breakdown and an AI summary — on a single card.</p>
            </div>

            <div data-reveal="" style={{ marginTop: 40, display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(270px, 1fr))", gap: 20 }}>
              {products.map((p) => (
                <Card key={p.name} interactive padded={false} style={{ overflow: "hidden", display: "flex", flexDirection: "column" }}>
                  <div style={{ position: "relative", height: 128, background: "linear-gradient(135deg, var(--cream-100), color-mix(in srgb, var(--green-800) 6%, var(--cream-100)))", display: "flex", alignItems: "center", justifyContent: "center", borderBottom: "1px solid var(--border-subtle)" }}>
                    <Icon name={p.icon} size={40} color="color-mix(in srgb, var(--green-800) 40%, transparent)" />
                    <div style={{ position: "absolute", top: 12, left: 12 }}><Badge variant={p.badge as BadgeVariant} size="sm">{p.statusLabel}</Badge></div>
                  </div>
                  <div style={{ padding: "16px 18px 18px", display: "flex", flexDirection: "column", flex: 1 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)" }}>{p.brand}</div>
                    <div style={{ fontSize: 16.5, fontWeight: 800, color: "var(--green-900)", letterSpacing: "-0.01em", marginTop: 2 }}>{p.name}</div>
                    <div style={{ display: "flex", gap: 14, marginTop: 12, fontSize: 12.5, color: "var(--text-muted)" }}>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><Icon name="map-pin" size={13} color="var(--charcoal-600)" />{p.country}</span>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><Icon name="stamp" size={13} color="var(--charcoal-600)" />{p.authority}</span>
                    </div>
                    <p style={{ margin: "12px 0 0", fontSize: 13, lineHeight: 1.5, color: "var(--text-body)", flex: 1 }}>{p.summary}</p>
                    <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)" }}>AI confidence</span>
                      <span style={{ fontSize: 15, fontWeight: 800, color: "var(--green-800)" }}>{p.confidence}</span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* ============ REPOSITORY ============ */}
        <section id="repository" style={{ background: "var(--cream-50)", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={sectionInner}>
            <div data-reveal="" style={{ maxWidth: 720 }}>
              <div style={overline}>Global Repository</div>
              <h2 style={h2Style}>Search the world&rsquo;s halal record.</h2>
              <p style={{ margin: "16px 0 0", fontSize: 18, lineHeight: 1.6, color: "var(--text-muted)" }}>Millions of products, ingredients, manufacturers and certificates — filterable by authority, country and category.</p>
            </div>

            <div data-reveal="" style={{ marginTop: 32, background: "var(--white)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-xl)", boxShadow: "var(--shadow-sm)", overflow: "hidden" }}>
              <div style={{ padding: 20, borderBottom: "1px solid var(--border-subtle)" }}>
                <SearchBar placeholder="Search products, ingredients, certificates or manufacturers" size="lg" onSubmit={goToApp} />
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14 }}>
                  {repoFilters.map((f) => (
                    <button key={f} className="hl-chip" style={{ fontSize: 13, fontWeight: 700, color: "var(--green-900)", padding: "7px 14px", borderRadius: "var(--radius-pill)", background: "var(--cream-100)", border: "1px solid var(--border-subtle)", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6 }}>{f}<Icon name="chevron-down" size={13} color="var(--charcoal-600)" /></button>
                  ))}
                </div>
              </div>
              <div>
                {repoData.map((r) => (
                  <div
                    key={r.name}
                    className="hl-chip"
                    style={{ display: "flex", alignItems: "center", gap: 16, padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)", cursor: "pointer" }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "var(--cream-100)" }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "transparent" }}
                    onClick={goToApp}
                  >
                    <div style={{ flex: "0 0 auto", width: 42, height: 42, borderRadius: 11, background: "var(--cream-100)", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <Icon name={r.icon} size={19} color="var(--green-800)" />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 15, fontWeight: 800, color: "var(--green-900)" }}>{r.name}</div>
                      <div style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 2 }}>{r.meta}</div>
                    </div>
                    <Badge variant={r.badge as BadgeVariant} size="sm">{r.statusLabel}</Badge>
                    <span style={{ fontSize: 12, color: "var(--text-muted)", minWidth: 90, textAlign: "right" }}>{r.updated}</span>
                  </div>
                ))}
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px", background: "var(--cream-100)" }}>
                <span style={{ fontSize: 13, color: "var(--text-muted)" }}>Showing verified results from the global repository</span>
                <Button variant="ghost" size="sm" href={APP}>View all results</Button>
              </div>
            </div>

            <div data-reveal="" style={{ marginTop: 20, display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
              <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-muted)" }}>Trending</span>
              {trending.map((t) => (
                <span key={t} className="hl-chip" style={{ fontSize: 13, fontWeight: 600, color: "var(--green-900)", padding: "6px 13px", borderRadius: "var(--radius-pill)", background: "var(--white)", border: "1px solid var(--border-subtle)" }}>{t}</span>
              ))}
            </div>
          </div>
        </section>

        {/* ============ OCR SCANNER ============ */}
        <section id="scanner" className="hl-on-dark" style={{ background: "var(--green-800)", color: "var(--cream-50)", position: "relative", overflow: "hidden" }}>
          <div aria-hidden="true" style={{ position: "absolute", inset: 0, backgroundImage: "radial-gradient(color-mix(in srgb, var(--cream-50) 6%, transparent) 1px, transparent 1px)", backgroundSize: "26px 26px", opacity: 0.4 }} />
          <div className="hl-split" style={{ position: "relative", maxWidth: 1200, margin: "0 auto", padding: "96px 32px", display: "grid", gridTemplateColumns: "0.8fr 1.2fr", gap: 56, alignItems: "center" }}>
            <div data-reveal="" style={{ justifySelf: "center" }}>
              <div style={{ width: 260, height: 520, borderRadius: 42, background: "#071f14", padding: 12, boxShadow: "0 40px 90px rgba(0,0,0,.5)", border: "1px solid color-mix(in srgb, var(--cream-50) 16%, transparent)" }}>
                <div style={{ position: "relative", width: "100%", height: "100%", borderRadius: 32, overflow: "hidden", background: "linear-gradient(160deg, #0d3f28, #07351f)" }}>
                  <div style={{ position: "absolute", top: 14, left: "50%", transform: "translateX(-50%)", width: 90, height: 22, borderRadius: 999, background: "#050f0a" }} />
                  <div style={{ position: "absolute", inset: "44px 20px auto", display: "flex", alignItems: "center", gap: 8, color: "var(--cream-50)", fontSize: 13, fontWeight: 700 }}>
                    <Icon name="scan-line" size={16} color="var(--gold-500)" />Scanning label
                  </div>
                  <div style={{ position: "absolute", inset: "82px 20px 150px", borderRadius: 16, border: "2px solid color-mix(in srgb, var(--gold-500) 70%, transparent)", background: "color-mix(in srgb, var(--cream-50) 6%, transparent)", overflow: "hidden" }}>
                    <div style={{ position: "absolute", left: 0, right: 0, height: 2, background: "linear-gradient(90deg, transparent, var(--gold-500), transparent)", boxShadow: "0 0 14px var(--gold-500)", animation: "hl-scanline 2.6s var(--ease-standard) infinite" }} />
                    <div style={{ position: "absolute", inset: 14, display: "flex", flexDirection: "column", gap: 7, opacity: 0.55 }}>
                      <div style={{ height: 8, width: "70%", borderRadius: 3, background: "var(--cream-50)" }} />
                      <div style={{ height: 8, width: "90%", borderRadius: 3, background: "var(--cream-50)" }} />
                      <div style={{ height: 8, width: "55%", borderRadius: 3, background: "var(--cream-50)" }} />
                      <div style={{ height: 8, width: "82%", borderRadius: 3, background: "var(--cream-50)" }} />
                    </div>
                  </div>
                  <div style={{ position: "absolute", left: 20, right: 20, bottom: 24, background: "var(--white)", borderRadius: 16, padding: 14, color: "var(--text-body)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Badge variant="verified" size="sm">Halal</Badge>
                      <span style={{ marginLeft: "auto", fontSize: 12, fontWeight: 800, color: "var(--green-800)" }}>98%</span>
                    </div>
                    <div style={{ marginTop: 8, fontSize: 12, color: "var(--text-muted)" }}>14 ingredients read · 0 flagged</div>
                  </div>
                </div>
              </div>
            </div>

            <div data-reveal="">
              <div style={{ ...overline, color: "var(--gold-500)" }}>OCR Ingredient Scanner</div>
              <h2 style={{ ...h2Style, fontSize: "clamp(28px, 3.4vw, 42px)", color: "var(--white)" }}>Point. Scan. Understand.</h2>
              <p style={{ margin: "14px 0 0", maxWidth: 520, fontSize: 17, lineHeight: 1.6, color: "var(--text-on-dark-muted)" }}>Capture any label and the scanner reads every ingredient, cross&#8209;references the repository, and returns a confidence&#8209;scored verdict with reasoning.</p>

              <div style={{ marginTop: 28, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {scanSteps.map((st) => (
                    <div key={st.title} style={{ display: "flex", gap: 12, alignItems: "flex-start", padding: "8px 0" }}>
                      <div style={{ flex: "0 0 auto", width: 34, height: 34, borderRadius: 10, background: "color-mix(in srgb, var(--cream-50) 12%, transparent)", border: "1px solid var(--border-on-dark)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <Icon name={st.icon} size={17} color="var(--gold-500)" />
                      </div>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 800, color: "var(--white)" }}>{st.title}</div>
                        <div style={{ fontSize: 12.5, lineHeight: 1.45, color: "var(--text-on-dark-muted)", marginTop: 2 }}>{st.desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
                <div style={{ background: "color-mix(in srgb, var(--cream-50) 8%, transparent)", border: "1px solid var(--border-on-dark)", borderRadius: "var(--radius-lg)", padding: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-on-dark-muted)", marginBottom: 10 }}>Ingredient analysis</div>
                  {scanIngredients.map((ing) => (
                    <div key={ing.name} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border-on-dark)" }}>
                      <Icon name={ing.icon} size={16} color={ing.color} />
                      <span style={{ fontSize: 13.5, color: "var(--cream-50)", flex: 1 }}>{ing.name}</span>
                      <span style={{ fontSize: 11.5, fontWeight: 700, color: ing.color }}>{ing.tag}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ============ MOBILE ============ */}
        <section id="mobile" style={{ background: "var(--white)", borderTop: "1px solid var(--border-subtle)" }}>
          <div className="hl-split" style={{ maxWidth: 1200, margin: "0 auto", padding: "96px 32px", display: "grid", gridTemplateColumns: "1fr 0.85fr", gap: 56, alignItems: "center" }}>
            <div data-reveal="">
              <div style={overline}>Mobile Experience</div>
              <h2 style={h2Style}>Halal clarity, in your pocket.</h2>
              <p style={{ margin: "16px 0 0", maxWidth: 500, fontSize: 18, lineHeight: 1.6, color: "var(--text-muted)" }}>Scan, ask and discover on the go. The full intelligence of the platform, designed for the moment you&rsquo;re standing in the aisle.</p>
              <div style={{ marginTop: 28, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, maxWidth: 520 }}>
                {mobileFeatures.map((m) => (
                  <div key={m.label} style={{ display: "flex", alignItems: "center", gap: 12, padding: 14, borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)", background: "var(--cream-50)" }}>
                    <div style={{ flex: "0 0 auto", width: 38, height: 38, borderRadius: 10, background: "color-mix(in srgb, var(--green-800) 8%, transparent)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <Icon name={m.icon} size={19} color="var(--green-800)" />
                    </div>
                    <div>
                      <div style={{ fontSize: 14.5, fontWeight: 800, color: "var(--green-900)" }}>{m.label}</div>
                      <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 1 }}>{m.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div data-reveal="" style={{ justifySelf: "center" }}>
              <div style={{ width: 280, borderRadius: 44, background: "#071f14", padding: 12, boxShadow: "var(--shadow-lg)", border: "1px solid var(--border-subtle)" }}>
                <Image src="/images/halalone-mobile.png" alt="Halal One mobile app" width={256} height={512} style={{ display: "block", width: "100%", height: "auto", borderRadius: 34 }} />
              </div>
            </div>
          </div>
        </section>

        {/* ============ ANALYTICS ============ */}
        <section id="analytics" style={{ background: "var(--cream-50)", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={sectionInner}>
            <div data-reveal="" style={{ maxWidth: 720 }}>
              <div style={overline}>Analytics &amp; Global Coverage</div>
              <h2 style={h2Style}>A living map of the global halal economy.</h2>
            </div>

            <div data-reveal="" style={{ marginTop: 40, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 18 }}>
              {kpis.map((k) => (
                <Card key={k.label}>
                  <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--text-muted)" }}>{k.label}</div>
                  <div style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.03em", color: "var(--green-900)", marginTop: 8, lineHeight: 1 }}>{k.value}</div>
                  <div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--green-700)", marginTop: 8, display: "inline-flex", alignItems: "center", gap: 5 }}>
                    <Icon name="trending-up" size={14} color="var(--green-700)" />{k.delta}
                  </div>
                </Card>
              ))}
            </div>

            <div className="hl-split" data-reveal="" style={{ marginTop: 20, display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20 }}>
              <Card>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ fontSize: 16, fontWeight: 800, color: "var(--green-900)" }}>Repository growth</div>
                  <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)" }}>Verified records · last 12 months</span>
                </div>
                <div style={{ marginTop: 24, height: 190, display: "flex", alignItems: "flex-end", gap: 10 }}>
                  {growthBars.map((b, i) => (
                    <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
                      <div style={{ width: "100%", borderRadius: "6px 6px 0 0", background: "linear-gradient(180deg, var(--green-700), var(--green-800))", height: b.h }} />
                      <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{b.m}</span>
                    </div>
                  ))}
                </div>
              </Card>
              <Card>
                <div style={{ fontSize: 16, fontWeight: 800, color: "var(--green-900)" }}>Coverage by region</div>
                <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 16 }}>
                  {regions.map((rg) => (
                    <div key={rg.name}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontWeight: 700, color: "var(--text-body)", marginBottom: 6 }}><span>{rg.name}</span><span style={{ color: "var(--green-800)" }}>{rg.pct}</span></div>
                      <div style={{ height: 8, borderRadius: 999, background: "var(--green-100)", overflow: "hidden" }}><div style={{ height: "100%", borderRadius: 999, background: "linear-gradient(90deg, var(--green-700), var(--gold-500))", width: rg.pct }} /></div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        </section>

        {/* ============ TRUST ============ */}
        <section id="trust" style={{ background: "var(--white)", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={sectionInner}>
            <div data-reveal="" style={{ maxWidth: 760 }}>
              <div style={overline}>Institutional Trust</div>
              <h2 style={h2Style}>Built with the Islamic Chamber of Commerce &amp; Development.</h2>
              <p style={{ margin: "16px 0 0", fontSize: 18, lineHeight: 1.6, color: "var(--text-muted)" }}>Halal One is developed under ICCD to serve consumers, businesses, certification authorities, governments and OIC institutions — grounded in recognised standards and traceable data.</p>
            </div>
            <div data-reveal="" style={{ marginTop: 40, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 20 }}>
              {trustPillars.map((tp) => (
                <Card key={tp.title} surface="cream">
                  <div style={{ width: 42, height: 42, borderRadius: 11, background: "var(--white)", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Icon name={tp.icon} size={21} color="var(--green-800)" />
                  </div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: "var(--green-900)", marginTop: 14 }}>{tp.title}</div>
                  <p style={{ margin: "6px 0 0", fontSize: 13.5, lineHeight: 1.55, color: "var(--text-muted)" }}>{tp.desc}</p>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* ============ CTA BAND ============ */}
        <section className="hl-on-dark" style={{ background: "var(--green-900)", color: "var(--cream-50)" }}>
          <div style={{ maxWidth: 1000, margin: "0 auto", padding: "84px 32px", textAlign: "center" }}>
            <h2 style={{ margin: 0, fontSize: "clamp(30px, 4vw, 46px)", lineHeight: 1.08, fontWeight: 800, letterSpacing: "-0.025em", color: "var(--white)", textWrap: "balance" }}>Bring verified halal intelligence to your organization.</h2>
            <p style={{ margin: "18px auto 0", maxWidth: 560, fontSize: 18, lineHeight: 1.6, color: "var(--text-on-dark-muted)" }}>For enterprises, certification bodies and institutions ready to build on the world&rsquo;s halal record.</p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "center", marginTop: 30 }}>
              <Button variant="gold" size="lg" href={APP}>Request a demo</Button>
              <Button variant="secondary" size="lg" href="#trust" style={{ color: "var(--cream-50)", borderColor: "var(--border-on-dark)" }}>Contact ICCD</Button>
            </div>
          </div>
        </section>

        {/* ============ FOOTER ============ */}
        <footer className="hl-on-dark" style={{ background: "var(--green-800)", color: "var(--cream-50)" }}>
          <div style={{ maxWidth: 1200, margin: "0 auto", padding: "64px 32px 40px" }}>
            <div className="hl-hero-grid" style={{ display: "grid", gridTemplateColumns: "1.4fr repeat(4, 1fr)", gap: 40 }}>
              <div>
                <Logo size={26} onDark />
                <p style={{ margin: "14px 0 0", maxWidth: 280, fontSize: 13.5, lineHeight: 1.6, color: "var(--text-on-dark-muted)" }}>Your trusted gateway to halal intelligence. One platform. Every halal answer.</p>
                <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
                  {socials.map((so) => (
                    <a key={so} href="#" aria-label={so} style={{ width: 36, height: 36, borderRadius: 10, border: "1px solid var(--border-on-dark)", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
                      <Icon name={so} size={16} color="var(--cream-50)" />
                    </a>
                  ))}
                </div>
              </div>
              {footerCols.map((col) => (
                <div key={col.title} className="hl-fcol">
                  <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--gold-500)", marginBottom: 8 }}>{col.title}</div>
                  {col.links.map((lnk) => {
                    const route = FOOTER_ROUTES[lnk]
                    return route ? <Link key={lnk} href={route}>{lnk}</Link> : <a key={lnk} href="#">{lnk}</a>
                  })}
                </div>
              ))}
            </div>
            <div style={{ marginTop: 48, paddingTop: 24, borderTop: "1px solid var(--border-on-dark)", display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12.5, color: "var(--text-on-dark-muted)" }}>© 2026 Halal One · Islamic Chamber of Commerce &amp; Development. All rights reserved.</span>
              <div style={{ display: "flex", gap: 20 }}>
                <a href="#" style={{ fontSize: 12.5, color: "var(--text-on-dark-muted)" }}>Privacy</a>
                <a href="#" style={{ fontSize: 12.5, color: "var(--text-on-dark-muted)" }}>Terms</a>
                <a href="#" style={{ fontSize: 12.5, color: "var(--text-on-dark-muted)" }}>Accessibility</a>
              </div>
            </div>
          </div>
        </footer>

      </div>
    </div>
  )
}
