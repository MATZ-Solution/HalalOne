import Link from 'next/link'

/**
 * Left-hand brand/marketing panel shared by the login and signup pages.
 * Hidden below the `lg` breakpoint (the form panel goes full-width on mobile).
 * Ported from the HalalOne auth design — deep-green gradient with the gold
 * geometric mark, a pitch, and either sign-in stats or sign-up perks.
 */
type Props = { variant: 'login' | 'signup' }

const perks = [
  'Verified ingredient & certificate lookup',
  'Regulatory alerts across 20+ markets',
  'AI assistant with cited halal rulings',
]

const stats = [
  { value: '20+', label: 'Countries covered' },
  { value: '4', label: 'Intelligence modules' },
  { value: 'AI', label: 'Powered assistant' },
]

export default function BrandPanel({ variant }: Props) {
  const isSignup = variant === 'signup'

  return (
    <aside
      className="hidden lg:flex"
      style={{
        position: 'relative',
        overflow: 'hidden',
        background: 'linear-gradient(160deg,#0F4B2E,#07351F)',
        color: '#FBFAF6',
        flexDirection: 'column',
        padding: '44px 52px',
        minHeight: '100dvh',
      }}
    >
      {/* geometric tile pattern */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg width='64' height='64' viewBox='0 0 64 64' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M32 3L56 32L32 61L8 32Z' fill='none' stroke='rgba(251,250,246,0.05)' stroke-width='1'/%3E%3C/svg%3E\")",
          backgroundSize: '64px',
        }}
      />
      {/* gold radial glow */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: -120,
          right: -120,
          width: 360,
          height: 360,
          borderRadius: '50%',
          background:
            'radial-gradient(circle,color-mix(in srgb,#C9A248 24%,transparent),transparent 70%)',
        }}
      />

      {/* logo */}
      <Link href="/" style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: 11 }}>
        <svg width="34" height="34" viewBox="-16 -16 32 32" aria-hidden="true">
          <path d="M0 -13 L11.3 -6.5 L11.3 6.5 L0 13 L-11.3 6.5 L-11.3 -6.5 Z" fill="none" stroke="#C9A248" strokeWidth="2.6" strokeLinejoin="round" />
          <path d="M-5 0.5 L-1.3 4.6 L5.8 -4.5" fill="none" stroke="#FBFAF6" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.02em', color: '#fff' }}>
          Halal<span style={{ color: '#C9A248' }}>One</span>
        </div>
      </Link>

      {/* pitch */}
      <div style={{ position: 'relative', margin: 'auto 0', padding: '40px 0' }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.14em', textTransform: 'uppercase', color: '#C9A248' }}>
          {isSignup ? 'Get started free' : 'Welcome back'}
        </div>
        <h1 style={{ margin: '16px 0 0', fontSize: 'clamp(28px,3vw,40px)', lineHeight: 1.1, fontWeight: 800, letterSpacing: '-0.025em', color: '#fff', maxWidth: isSignup ? '16ch' : '15ch' }}>
          {isSignup ? 'Join the halal intelligence ecosystem.' : 'Halal clarity, all in one.'}
        </h1>
        <p style={{ margin: '18px 0 0', fontSize: 16, lineHeight: 1.65, color: 'color-mix(in srgb,#FBFAF6 74%,transparent)', maxWidth: '42ch' }}>
          {isSignup
            ? 'Create your account to search verified ingredients, track certifications across 20+ markets, and get instant answers from the AI assistant.'
            : 'Sign in to access regulatory intelligence, the ingredient repository, live alerts, and the AI assistant — one verified halal ecosystem.'}
        </p>

        {isSignup ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 34 }}>
            {perks.map((p) => (
              <div key={p} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ flex: '0 0 auto', width: 26, height: 26, borderRadius: 8, background: 'rgba(201,162,72,.18)', border: '1px solid rgba(201,162,72,.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#C9A248', fontWeight: 800, fontSize: 13 }}>✓</div>
                <div style={{ fontSize: 14.5, color: 'color-mix(in srgb,#FBFAF6 88%,transparent)' }}>{p}</div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ display: 'flex', gap: 28, marginTop: 36, paddingTop: 26, borderTop: '1px solid rgba(251,250,246,.16)' }}>
            {stats.map((s) => (
              <div key={s.label}>
                <div style={{ fontSize: 26, fontWeight: 800, color: '#fff', lineHeight: 1 }}>{s.value}</div>
                <div style={{ fontSize: 12, color: 'color-mix(in srgb,#FBFAF6 60%,transparent)', marginTop: 5 }}>{s.label}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ position: 'relative', fontSize: 12, color: 'color-mix(in srgb,#FBFAF6 52%,transparent)' }}>
        © 2026 HalalOne · ICCD Technology
      </div>
    </aside>
  )
}
