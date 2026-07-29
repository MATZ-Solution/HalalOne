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
  // Only the chat app requires authentication. The landing page and marketing
  // routes are public so visitors can browse before ever signing in.
  const isProtected = path.startsWith('/chat')

  // Unauthenticated user opening a protected page → send to login, remembering
  // where they were headed so we can return them there after they sign in.
  if (!user && isProtected) {
    const loginUrl = request.nextUrl.clone()
    loginUrl.pathname = '/login'
    loginUrl.search = ''
    loginUrl.searchParams.set('next', path)
    return NextResponse.redirect(loginUrl)
  }

  // Authenticated user visiting login/signup → skip the form. Honour a ?next=
  // (e.g. the "Get started" flow lands them on /chat); otherwise the landing.
  if (user && isAuthPage) {
    const dest = request.nextUrl.clone()
    const next = request.nextUrl.searchParams.get('next')
    dest.pathname = next && next.startsWith('/') && !next.startsWith('//') ? next : '/'
    dest.search = ''
    return NextResponse.redirect(dest)
  }

  return supabaseResponse
}

export const config = {
  matcher: [
    // Run on all paths except Next.js internals and static assets.
    '/((?!_next/static|_next/image|favicon.ico|.*\\.svg$|.*\\.png$|.*\\.jpg$|.*\\.ico$).*)',
  ],
}
