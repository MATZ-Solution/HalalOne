'use client'

import { createClient } from '@/utils/supabase/client'

type Props = {
  label?: string
  // Where to land after the OAuth round-trip completes. Forwarded to the
  // /auth/callback handler as ?next= so the "Get started" flow returns to /chat
  // while a plain sign-in returns to the landing page.
  next?: string
}

/**
 * Triggers Google OAuth sign-in using the PKCE flow, styled to the HalalOne
 * auth design (light card button). @supabase/ssr generates and stores the PKCE
 * code verifier in a cookie before redirecting to Google.
 */
export default function GoogleButton({ label = 'Continue with Google', next = '/' }: Props) {
  const supabase = createClient()

  const handleGoogleSignIn = async () => {
    const callback = `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      // After Google authenticates, it redirects here to complete PKCE exchange.
      options: { redirectTo: callback },
    })
  }

  return (
    <button
      type="button"
      onClick={handleGoogleSignIn}
      className="flex items-center justify-center gap-2.5 w-full py-3 rounded-xl border border-[#D9DED8] bg-white cursor-pointer plus-jakarta-sans-700 text-sm text-[#222] hover:bg-[#F7F4EC] transition-colors"
    >
      <svg width="17" height="17" viewBox="0 0 24 24" aria-hidden="true" className="shrink-0">
        <path fill="#4285F4" d="M23 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.2a5.3 5.3 0 0 1-2.3 3.5v2.9h3.7c2.2-2 3.4-5 3.4-8.6z" />
        <path fill="#34A853" d="M12 24c3.1 0 5.7-1 7.6-2.8l-3.7-2.9c-1 .7-2.3 1.1-3.9 1.1-3 0-5.5-2-6.4-4.7H1.8v3C3.7 21.4 7.6 24 12 24z" />
        <path fill="#FBBC05" d="M5.6 14.7a7.2 7.2 0 0 1 0-4.6v-3H1.8a12 12 0 0 0 0 10.6l3.8-3z" />
        <path fill="#EA4335" d="M12 4.8c1.7 0 3.2.6 4.4 1.7l3.3-3.3C17.7 1.2 15.1 0 12 0 7.6 0 3.7 2.6 1.8 6.4l3.8 3C6.5 6.7 9 4.8 12 4.8z" />
      </svg>
      {label}
    </button>
  )
}
