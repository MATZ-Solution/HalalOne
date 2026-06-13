'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/utils/supabase/client'

export default function LogoutButton() {
  const router = useRouter()
  const supabase = createClient()

  // Read the same localStorage key HalalifyChat writes to.
  const [isLight, setIsLight] = useState(false)

  useEffect(() => {
    const read = () => setIsLight(localStorage.getItem('halalify-theme') === 'light')
    read()
    // storage event only fires across tabs; poll for same-tab changes.
    const id = setInterval(read, 200)
    return () => clearInterval(id)
  }, [])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/login')
    router.refresh()
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      title="Sign out"
      className={`flex items-center gap-1.5 text-xs transition-colors px-2 py-1 rounded-lg cursor-pointer ${
        isLight
          ? 'text-black/40 hover:text-black/70 hover:bg-black/5'
          : 'text-white/40 hover:text-white/70 hover:bg-white/5'
      }`}
    >
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
        <polyline points="16 17 21 12 16 7" />
        <line x1="21" y1="12" x2="9" y2="12" />
      </svg>
      Sign out
    </button>
  )
}
