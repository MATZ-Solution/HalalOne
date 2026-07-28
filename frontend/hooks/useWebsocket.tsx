"use client"
import { useRef, useState, useEffect, useCallback } from "react"
import { createClient } from "@/utils/supabase/client"

interface UseWebSocketReturn {
    isConnected: boolean;
    lastMessage: string | null;
    messageCount: number;
    sendMessage: (message: string) => void;
}

const MAX_RECONNECT_TRIES = 5

const useWebsocket = (url: string): UseWebSocketReturn => {
    const wsRef = useRef<WebSocket | null>(null)
    const [isConnected, setIsConnected] = useState(false)
    const [lastMessage, setLastMessage] = useState<string | null>(null)
    const [messageCount, setMessageCount] = useState<number>(0)
    const reconnectAttemptRef = useRef(0)
    const totalReconnectAttempts = useRef(0)

    // Authenticated URL built once the Supabase session is resolved.
    const authedUrlRef = useRef<string | null>(null)
    const [authedUrl, setAuthedUrl] = useState<string | null>(null)

    // Fetch the access token and append it as ?token=... before connecting.
    useEffect(() => {
        const supabase = createClient()
        supabase.auth.getSession().then(({ data: { session } }) => {
            const token = session?.access_token ?? ""
            authedUrlRef.current = `${url}?token=${token}`
            setAuthedUrl(authedUrlRef.current)
        })
    }, [url])

    useEffect(() => {
        if (!authedUrl) return

        let reconnectTimeout: NodeJS.Timeout | undefined
        let stableTimeout: NodeJS.Timeout | undefined
        // Scoped to this effect instance. Set on cleanup (unmount / URL change)
        // so an intentional close doesn't count as a failure or trigger a reconnect.
        let cancelled = false

        const scheduleReconnect = () => {
            if (cancelled) return
            // Count every failed attempt toward the cap. Because the cap is only
            // reset after a *stable* connection (see onopen), a server that
            // accepts-then-closes can't reconnect forever (which would flood
            // setState and trip React's max-update-depth).
            totalReconnectAttempts.current += 1
            if (totalReconnectAttempts.current >= MAX_RECONNECT_TRIES) {
                console.log("Max reconnect attempts reached. Waiting for manual user action.")
                return
            }
            const delay = Math.min(1000 * Math.pow(2, reconnectAttemptRef.current), 30000)
            console.log(`❌ Socket closed. Retrying in ${delay / 1000}s...`)
            reconnectTimeout = setTimeout(() => {
                reconnectAttemptRef.current += 1
                wsRef.current = null
                connect()
            }, delay)
        }

        const connect = () => {
            if (cancelled) return
            if (totalReconnectAttempts.current >= MAX_RECONNECT_TRIES) {
                setIsConnected(false)
                return
            }

            let ws: WebSocket
            try {
                ws = new WebSocket(authedUrlRef.current!)
            } catch (err) {
                // e.g. malformed URL (NEXT_PUBLIC_BACKEND_WS_URL unset). Don't let
                // the throw re-run the effect into a tight loop.
                console.error("Failed to open WebSocket:", err)
                setIsConnected(false)
                scheduleReconnect()
                return
            }
            wsRef.current = ws

            ws.onopen = () => {
                console.log("Websocket connected successfully!")
                reconnectAttemptRef.current = 0
                setIsConnected(true)
                // Only clear the failure cap once the connection has stayed open
                // a while — a flapping server shouldn't be able to reset it.
                stableTimeout = setTimeout(() => { totalReconnectAttempts.current = 0 }, 5000)
            }

            ws.onmessage = (event) => {
                setLastMessage(event.data)
                setMessageCount(prev => prev + 1)
            }

            ws.onclose = () => {
                clearTimeout(stableTimeout)
                setIsConnected(false)
                // Don't reconnect when the close was intentional (URL change/unmount).
                if (cancelled) return
                console.warn("Websocket connection closed!")
                scheduleReconnect()
            }

            ws.onerror = (error) => {
                console.error(`Websocket Error: ${error}`)
                wsRef.current?.close()
            }
        }

        connect()

        return () => {
            cancelled = true
            clearTimeout(reconnectTimeout)
            clearTimeout(stableTimeout)
            wsRef.current?.close()
        }
    }, [authedUrl])

    // Stable identity so consumers can safely list it in effect deps.
    const sendMessage = useCallback((message: string) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(message)
        }
    }, [])

    return { isConnected, messageCount, lastMessage, sendMessage }
}

export default useWebsocket
