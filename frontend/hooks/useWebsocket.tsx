"use client"
import { useRef, useState, useEffect } from "react"
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

        let reconnectTimeout: NodeJS.Timeout

        const connect = () => {
            if (totalReconnectAttempts.current >= MAX_RECONNECT_TRIES) {
                console.log("Max reconnect attempts reached. Waiting for manual user action.")
                setIsConnected(false)
                return
            }
            const ws = new WebSocket(authedUrlRef.current!)
            wsRef.current = ws

            ws.onopen = () => {
                console.log("Websocket connected successfully!")
                totalReconnectAttempts.current = 0
                setIsConnected(true)
            }

            ws.onmessage = (event) => {
                setLastMessage(event.data)
                setMessageCount(prev => prev + 1)
            }

            ws.onclose = () => {
                console.warn("Websocket connection closed!")
                setIsConnected(false)
                totalReconnectAttempts.current += 1
                const delay = Math.min(1000 * Math.pow(2, reconnectAttemptRef.current), 30000)
                console.log(`❌ Socket closed. Retrying in ${delay / 1000}s...`)
                reconnectTimeout = setTimeout(() => {
                    reconnectAttemptRef.current += 1
                    wsRef.current = null
                    connect()
                }, delay)
            }

            ws.onerror = (error) => {
                console.error(`Websocket Error: ${error}`)
                wsRef.current?.close()
            }
        }

        connect()

        return () => {
            clearTimeout(reconnectTimeout)
            wsRef.current?.close()
        }
    }, [authedUrl])

    const sendMessage = (message: string) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(message)
        }
    }

    return { isConnected, messageCount, lastMessage, sendMessage }
}

export default useWebsocket
