"use client"
import { useRef, useState, useEffect } from "react";

interface UseWebSocketReturn {
    isConnected: boolean;
    lastMessage: string | null;
    messageCount: number;
    sendMessage: (message: string) => void;
}

const useWebsocket = (url: string): UseWebSocketReturn => {
    const wsRef = useRef<WebSocket | null>(null)
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<string | null>(null);
    // message counter, updates whenever a new message is received
    const [messageCount, setMessageCount] = useState<number>(0)

    useEffect(() => {
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("Websocket connected successfully!");
            setIsConnected(true);
        };

        ws.onmessage = (event) => {
            setLastMessage(event.data);
            setMessageCount(prev => prev + 1)
        };

        ws.onclose = () => {
            console.warn("Websocket connection closed!");
            setIsConnected(false);
        };

        ws.onerror = (error) => {
            console.error(`Websocket Error: ${error}`);
        };

        return () => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.close();
            }
        };
    }, [url]);

    const sendMessage = (message: string) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(message)
        }
    }

    return { isConnected, messageCount, lastMessage, sendMessage }
}

export default useWebsocket