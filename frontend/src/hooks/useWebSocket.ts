import { useEffect, useRef, useState, useCallback } from 'react'
import type { WSServerMessage, WSClientMessage } from '../types/council'

interface UseWebSocketOptions {
  onMessage?: (message: WSServerMessage) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: Event) => void
}

interface UseWebSocketReturn {
  isConnected: boolean
  send: (message: WSClientMessage) => void
  connect: () => void
  disconnect: () => void
}

export function useWebSocket(
  sessionId: string | undefined,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const { onMessage, onOpen, onClose, onError } = options
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number>()

  const connect = useCallback(() => {
    if (!sessionId) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const ws = new WebSocket(`${protocol}//${host}/ws/council/${sessionId}`)

    ws.onopen = () => {
      setIsConnected(true)
      onOpen?.()
    }

    ws.onclose = () => {
      setIsConnected(false)
      onClose?.()
    }

    ws.onerror = (error) => {
      onError?.(error)
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WSServerMessage
        onMessage?.(message)
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    wsRef.current = ws
  }, [sessionId, onMessage, onOpen, onClose, onError])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  const send = useCallback((message: WSClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  // クリーンアップ
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    isConnected,
    send,
    connect,
    disconnect,
  }
}
