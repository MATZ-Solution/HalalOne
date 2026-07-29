import { createClient } from '@/utils/supabase/server'
import Landing from '@/components/landing/Landing'

// The landing page is the public entry point for everyone. Its "Get started"
// CTA sends visitors to /login (then on to /chat); signed-in visitors see their
// profile in the nav and go straight to the app. /chat is the only gated route.
export default async function App() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  const profile = user
    ? {
        name:
          (user.user_metadata?.full_name as string) ||
          (user.email ? user.email.split('@')[0] : 'User'),
        email: user.email ?? '',
        avatarUrl:
          (user.user_metadata?.avatar_url as string) ||
          (user.user_metadata?.picture as string) ||
          '',
      }
    : null

  return <Landing profile={profile} />
}
