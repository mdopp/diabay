import { useEffect, useRef, useCallback } from 'react'
import { WebSocketManager } from '@/lib/websocket/client'
import { useStatsStore } from '@/store/useStatsStore'

/**
 * React hook for WebSocket connection
 * Automatically connects on mount and disconnects on unmount
 * Retries indefinitely with exponential backoff (capped at 30s)
 */

export function useWebSocket() {
  const wsRef = useRef<WebSocketManager | null>(null)
  const isConnecting = useRef(false)

  useEffect(() => {
    // Prevent double-connection in React StrictMode
    if (isConnecting.current) {
      return
    }
    isConnecting.current = true

    // Use dynamic WebSocket URL based on current hostname
    // This allows accessing from any device on the network
    // Evaluate at runtime to ensure window is available
    const WS_URL = import.meta.env.VITE_WS_URL ||
      `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8000/ws/status`

    // Get store functions
    const handleWebSocketMessage = useStatsStore.getState().handleWebSocketMessage
    const setConnectionStatus = useStatsStore.getState().setConnectionStatus

    // Create WebSocket manager
    wsRef.current = new WebSocketManager({
      url: WS_URL,
      onMessage: (message) => {
        try {
          handleWebSocketMessage(message)
        } catch (error) {
          console.error('[useWebSocket] Error handling message:', error)
        }
      },
      onStatusChange: (status) => {
        setConnectionStatus(status)
      },
      reconnectDelay: 2000,
      maxReconnectAttempts: Infinity, // Infinite retries - will keep trying until backend comes back
      heartbeatInterval: 5000,
    })

    // Connect
    wsRef.current.connect()

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect()
        wsRef.current = null
      }
      isConnecting.current = false
    }
  }, []) // Empty dependency array - only connect once

  const reconnect = useCallback(() => {
    wsRef.current?.reconnect()
  }, [])

  return {
    status: wsRef.current?.status || 'disconnected',
    reconnect, // Expose manual reconnect for UI
    reconnectInfo: wsRef.current?.reconnectInfo || { attempts: 0, isRetrying: false },
  }
}
