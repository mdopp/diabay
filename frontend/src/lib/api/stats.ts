import apiClient from './client'
import type { PipelineStats } from '@/types/stats'

/**
 * Statistics API endpoints
 */

export const statsApi = {
  /**
   * Get current pipeline statistics
   * Used as fallback when WebSocket is disconnected
   */
  get: async (): Promise<PipelineStats> => {
    const response = await apiClient.get<PipelineStats>('/api/stats')
    return response.data
  },
}
