import apiClient from './client'
import type { DuplicateGroup } from '@/types/image'
import type { FindDuplicatesRequest } from '@/types/api'

/**
 * Duplicate detection API endpoints
 */

export interface DuplicatesResponse {
  groups: DuplicateGroup[]
  total_duplicates: number
  message?: string
}

export const duplicatesApi = {
  /**
   * Find duplicate images
   */
  find: async (request: FindDuplicatesRequest): Promise<DuplicatesResponse> => {
    const response = await apiClient.get<DuplicatesResponse>('/api/duplicates', {
      params: request,
    })
    return response.data
  },

  /**
   * Delete duplicate images
   * TODO: Backend endpoint needs to be implemented
   */
  deleteDuplicates: async (imageIds: number[]): Promise<void> => {
    await apiClient.post('/api/duplicates/delete', { image_ids: imageIds })
  },
}
