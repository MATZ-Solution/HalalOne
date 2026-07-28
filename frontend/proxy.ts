import { NextResponse, type NextRequest } from 'next/server'
import { createServerClient } from '@supabase/ssr'

/**
 * Next.js 16 Proxy (formerly Middleware).
 * Runs before every matched request to:
 *  1. Refresh the Supabase session cookie (keeps the user logged in).
 *  2. Redirect unauthenticated users to /login.
 *  3. Redirect already-authenticated users away from auth pages.
 */
export async function proxy(request: NextRequest) {
  // Start with a passthrough response so cookies can be mutated on it.
  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          // Write updated cookies back to both the request and response so
          // downstream server components see the refreshed session.
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          )
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  const path = request.nextUrl.pathname

  // Let /auth/* routes pass through untouched — the route handler owns the
  // PKCE cookie exchange. Calling getUser() here would consume the verifier
  // cookie and cause bad_oauth_state errors on subsequent callback requests.
  if (path.startsWith('/auth')) {
    return NextResponse.next({ request })
  }

  // getUser() validates the JWT on the Supabase server — more secure than getSession().
  const { data: { user } } = await supabase.auth.getUser()

  const isAuthPage = path.startsWith('/login') || path.startsWith('/signup')

  // Unauthenticated user trying to access a protected page → send to login.
  if (!user && !isAuthPage) {
    const loginUrl = request.nextUrl.clone()
    loginUrl.pathname = '/login'
    return NextResponse.redirect(loginUrl)
  }

  // Authenticated user visiting login/signup → send to app root.
  if (user && isAuthPage) {
    const homeUrl = request.nextUrl.clone()
    homeUrl.pathname = '/'
    return NextResponse.redirect(homeUrl)
  }

  return supabaseResponse
}

export const config = {
  matcher: [
    // Run on all paths except Next.js internals and static assets.
    '/((?!_next/static|_next/image|favicon.ico|.*\\.svg$|.*\\.png$|.*\\.jpg$|.*\\.ico$).*)',
  ],
}
