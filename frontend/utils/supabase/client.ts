import { createBrowserClient } from '@supabase/ssr'

/**
 * Browser-side Supabase client for use in Client Components.
 * Safe to call multiple times — createBrowserClient is a singleton per tab.
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
  )
}
