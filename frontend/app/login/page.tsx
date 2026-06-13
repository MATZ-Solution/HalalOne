'use client'

import { useState, useEffect, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { createClient } from '@/utils/supabase/client'
import GoogleButton from '@/components/auth/GoogleButton'

// Unsplash photo: colorful spice market (no people)
const BG_IMAGE = 'https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=1400&q=80&auto=format&fit=crop'

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
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const router = useRouter()
  const searchParams = useSearchParams()
  const supabase = createClient()

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
      router.push('/')
      router.refresh()
    }
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

          <h1 className="text-white text-2xl manrope-600 mb-1">Welcome back</h1>
          <p className="text-white/40 text-sm manrope-400 mb-8">Sign in to continue</p>

          <form onSubmit={handleLogin} className="space-y-3">
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
              placeholder="Password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              autoComplete="current-password"
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
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-white/8" />
            <span className="text-white/25 text-xs">or</span>
            <div className="flex-1 h-px bg-white/8" />
          </div>

          <GoogleButton />

          <p className="text-center text-white/35 text-sm mt-8">
            {"Don't have an account? "}
            <Link href="/signup" className="text-white/70 hover:text-white transition-colors underline underline-offset-2">
              Sign up
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
        {/* Gradient overlay blending into the form panel */}
        <div className="absolute inset-0 bg-linear-to-r from-[#0c0c0c] via-transparent to-transparent" />
        <div className="absolute inset-0 bg-black/25" />

        {/* Quote overlay */}
        <div className="absolute bottom-12 left-10 right-10">
          <p className="text-white/80 text-lg manrope-500 leading-snug">
            Know what's in your food.<br />
            <span className="text-white/50 text-sm manrope-400">Search 200,000+ halal-certified products.</span>
          </p>
        </div>
      </div>

    </div>
  )
}
