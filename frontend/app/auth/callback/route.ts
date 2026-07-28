import { NextResponse } from 'next/server'
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

/**
 * OAuth / Magic-link callback handler.
 *
 * After Google (or any provider) redirects back here with ?code=...,
 * this route exchanges that authorization code for a Supabase session.
 * This is the PKCE step: the code verifier stored in the browser cookie
 * is used server-side to verify the code challenge sent to the provider.
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const code = searchParams.get('code')
  // Optional: redirect to a specific page after login (e.g. ?next=/dashboard)
  const next = searchParams.get('next') ?? '/'

  // Public base URL to redirect back to after login. `request.url`'s origin is
  // the address the container sees internally (e.g. http://localhost:3000 behind
  // a reverse proxy), so it can't be trusted for the user-facing redirect.
  // Use the explicit site URL; fall back to local dev when it isn't set.
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'

  if (code) {
    const cookieStore = await cookies()

    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll()
          },
          setAll(cookiesToSet) {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            )
          },
        },
      }
    )

    const { error } = await supabase.auth.exchangeCodeForSession(code)

    if (!error) {
      return NextResponse.redirect(`${baseUrl}${next}`)
    }
  }

  // Something went wrong — send back to login with an error flag.
  return NextResponse.redirect(`${baseUrl}/login?error=auth_callback_error`)
}
