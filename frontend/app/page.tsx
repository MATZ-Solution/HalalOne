import { redirect } from 'next/navigation'
import { createClient } from '@/utils/supabase/server'
import HalalifyChat from '@/pages/HalalifyChat'
import LogoutButton from '@/components/auth/LogoutButton'

/**
 * Root page — server component.
 * The proxy.ts already redirects unauthenticated users, but we double-check
 * here so the server component never renders for a logged-out user.
 */
export default async function App() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/login')
  }

  return (
    <>
      {/* Floating sign-out button — fixed top-right, above chat UI */}
      <div className="fixed top-3 right-16 z-40">
        <LogoutButton />
      </div>
      <HalalifyChat />
    </>
  )
}
