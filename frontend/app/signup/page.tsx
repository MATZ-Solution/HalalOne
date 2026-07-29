'use client'

import { useState, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { createClient } from '@/utils/supabase/client'
import GoogleButton from '@/components/auth/GoogleButton'
import BrandPanel from '@/components/auth/BrandPanel'

// Only same-origin relative paths are honoured as a post-signup destination.
function safePath(next: string | null): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.startsWith('/\\')) return '/'
  return next
}

// Mirrors the design's strength heuristic (0–4).
function passwordStrength(pw: string): number {
  let s = 0
  if (pw.length >= 8) s++
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++
  if (/\d/.test(pw)) s++
  if (/[^A-Za-z0-9]/.test(pw)) s++
  return Math.min(s, 4)
}

const STRENGTH_LABELS = ['Too weak', 'Weak', 'Fair', 'Good', 'Strong']
const STRENGTH_PALETTE = ['#B23A2E', '#B7902F', '#C9A248', '#196B24']

export default function SignupPage() {
  return (
    <Suspense>
      <SignupForm />
    </Suspense>
  )
}

function SignupForm() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [org, setOrg] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [agree, setAgree] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  // After a successful sign-up, Supabase sends a confirmation email.
  const [confirmed, setConfirmed] = useState(false)

  const router = useRouter()
  const searchParams = useSearchParams()
  const supabase = createClient()

  const next = safePath(searchParams?.get('next') ?? null)
  const loginHref = next === '/' ? '/login' : `/login?next=${encodeURIComponent(next)}`

  const strength = password ? passwordStrength(password) : 0
  const strengthColor = strength === 0 ? '#657269' : STRENGTH_PALETTE[Math.max(0, strength - 1)]

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!agree) {
      setError('Please agree to the Terms of Service and Privacy Policy to continue.')
      return
    }
    setLoading(true)
    setError(null)

    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        // Redirect here after the user clicks the confirmation link.
        emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
        // Stored on the Supabase user; the app reads full_name for the profile.
        data: {
          full_name: name,
          ...(org ? { organization: org } : {}),
        },
      },
    })

    if (error) {
      setError(error.message)
      setLoading(false)
    } else {
      // If email confirmations are disabled in Supabase, the user is logged in
      // immediately. Otherwise we show the "check your email" state.
      const { data: { user } } = await supabase.auth.getUser()
      if (user?.confirmed_at) {
        router.push(next)
        router.refresh()
      } else {
        setConfirmed(true)
        setLoading(false)
      }
    }
  }

  const inputCls =
    'w-full px-3.5 py-3 rounded-xl border border-[#D9DED8] bg-white text-sm text-[#07351F] placeholder:text-[#657269] outline-none focus:border-[#196B24] focus:shadow-[0_0_0_3px_rgba(25,107,36,0.16)] transition'

  // ── Email confirmation state ──────────────────────────────────────────────
  if (confirmed) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-[#FBFAF6] px-8 plus-jakarta-sans-400">
        <div className="w-full max-w-[400px] text-center">
          <div className="w-12 h-12 rounded-full bg-white border border-[#D9DED8] flex items-center justify-center mx-auto mb-6">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0F4B2E" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
            </svg>
          </div>
          <h2 className="text-[#07351F] text-xl plus-jakarta-sans-800 mb-2">Check your email</h2>
          <p className="text-[#657269] text-sm mb-8 leading-relaxed">
            We sent a confirmation link to <span className="text-[#07351F] plus-jakarta-sans-700">{email}</span>. Click it to activate your account.
          </p>
          <Link href={loginHref} className="text-[#0F4B2E] text-sm plus-jakarta-sans-700 hover:text-[#B7902F] transition-colors">
            Back to sign in
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-dvh bg-[#FBFAF6] text-[#222] plus-jakarta-sans-400 lg:grid lg:grid-cols-[1.05fr_1fr]">
      <BrandPanel variant="signup" />

      {/* ── Form panel ── */}
      <main className="flex flex-col min-h-dvh px-6 sm:px-10 py-8">
        {/* top-right switch to login */}
        <div className="flex justify-end items-center gap-2.5 text-[13.5px] text-[#657269]">
          Already have an account?
          <Link href={loginHref} className="plus-jakarta-sans-700 px-4 py-2 rounded-full border border-[#D9DED8] text-[#0F4B2E] hover:bg-[#F7F4EC] transition-colors">
            Sign in
          </Link>
        </div>

        <div className="m-auto w-full max-w-[410px] py-5">
          <h2 className="text-[28px] plus-jakarta-sans-800 tracking-tight text-[#07351F]">Create your account</h2>
          <p className="text-sm text-[#657269] mt-2 leading-relaxed">Free to start. No credit card required.</p>

          <div className="mt-6">
            <GoogleButton label="Sign up with Google" next={next} />
          </div>

          <div className="flex items-center gap-3.5 my-5">
            <div className="flex-1 h-px bg-[#D9DED8]" />
            <span className="text-[11.5px] plus-jakarta-sans-700 tracking-wider uppercase text-[#657269]">or</span>
            <div className="flex-1 h-px bg-[#D9DED8]" />
          </div>

          <form onSubmit={handleSignup} className="flex flex-col gap-[15px]">
            <label className="block">
              <span className="block text-[12.5px] plus-jakarta-sans-700 text-[#07351F] mb-1.5">Full name</span>
              <input type="text" required autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Aisha Rahman" className={inputCls} />
            </label>

            <label className="block">
              <span className="block text-[12.5px] plus-jakarta-sans-700 text-[#07351F] mb-1.5">Work email</span>
              <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" className={inputCls} />
            </label>

            <label className="block">
              <span className="block text-[12.5px] plus-jakarta-sans-700 text-[#07351F] mb-1.5">
                Organization <span className="text-[#657269] plus-jakarta-sans-600">(optional)</span>
              </span>
              <input type="text" autoComplete="organization" value={org} onChange={(e) => setOrg(e.target.value)} placeholder="Company or certifier" className={inputCls} />
            </label>

            <label className="block">
              <span className="block text-[12.5px] plus-jakarta-sans-700 text-[#07351F] mb-1.5">Password</span>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className={inputCls.replace('px-3.5', 'pl-3.5 pr-11')}
                />
                <button
                  type="button"
                  onClick={() => setShowPw((s) => !s)}
                  aria-label="Toggle password visibility"
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 p-2 text-xs plus-jakarta-sans-700 text-[#657269] hover:text-[#0F4B2E]"
                >
                  {showPw ? 'Hide' : 'Show'}
                </button>
              </div>
              {/* strength meter */}
              <div className="flex gap-[5px] mt-2.5">
                {[0, 1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="flex-1 h-1 rounded-full transition-colors"
                    style={{ background: i < strength ? strengthColor : '#D9DED8' }}
                  />
                ))}
              </div>
              <div className="text-[11.5px] text-[#657269] mt-1.5">
                Password strength: <span className="plus-jakarta-sans-700" style={{ color: strengthColor }}>{STRENGTH_LABELS[strength]}</span>
              </div>
            </label>

            <label className="flex items-start gap-2.5 cursor-pointer text-[12.5px] text-[#657269] select-none leading-relaxed">
              <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} className="w-4 h-4 mt-0.5 accent-[#0F4B2E] cursor-pointer shrink-0" />
              <span>
                I agree to HalalOne&apos;s{' '}
                <Link href="#" className="plus-jakarta-sans-700 text-[#0F4B2E] hover:text-[#B7902F]">Terms of Service</Link> and{' '}
                <Link href="#" className="plus-jakarta-sans-700 text-[#0F4B2E] hover:text-[#B7902F]">Privacy Policy</Link>.
              </span>
            </label>

            {error && <p className="text-[#B23A2E] text-xs">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="mt-1 w-full py-3.5 rounded-xl bg-[#0F4B2E] text-white plus-jakarta-sans-800 text-[15px] tracking-tight shadow-[0_10px_28px_rgba(7,53,31,0.12)] hover:bg-[#07351F] hover:-translate-y-px active:translate-y-0 transition disabled:opacity-60 disabled:hover:translate-y-0"
            >
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>
        </div>

        <div className="flex items-center gap-2 text-xs text-[#657269] justify-center">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 2 4 5v6c0 5 3.4 8.5 8 11 4.6-2.5 8-6 8-11V5l-8-3Z" stroke="#196B24" strokeWidth="2" strokeLinejoin="round" />
          </svg>
          Your data is encrypted and never shared
        </div>
      </main>
    </div>
  )
}
