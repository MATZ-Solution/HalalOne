'use client'

import { useState, useEffect, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { createClient } from '@/utils/supabase/client'
import GoogleButton from '@/components/auth/GoogleButton'
import BrandPanel from '@/components/auth/BrandPanel'

// Only same-origin relative paths are honoured as a post-login destination,
// so a crafted ?next= can't turn this into an open redirect.
function safePath(next: string | null): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.startsWith('/\\')) return '/'
  return next
}

// Suspense wrapper required because useSearchParams() opts out of static rendering.
export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  )
}

function LoginForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [remember, setRemember] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const router = useRouter()
  const searchParams = useSearchParams()
  const supabase = createClient()

  // ?next=/chat when arriving via the landing "Get started" CTA; absent for a
  // plain sign-in, which then returns to the landing page.
  const next = safePath(searchParams?.get('next') ?? null)
  const signupHref = next === '/' ? '/signup' : `/signup?next=${encodeURIComponent(next)}`

  // Show a message if redirected here after a failed OAuth callback.
  useEffect(() => {
    if (searchParams?.get('error') === 'auth_callback_error') {
      setError('Authentication failed. Please try again.')
    }
  }, [searchParams])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const { error } = await supabase.auth.signInWithPassword({ email, password })

    if (error) {
      setError(error.message)
      setLoading(false)
    } else {
      // refresh() re-runs server components so the proxy sees the new session.
      router.push(next)
      router.refresh()
    }
  }

  const inputCls =
    'w-full px-3.5 py-3 rounded-xl border border-[#D9DED8] bg-white text-sm text-[#07351F] placeholder:text-[#657269] outline-none focus:border-[#196B24] focus:shadow-[0_0_0_3px_rgba(25,107,36,0.16)] transition'

  return (
    <div className="min-h-dvh bg-[#FBFAF6] text-[#222] plus-jakarta-sans-400 lg:grid lg:grid-cols-[1.05fr_1fr]">
      <BrandPanel variant="login" />

      {/* ── Form panel ── */}
      <main className="flex flex-col min-h-dvh px-6 sm:px-10 py-8">
        {/* top-right switch to signup */}
        <div className="flex justify-end items-center gap-2.5 text-[13.5px] text-[#657269]">
          New to HalalOne?
          <Link href={signupHref} className="plus-jakarta-sans-700 px-4 py-2 rounded-full border border-[#D9DED8] text-[#0F4B2E] hover:bg-[#F7F4EC] transition-colors">
            Create account
          </Link>
        </div>

        <div className="m-auto w-full max-w-[400px] py-6">
          <h2 className="text-[28px] plus-jakarta-sans-800 tracking-tight text-[#07351F]">Sign in to your account</h2>
          <p className="text-sm text-[#657269] mt-2 leading-relaxed">Enter your credentials to continue to the platform.</p>

          {/* SSO */}
          <div className="mt-6">
            <GoogleButton next={next} />
          </div>

          <div className="flex items-center gap-3.5 my-5">
            <div className="flex-1 h-px bg-[#D9DED8]" />
            <span className="text-[11.5px] plus-jakarta-sans-700 tracking-wider uppercase text-[#657269]">or</span>
            <div className="flex-1 h-px bg-[#D9DED8]" />
          </div>

          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            <label className="block">
              <span className="block text-[12.5px] plus-jakarta-sans-700 text-[#07351F] mb-1.5">Email address</span>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className={inputCls}
              />
            </label>

            <label className="block">
              <div className="flex justify-between items-baseline mb-1.5">
                <span className="text-[12.5px] plus-jakarta-sans-700 text-[#07351F]">Password</span>
                <Link href="#" className="text-xs plus-jakarta-sans-700 text-[#0F4B2E] hover:text-[#B7902F] transition-colors">Forgot password?</Link>
              </div>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
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
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer text-[13px] text-[#657269] select-none">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                className="w-4 h-4 accent-[#0F4B2E] cursor-pointer"
              />
              Keep me signed in for 30 days
            </label>

            {error && <p className="text-[#B23A2E] text-xs">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="mt-1 w-full py-3.5 rounded-xl bg-[#0F4B2E] text-white plus-jakarta-sans-800 text-[15px] tracking-tight shadow-[0_10px_28px_rgba(7,53,31,0.12)] hover:bg-[#07351F] hover:-translate-y-px active:translate-y-0 transition disabled:opacity-60 disabled:hover:translate-y-0"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="text-[12.5px] text-[#657269] text-center mt-5 leading-relaxed">
            By continuing you agree to HalalOne&apos;s{' '}
            <Link href="#" className="plus-jakarta-sans-700 text-[#0F4B2E] hover:text-[#B7902F]">Terms</Link> and{' '}
            <Link href="#" className="plus-jakarta-sans-700 text-[#0F4B2E] hover:text-[#B7902F]">Privacy Policy</Link>.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-[#657269] justify-center">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 2 4 5v6c0 5 3.4 8.5 8 11 4.6-2.5 8-6 8-11V5l-8-3Z" stroke="#196B24" strokeWidth="2" strokeLinejoin="round" />
          </svg>
          Protected by enterprise-grade encryption
        </div>
      </main>
    </div>
  )
}
