'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { createClient } from '@/utils/supabase/client'
import GoogleButton from '@/components/auth/GoogleButton'

// Unsplash photo: halal grilled meat / kebab spread (no people)
const BG_IMAGE = 'https://images.unsplash.com/photo-1547592166-23ac45744acd?w=1400&q=80&auto=format&fit=crop'

export default function SignupPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  // After a successful sign-up, Supabase sends a confirmation email.
  const [confirmed, setConfirmed] = useState(false)

  const router = useRouter()
  const supabase = createClient()

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        // Redirect here after the user clicks the confirmation link.
        emailRedirectTo: `${window.location.origin}/auth/callback`,
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
        router.push('/')
        router.refresh()
      } else {
        setConfirmed(true)
        setLoading(false)
      }
    }
  }

  // ── Email confirmation state ────────────────────────────────────────────────
  if (confirmed) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0c0c0c] px-8">
        <div className="w-full max-w-[360px] text-center">
          <div className="w-12 h-12 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-6">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-white/60">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
            </svg>
          </div>
          <h2 className="text-white text-xl manrope-600 mb-2">Check your email</h2>
          <p className="text-white/40 text-sm manrope-400 mb-8 leading-relaxed">
            We sent a confirmation link to{' '}
            <span className="text-white/60">{email}</span>. Click it to activate your account.
          </p>
          <Link href="/login" className="text-white/50 text-sm hover:text-white transition-colors">
            Back to sign in
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex bg-[#0c0c0c]">

      {/* ── Left: form panel ── */}
      <div className="flex-1 flex flex-col justify-center items-center px-8 py-12">
        <div className="w-full max-w-[360px]">

          {/* Brand */}
          <div className="mb-10">
            <span className="text-white font-semibold text-xl tracking-tight manrope-600">
              Halalify
            </span>
          </div>

          <h1 className="text-white text-2xl manrope-600 mb-1">Create an account</h1>
          <p className="text-white/40 text-sm manrope-400 mb-8">Start checking halal status today</p>

          <form onSubmit={handleSignup} className="space-y-3">
            <input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm placeholder:text-white/25 outline-none focus:border-white/30 transition-colors"
            />
            <input
              type="password"
              placeholder="Password (min. 6 characters)"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete="new-password"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm placeholder:text-white/25 outline-none focus:border-white/30 transition-colors"
            />

            {error && (
              <p className="text-red-400 text-xs pt-1">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-white text-black rounded-xl px-4 py-3 text-sm manrope-500 hover:bg-white/90 active:bg-white/80 transition-colors disabled:opacity-50 mt-1"
            >
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-white/8" />
            <span className="text-white/25 text-xs">or</span>
            <div className="flex-1 h-px bg-white/8" />
          </div>

          <GoogleButton label="Sign up with Google" />

          <p className="text-center text-white/35 text-sm mt-8">
            Already have an account?{' '}
            <Link href="/login" className="text-white/70 hover:text-white transition-colors underline underline-offset-2">
              Sign in
            </Link>
          </p>
        </div>
      </div>

      {/* ── Right: decorative image (hidden on small screens) ── */}
      <div className="hidden lg:block w-[52%] relative overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={BG_IMAGE}
          alt=""
          aria-hidden="true"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-linear-to-r from-[#0c0c0c] via-transparent to-transparent" />
        <div className="absolute inset-0 bg-black/25" />

        <div className="absolute bottom-12 left-10 right-10">
          <p className="text-white/80 text-lg manrope-500 leading-snug">
            Your halal guide, always in reach.<br />
            <span className="text-white/50 text-sm manrope-400">Certified products from around the world.</span>
          </p>
        </div>
      </div>

    </div>
  )
}
