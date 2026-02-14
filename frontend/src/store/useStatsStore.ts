import { create } from 'zustand'
import type { PipelineStats, WebSocketMessage } from '@/types/stats'
import type { WebSocketStatus } from '@/lib/websocket/client'

/**
 * Statistics store - synced with WebSocket
 */

interface StatsStore {
  stats: PipelineStats | null
  isConnected: boolean
  connectionStatus: WebSocketStatus
  lastUpdate: Date | null
  lastDeletedImageId: number | null

  // Actions
  updateStats: (stats: PipelineStats) => void
  setConnectionStatus: (status: WebSocketStatus) => void
  clearStats: () => void
  handleWebSocketMessage: (message: WebSocketMessage) => void
}

export const useStatsStore = create<StatsStore>((set) => ({
  stats: null,
  isConnected: false,
  connectionStatus: 'disconnected',
  lastUpdate: null,
  lastDeletedImageId: null,

  updateStats: (stats: PipelineStats) => {
    set({
      stats,
      lastUpdate: new Date(),
      isConnected: true,
    })
  },

  setConnectionStatus: (status: WebSocketStatus) => {
    set({
      connectionStatus: status,
      isConnected: status === 'connected',
    })
  },

  clearStats: () => {
    set({
      stats: null,
      lastUpdate: null,
    })
  },

  handleWebSocketMessage: (message: WebSocketMessage) => {
    // Check if this is a deletion event
    if ('type' in message && message.type === 'image_deleted') {
      console.log('[StatsStore] Image deleted:', message.image_id)
      set({ lastDeletedImageId: message.image_id })
    } else {
      // Regular stats update
      set({
        stats: message as PipelineStats,
        lastUpdate: new Date(),
        isConnected: true,
      })
    }
  },
}))
