import { redirect } from 'next/navigation'
import { createClient } from '@/utils/supabase/server'
import Landing from '@/components/landing/Landing'

// The landing page. Signed-in users land here after login; its CTAs lead to
// the chat/dashboard at /chat. Unauthenticated visitors go to /login.
export default async function App() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/login')
  }

  return <Landing />
}
