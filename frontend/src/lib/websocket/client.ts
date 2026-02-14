import type { WebSocketMessage } from '@/types/stats'

/**
 * WebSocket manager with automatic reconnection
 */

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

export interface WebSocketConfig {
  url: string
  onMessage: (message: WebSocketMessage) => void
  onStatusChange: (status: WebSocketStatus) => void
  reconnectDelay?: number
  maxReconnectAttempts?: number
  heartbeatInterval?: number
}

export class WebSocketManager {
  private ws: WebSocket | null = null
  private config: WebSocketConfig
  private reconnectAttempts = 0
  private reconnectDelay: number
  private maxReconnectAttempts: number
  private heartbeatInterval: number
  private heartbeatTimer: NodeJS.Timeout | null = null
  private reconnectTimer: NodeJS.Timeout | null = null
  private isIntentionallyClosed = false
  private maxReconnectDelay = 30000 // Cap at 30 seconds

  constructor(config: WebSocketConfig) {
    this.config = config
    this.reconnectDelay = config.reconnectDelay || 2000
    this.maxReconnectAttempts = config.maxReconnectAttempts || Infinity // Infinite retries by default
    this.heartbeatInterval = config.heartbeatInterval || 5000
  }

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      // [WebSocket] Already connected')
      return
    }

    this.isIntentionallyClosed = false
    this.config.onStatusChange('connecting')

    try {
      // [WebSocket] Connecting to:', this.config.url)
      this.ws = new WebSocket(this.config.url)

      this.ws.onopen = () => {
        // [WebSocket] Connected')
        this.reconnectAttempts = 0
        this.reconnectDelay = this.config.reconnectDelay || 2000
        this.config.onStatusChange('connected')
        this.startHeartbeat()
      }

      this.ws.onmessage = (event: MessageEvent) => {
        // [WebSocket] Received message:', event.data)
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          // [WebSocket] Parsed message successfully:', message)
          this.config.onMessage(message)
          // [WebSocket] onMessage callback completed')
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error)
          console.error('[WebSocket] Raw message data:', event.data)
        }
      }

      this.ws.onclose = () => {
        this.stopHeartbeat()
        this.config.onStatusChange('disconnected')

        if (!this.isIntentionallyClosed) {
          this.attemptReconnect()
        }
      }

      this.ws.onerror = (event: Event) => {
        console.error('[WebSocket] Error:', event)
        this.config.onStatusChange('error')
      }
    } catch (error) {
      console.error('[WebSocket] Connection failed:', error)
      this.config.onStatusChange('error')
      this.attemptReconnect()
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.isIntentionallyClosed = true
    this.stopHeartbeat()

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.config.onStatusChange('disconnected')
  }

  /**
   * Send message to server (e.g., heartbeat ping)
   */
  send(data: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(data)
    }
  }

  /**
   * Attempt to reconnect with exponential backoff (capped at 30s)
   * Retries indefinitely until backend comes back online
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnect attempts reached')
      this.config.onStatusChange('error')
      return
    }

    this.reconnectAttempts++

    // Exponential backoff, but cap at maxReconnectDelay (30s)
    const exponentialDelay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1)
    const delay = Math.min(exponentialDelay, this.maxReconnectDelay)

    console.log(
      `[WebSocket] Reconnecting in ${Math.round(delay / 1000)}s (attempt ${this.reconnectAttempts})`
    )

    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, delay)
  }

  /**
   * Start sending periodic heartbeat pings
   */
  private startHeartbeat(): void {
    this.stopHeartbeat()

    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send('ping')
      }
    }, this.heartbeatInterval)
  }

  /**
   * Stop heartbeat timer
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * Manually trigger reconnection (for UI retry button)
   */
  reconnect(): void {
    // [WebSocket] Manual reconnect triggered')
    this.reconnectAttempts = 0 // Reset attempt counter
    this.disconnect()
    this.connect()
  }

  /**
   * Get current connection status
   */
  get status(): WebSocketStatus {
    if (!this.ws) return 'disconnected'

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'connected'
      case WebSocket.CLOSING:
      case WebSocket.CLOSED:
        return 'disconnected'
      default:
        return 'disconnected'
    }
  }

  /**
   * Get reconnection info
   */
  get reconnectInfo() {
    return {
      attempts: this.reconnectAttempts,
      isRetrying: this.reconnectTimer !== null,
    }
  }
}
