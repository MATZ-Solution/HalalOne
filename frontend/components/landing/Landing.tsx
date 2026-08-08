"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"

import { createClient } from "@/utils/supabase/client"

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

// The directory / regulatory-intelligence routes.
const CERT_DIR = "/directory/certification-authority-directory"
const REG_INTEL = "/directory/regulatory-intelligence"
const BIZ_DIR = "/directory/business-directory"
const NEWS = "/directory/news-alerts"
const STANDARDS = "/directory/standards-library"
const TRADE = "/directory/trade-intelligence"
const INGREDIENTS = "/directory/ingredient-database"
const MARKET = "/directory/market-intelligence"

// Shared nav links (desktop bar + mobile hamburger overlay use the same list).
const NAV_LINKS: { label: string; href: string }[] = [
  { label: "Directory", href: CERT_DIR },
  { label: "Business", href: BIZ_DIR },
  { label: "Ingredients", href: INGREDIENTS },
  { label: "Regulatory", href: REG_INTEL },
  { label: "Standards", href: STANDARDS },
  { label: "Market", href: MARKET },
  { label: "Trade", href: TRADE },
  { label: "News", href: NEWS },
]

// Real destinations for footer link labels; anything unmapped stays a "#" stub.
const FOOTER_ROUTES: Record<string, string> = {
  "AI Assistant": APP,
  "Repository": CERT_DIR,
  "OCR Scanner": APP,
  "Standards": STANDARDS,
  "Certification lookup": CERT_DIR,
  "Business Directory": BIZ_DIR,
  "News & alerts": NEWS,
  "Market intelligence": MARKET,
  "Ingredient database": INGREDIENTS,
  "Knowledge graph": INGREDIENTS,
}

const overline = { fontSize: 11, fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase" as const, color: "var(--gold-600)" }
const h2Style = { margin: "14px 0 0", fontSize: "clamp(30px, 3.6vw, 44px)", lineHeight: 1.1, fontWeight: 800, letterSpacing: "-0.022em", color: "var(--text-heading)" }
const sectionInner = { maxWidth: 1200, margin: "0 auto", padding: "96px 32px" }

type BadgeVariant = "verified" | "warning" | "danger"

// Halal-status tag styling for the product cards — mirrors the chat app's
// statusStyle (Halal / Haram / Mushbooh / Unknown), normalized so spelling
// variants like "haraam"/"halaal" map to the same tag.
const productStatusStyle = (raw: string) => {
  const s = (raw ?? "").toLowerCase().replace(/(.)\1+/g, "$1")
  if (s.includes("halal")) return { label: "Halal", rail: "var(--green-700)", fg: "var(--green-700)", dot: "var(--green-700)", bg: "color-mix(in srgb, var(--green-700) 12%, transparent)", border: "color-mix(in srgb, var(--green-700) 30%, transparent)" }
  if (s.includes("haram")) return { label: "Haram", rail: "var(--status-danger)", fg: "var(--status-danger)", dot: "var(--status-danger)", bg: "color-mix(in srgb, var(--status-danger) 12%, transparent)", border: "color-mix(in srgb, var(--status-danger) 30%, transparent)" }
  if (s.includes("mushbo") || s.includes("doubt") || s.includes("depend")) return { label: "Mushbooh", rail: "var(--gold-500)", fg: "var(--gold-600)", dot: "var(--gold-500)", bg: "color-mix(in srgb, var(--gold-500) 16%, transparent)", border: "color-mix(in srgb, var(--gold-500) 40%, transparent)" }
  return { label: "Unknown", rail: "var(--text-muted)", fg: "var(--text-muted)", dot: "var(--text-muted)", bg: "color-mix(in srgb, var(--text-muted) 12%, transparent)", border: "color-mix(in srgb, var(--text-muted) 30%, transparent)" }
}

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

  // Profile dropdown (sign in → the avatar opens a menu instead of navigating).
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Mobile nav overlay (hamburger), shown when the desktop nav bar is hidden.
  const [navOpen, setNavOpen] = useState(false)
  useEffect(() => {
    if (!navOpen) return
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setNavOpen(false) }
    window.addEventListener("keydown", onKey)
    return () => { document.body.style.overflow = prev; window.removeEventListener("keydown", onKey) }
  }, [navOpen])

  useEffect(() => {
    if (!menuOpen) return
    const onDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setMenuOpen(false) }
    document.addEventListener("mousedown", onDown)
    document.addEventListener("keydown", onKey)
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey) }
  }, [menuOpen])

  const handleSignOut = async () => {
    setMenuOpen(false)
    await createClient().auth.signOut()
    router.refresh()   // re-runs the server page → nav flips back to signed-out
  }

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
          <nav style={{ maxWidth: 1200, margin: "0 auto", height: 68, padding: "0 32px", display: "flex", justifyContent:'center', alignItems: "center", gap: 20 }}>
            <a href="#top" style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Logo size={28} />
            </a>
            <div className="hl-navcenter" style={{ display: "flex", alignItems: "center", gap: 2, marginLeft: 18 }}>
              <Link className="hl-navlink" href={CERT_DIR}>Directory</Link>
              <Link className="hl-navlink" href={BIZ_DIR}>Business</Link>
              <Link className="hl-navlink" href={INGREDIENTS}>Ingredients</Link>
              <Link className="hl-navlink" href={REG_INTEL}>Regulatory</Link>
              <Link className="hl-navlink" href={STANDARDS}>Standards</Link>
              <Link className="hl-navlink" href={MARKET}>Market</Link>
              <Link className="hl-navlink" href={TRADE}>Trade</Link>
              <Link className="hl-navlink" href={NEWS}>News</Link>
            </div>
            <div className="hl-nav-actions" style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
              <button
                type="button"
                className="hl-navburger"
                aria-label="Open menu"
                aria-expanded={navOpen}
                onClick={() => setNavOpen(true)}
                style={{ alignItems: "center", justifyContent: "center", width: 40, height: 40, borderRadius: 10, border: "1px solid var(--border-subtle)", background: "var(--white)", cursor: "pointer", color: "var(--green-900)" }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
              </button>
              {profile ? (
                <>
                  <div ref={menuRef} style={{ position: "relative" }}>
                    <button
                      type="button"
                      onClick={() => setMenuOpen((o) => !o)}
                      aria-haspopup="menu"
                      aria-expanded={menuOpen}
                      aria-label="Account menu"
                      style={{ display: "inline-flex", alignItems: "center", gap: 9, background: "transparent", border: "none", cursor: "pointer", padding: 0 }}
                    >
                      {profile.avatarUrl ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={profile.avatarUrl} alt="" referrerPolicy="no-referrer" style={{ width: 34, height: 34, borderRadius: "50%", objectFit: "cover", border: "1px solid var(--border-subtle)", flex: "0 0 auto" }} />
                      ) : (
                        <span style={{ width: 34, height: 34, borderRadius: "50%", background: "var(--green-800)", color: "var(--white)", display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 14, flex: "0 0 auto" }}>{(profile.name || "U").charAt(0).toUpperCase()}</span>
                      )}
                      <span className="hl-hide-sm" style={{ fontSize: 14, fontWeight: 700, color: "var(--green-900)", letterSpacing: "-0.01em" }}>{firstName}</span>
                      <svg className="hl-hide-sm" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ transition: "transform .15s ease", transform: menuOpen ? "rotate(180deg)" : "none" }}><path d="M6 9l6 6 6-6" stroke="var(--charcoal-600)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    </button>

                    {menuOpen && (
                      <div role="menu" style={{ position: "absolute", top: "calc(100% + 8px)", right: 0, minWidth: 220, background: "var(--white)", border: "1px solid var(--border-subtle)", borderRadius: 12, boxShadow: "var(--shadow-md)", overflow: "hidden", zIndex: 60 }}>
                        <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border-subtle)" }}>
                          <div style={{ fontSize: 13.5, fontWeight: 700, color: "var(--green-900)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{profile.name || "User"}</div>
                          <div style={{ fontSize: 12, color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{profile.email}</div>
                        </div>
                        <Link href={APP} role="menuitem" onClick={() => setMenuOpen(false)} style={{ display: "flex", alignItems: "center", gap: 9, padding: "10px 14px", fontSize: 14, fontWeight: 600, color: "var(--green-900)" }}>
                          <Icon name="sparkles" size={16} color="var(--green-800)" />Open chat
                        </Link>
                        <button type="button" role="menuitem" onClick={handleSignOut} style={{ width: "100%", display: "flex", alignItems: "center", gap: 9, padding: "10px 14px", fontSize: 14, fontWeight: 600, color: "var(--status-danger)", background: "transparent", border: "none", borderTop: "1px solid var(--border-subtle)", cursor: "pointer", textAlign: "left" }}>
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                          Sign out
                        </button>
                      </div>
                    )}
                  </div>
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

        {/* ============ MOBILE NAV OVERLAY ============ */}
        <AnimatePresence>
          {navOpen && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}
              style={{ position: "fixed", inset: 0, zIndex: 100, background: "var(--cream-50)", display: "flex", flexDirection: "column" }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: 68, padding: "0 24px", borderBottom: "1px solid var(--border-subtle)" }}>
                <Logo size={26} />
                <button type="button" aria-label="Close menu" onClick={() => setNavOpen(false)} style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 40, height: 40, borderRadius: 10, border: "1px solid var(--border-subtle)", background: "var(--white)", cursor: "pointer", color: "var(--green-900)" }}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
                </button>
              </div>
              <nav style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
                {NAV_LINKS.map((l) => (
                  <Link key={l.href} href={l.href} onClick={() => setNavOpen(false)} style={{ padding: "18px 24px", fontSize: 20, fontWeight: 700, letterSpacing: "-0.01em", color: "var(--green-900)", borderBottom: "1px solid var(--border-subtle)" }}>
                    {l.label}
                  </Link>
                ))}
                {!profile && (
                  <Link href="/login" onClick={() => setNavOpen(false)} style={{ padding: "18px 24px", fontSize: 20, fontWeight: 700, letterSpacing: "-0.01em", color: "var(--green-900)", borderBottom: "1px solid var(--border-subtle)" }}>
                    Sign in
                  </Link>
                )}
              </nav>
              <div style={{ padding: 24, borderTop: "1px solid var(--border-subtle)" }}>
                {profile ? (
                  <Button size="lg" block href={APP}>Start Chat</Button>
                ) : (
                  <Button size="lg" block href={START}>Get started</Button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ============ HERO ============ */}
        <section id="top" className="hl-on-dark" style={{ position: "relative", background: "radial-gradient(120% 120% at 80% -10%, #12583a 0%, var(--green-800) 42%, var(--green-900) 100%)", color: "var(--cream-50)", overflow: "hidden" }}>
          <div aria-hidden="true" style={{ position: "absolute", inset: 0, backgroundImage: "radial-gradient(color-mix(in srgb, var(--cream-50) 6%, transparent) 1px, transparent 1px)", backgroundSize: "26px 26px", opacity: 0.5 }} />
          <div aria-hidden="true" style={{ position: "absolute", top: -140, right: -120, width: 520, height: 520, borderRadius: "var(--radius-pill)", background: "radial-gradient(circle, color-mix(in srgb, var(--gold-500) 22%, transparent) 0%, transparent 68%)" }} />
          <div className="hl-hero-grid" style={{ position: "relative", maxWidth: 1200, margin: "0 auto", padding: "84px 32px 76px", display: "grid", gridTemplateColumns: "1.05fr 0.95fr", gap: 56, alignItems: "center" }}>
            <div>
              <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "7px 16px", borderRadius: "var(--radius-pill)", border: "1px solid transparent", background: "var(--gold-500)", fontSize: 11, fontWeight: 800, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--green-900)", boxShadow: "var(--shadow-sm)" }}>
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

            {/* OCR scanner phone mockup (relocated from the scanner section) */}
            <div style={{ position: "relative", display: "flex", justifyContent: "center" }}>
              <div aria-hidden="true" style={{ position: "absolute", inset: -18, borderRadius: 32, background: "radial-gradient(circle at 30% 0%, color-mix(in srgb, var(--gold-500) 16%, transparent), transparent 70%)" }} />
              <div style={{ position: "relative", width: 260, height: 520, borderRadius: 42, background: "#071f14", padding: 12, boxShadow: "0 40px 90px rgba(0,0,0,.5)", border: "1px solid color-mix(in srgb, var(--cream-50) 16%, transparent)" }}>
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
                  <span style={{ marginLeft: "auto", fontSize: 12, fontWeight: 700, color: "var(--text-muted)" }}>Grounded in 200K+ verified records</span>
                </div>
                <div style={{ padding: 22, display: "flex", flexDirection: "column", gap: 22, background: "var(--cream-50)" }}>
                  {/* user bubble — same as the chat page */}
                  <div style={{ alignSelf: "flex-end", maxWidth: "80%", background: "color-mix(in srgb, var(--green-700) 9%, transparent)", border: "1px solid color-mix(in srgb, var(--green-700) 20%, transparent)", color: "var(--green-900)", borderRadius: "16px 16px 4px 16px", padding: "12px 16px", fontSize: 14.5, lineHeight: 1.55 }}>
                    I am so confused about the halal status of additive E471, is it actually HALAL?
                  </div>

                  {/* assistant — avatar + reply + product card, same as the chat page */}
                  <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                    <div style={{ flex: "0 0 auto", width: 32, height: 32, borderRadius: 9, background: "linear-gradient(150deg,#0F4B2E,#07351F)", display: "flex", alignItems: "center", justifyContent: "center", marginTop: 2 }}>
                      <svg width="18" height="18" viewBox="-16 -16 32 32" aria-hidden="true"><path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke="var(--gold-500)" strokeWidth="2.8" strokeLinejoin="round" /><path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke="var(--cream-50)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.65, color: "var(--text-body)" }}>
                        Great question — E471 is a common source of confusion. <strong>E471 (mono&#8209; and diglycerides of fatty acids)</strong> is listed as <strong>Halal</strong> in our repository, but it&rsquo;s origin&#8209;dependent: <strong>halal</strong> when derived from plant fat, and <strong>haraam</strong> when derived from pork fat. If the source isn&rsquo;t stated it&rsquo;s treated as mushbooh (doubtful), so confirm the origin with the manufacturer. Here&rsquo;s the record:
                      </p>

                      {/* product card — identical to the chat page ProductCard */}
                      <div style={{ marginTop: 14, background: "var(--white)", border: "1px solid var(--border-subtle)", borderLeftWidth: 4, borderLeftColor: "var(--green-700)", borderRadius: 14, padding: "16px 18px", boxShadow: "var(--shadow-sm)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 14 }}>
                          <div style={{ fontSize: 15, fontWeight: 800, color: "var(--green-900)", lineHeight: 1.3, textTransform: "capitalize" }}>e471 mono-and diglycerides of fatty acids</div>
                          <span style={{ flex: "0 0 auto", display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 11px", borderRadius: 999, fontSize: 10.5, fontWeight: 800, background: "color-mix(in srgb, var(--green-700) 12%, transparent)", color: "var(--green-700)", border: "1px solid color-mix(in srgb, var(--green-700) 30%, transparent)" }}>
                            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--green-700)" }} />Halal
                          </span>
                        </div>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
                          {["Additive", "Preservative"].map((c) => (
                            <span key={c} style={{ padding: "3px 10px", borderRadius: 8, fontSize: 10.5, fontWeight: 700, background: "var(--cream-100)", color: "var(--text-muted)", border: "1px solid var(--border-subtle)" }}>{c}</span>
                          ))}
                        </div>
                        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6, marginTop: 10 }}>
                          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Certified by</span>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--green-700)", background: "color-mix(in srgb, var(--green-700) 8%, transparent)", border: "1px solid color-mix(in srgb, var(--green-700) 22%, transparent)", padding: "2px 9px", borderRadius: 7 }}>HFCI India</span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--cream-100)", fontSize: 11, fontWeight: 700, color: "var(--green-700)" }}>
                          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" /></svg>
                          Verified · Sourced from database
                        </div>
                        </div>
                    </div>
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
                <h2 style={h2Style}>Every product, with complete details.</h2>
              </div>
              <p style={{ maxWidth: 340, fontSize: 15, lineHeight: 1.6, color: "var(--text-muted)" }}>Halal status, category, companies and certifying authority — every result on a single verified card.</p>
            </div>

            <div data-reveal="" style={{ marginTop: 40, display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 20 }}>
              {products.map((p) => {
                const st = productStatusStyle(p.halal_status)
                const cats = [p.category_l1, p.category_l2].filter(Boolean)
                return (
                  <div
                    key={p.norm_name}
                    className="hl-chip"
                    style={{ background: "var(--white)", border: "1px solid var(--border-subtle)", borderLeftWidth: 4, borderLeftColor: st.rail, borderRadius: 14, padding: "16px 18px", boxShadow: "var(--shadow-sm)", cursor: "pointer" }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 14 }}>
                      <div style={{ fontSize: 15, fontWeight: 800, color: "var(--green-900)", lineHeight: 1.3, textTransform: "capitalize" }}>{p.norm_name}</div>
                      <span style={{ flex: "0 0 auto", display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 11px", borderRadius: 999, fontSize: 10.5, fontWeight: 800, background: st.bg, color: st.fg, border: `1px solid ${st.border}` }}>
                        <span style={{ width: 7, height: 7, borderRadius: "50%", background: st.dot }} />{st.label}
                      </span>
                    </div>
                    {cats.length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
                        {cats.map((c) => (
                          <span key={c} style={{ padding: "3px 10px", borderRadius: 8, fontSize: 10.5, fontWeight: 700, background: "var(--cream-100)", color: "var(--text-muted)", border: "1px solid var(--border-subtle)" }}>{c}</span>
                        ))}
                      </div>
                    )}
                    {p.companies.length > 0 && (
                      <div style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 10, lineHeight: 1.5 }}>
                        {p.companies.map((c) => c.charAt(0).toUpperCase() + c.slice(1)).join(" · ")}
                      </div>
                    )}
                    {p.cert_bodies.length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6, marginTop: 10 }}>
                        <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Certified by</span>
                        {p.cert_bodies.map((b) => (
                          <span key={b} style={{ fontSize: 11, fontWeight: 700, color: "var(--green-700)", background: "color-mix(in srgb, var(--green-700) 8%, transparent)", border: "1px solid color-mix(in srgb, var(--green-700) 22%, transparent)", padding: "2px 9px", borderRadius: 7 }}>{b}</span>
                        ))}
                      </div>
                    )}
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--cream-100)", fontSize: 11, fontWeight: 700, color: "var(--green-700)" }}>
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" /></svg>
                      Verified &middot; Sourced from database
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        {/* ============ REPOSITORY ============ */}
        <section id="repository" style={{ background: "var(--cream-50)", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={sectionInner}>
            <div data-reveal="" style={{ maxWidth: 720 }}>
              <div style={overline}>Global Repository</div>
              <h2 style={h2Style}>Search the world&rsquo;s halal record.</h2>
              <p style={{ margin: "16px 0 0", fontSize: 18, lineHeight: 1.6, color: "var(--text-muted)" }}>Hundreds of thousands of products, ingredients, manufacturers and certificates — filterable by authority, country and category.</p>
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
          <div className="hl-split" style={{ position: "relative", maxWidth: 1200, margin: "0 auto", padding: "96px 32px" }}>
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
          <div className="hl-split" style={{ maxWidth: 1200, margin: "0 auto", padding: "96px 32px", display: "grid", gridTemplateColumns: "1fr 0.85fr", gap: 56, alignItems: "stretch" }}>
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
            <div data-reveal="" style={{ alignSelf: "stretch", display: "flex", alignItems: "center", justifyContent: "center" }}>
              {/* CSS phone mockup — crisp at any size, mirrors the chat app UI */}
              <div style={{ position: "relative", width: 288, height: 588, borderRadius: 46, background: "#071f14", padding: 12, boxShadow: "var(--shadow-lg)", border: "1px solid color-mix(in srgb, var(--cream-50) 14%, transparent)" }}>
                <div style={{ position: "relative", width: "100%", height: "100%", borderRadius: 36, overflow: "hidden", background: "var(--cream-50)", display: "flex", flexDirection: "column" }}>
                  {/* notch */}
                  <div style={{ position: "absolute", top: 10, left: "50%", transform: "translateX(-50%)", width: 92, height: 20, borderRadius: 999, background: "#050f0a", zIndex: 2 }} />
                  {/* top bar */}
                  <div style={{ display: "flex", alignItems: "center", gap: 7, padding: "28px 16px 12px", borderBottom: "1px solid var(--border-subtle)" }}>
                    <svg width="16" height="16" viewBox="-16 -16 32 32" aria-hidden="true"><path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke="var(--gold-500)" strokeWidth="2.8" strokeLinejoin="round" /><path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke="var(--green-800)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--green-900)" }}>Halal<span style={{ color: "var(--gold-600)" }}>One</span></div>
                  </div>
                  {/* conversation */}
                  <div style={{ flex: 1, overflow: "hidden", padding: "14px 14px 0", display: "flex", flexDirection: "column", gap: 14 }}>
                    <div style={{ alignSelf: "flex-end", maxWidth: "82%", background: "color-mix(in srgb, var(--green-700) 9%, transparent)", border: "1px solid color-mix(in srgb, var(--green-700) 20%, transparent)", color: "var(--green-900)", borderRadius: "14px 14px 4px 14px", padding: "9px 12px", fontSize: 12.5, lineHeight: 1.5 }}>Is Oreo halal?</div>
                    <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                      <div style={{ flex: "0 0 auto", width: 24, height: 24, borderRadius: 7, background: "linear-gradient(150deg,#0F4B2E,#07351F)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <svg width="13" height="13" viewBox="-16 -16 32 32" aria-hidden="true"><path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke="var(--gold-500)" strokeWidth="2.8" strokeLinejoin="round" /><path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke="var(--cream-50)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.55, color: "var(--ink, #222)" }}>Generally yes — Oreo Original is certified halal in several markets.</p>
                        <div style={{ marginTop: 10, background: "var(--white)", border: "1px solid var(--border-subtle)", borderLeftWidth: 3, borderLeftColor: "var(--green-700)", borderRadius: 11, padding: "11px 12px", boxShadow: "var(--shadow-sm)" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                            <div style={{ fontSize: 12.5, fontWeight: 800, color: "var(--green-900)", lineHeight: 1.25 }}>Oreo Original Cookies</div>
                            <span style={{ flex: "0 0 auto", display: "inline-flex", alignItems: "center", gap: 4, padding: "3px 8px", borderRadius: 999, fontSize: 9, fontWeight: 800, background: "color-mix(in srgb, var(--green-700) 12%, transparent)", color: "var(--green-700)", border: "1px solid color-mix(in srgb, var(--green-700) 30%, transparent)" }}><span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--green-700)" }} />Halal</span>
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 8 }}>
                            <span style={{ padding: "2px 8px", borderRadius: 6, fontSize: 9, fontWeight: 700, background: "var(--cream-100)", color: "var(--text-muted)", border: "1px solid var(--border-subtle)" }}>Food</span>
                            <span style={{ padding: "2px 8px", borderRadius: 6, fontSize: 9, fontWeight: 700, background: "var(--cream-100)", color: "var(--text-muted)", border: "1px solid var(--border-subtle)" }}>Biscuits</span>
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 9, paddingTop: 9, borderTop: "1px solid var(--cream-100)", fontSize: 9, fontWeight: 700, color: "var(--green-700)" }}>
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" /></svg>
                            Verified &middot; Sourced from database
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  {/* composer */}
                  <div style={{ padding: 12 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, background: "var(--white)", border: "1px solid var(--border-subtle)", borderRadius: 999, padding: "6px 6px 6px 14px", boxShadow: "var(--shadow-sm)" }}>
                      <span style={{ flex: 1, fontSize: 11.5, color: "var(--text-muted)" }}>Ask about any product…</span>
                      <span style={{ flex: "0 0 auto", width: 28, height: 28, borderRadius: "50%", background: "var(--green-700)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 20V5M6 11l6-6 6 6" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                      </span>
                    </div>
                  </div>
                </div>
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
