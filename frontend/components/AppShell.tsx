"use client"
import { useState } from "react"
import useWebsocket from "@/hooks/useWebsocket"
import HalalifyChat from "@/components/HalalifyChat"
import ChatHistory from "@/components/ChatHistory"

export default function AppShell() {
    const [activeThreadId, setActiveThreadId] = useState(() => crypto.randomUUID())
    // True while an existing session's history is being fetched, so the chat
    // shows a skeleton instead of flashing the landing page. Not set for "New chat".
    const [historyLoading, setHistoryLoading] = useState(false)

    // One long-lived socket, shared by the chat and the history cupboard. The
    // session id travels in each message, so switching sessions never reconnects.
    const ws = useWebsocket(`${process.env.NEXT_PUBLIC_BACKEND_WS_URL}/ws`)

    const handleSelectSession = (id: string) => {
        if (id === activeThreadId) return
        setHistoryLoading(true)
        setActiveThreadId(id)
    }

    const handleNewChat = () => {
        setHistoryLoading(false)
        setActiveThreadId(crypto.randomUUID())
    }

    return (
        <>
            <ChatHistory
                activeThreadId={activeThreadId}
                onSelectSession={handleSelectSession}
                onNewChat={handleNewChat}
                sendMessage={ws.sendMessage}
                lastMessage={ws.lastMessage}
                messageCount={ws.messageCount}
            />
            <HalalifyChat
                threadId={activeThreadId}
                ws={ws}
                historyLoading={historyLoading}
                onHistoryLoaded={() => setHistoryLoading(false)}
            />
        </>
    )
}
