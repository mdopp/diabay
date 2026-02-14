import apiClient from './client'
import type { ImageListResponse, ImageDetail, Image } from '@/types/image'
import type {
  PaginationParams,
  ReprocessImageRequest,
  AddTagRequest,
  UpdateMetadataRequest
} from '@/types/api'

/**
 * Image API endpoints
 */

export const imagesApi = {
  /**
   * List all images with pagination
   */
  list: async (params: PaginationParams = {}): Promise<ImageListResponse> => {
    const { skip = 0, limit = 100 } = params
    const response = await apiClient.get<ImageListResponse>('/api/images', {
      params: { skip, limit },
    })
    return response.data
  },

  /**
   * Get image details by ID
   */
  getById: async (id: number): Promise<ImageDetail> => {
    const response = await apiClient.get<ImageDetail>(`/api/images/${id}`)
    return response.data
  },

  /**
   * Reprocess image with different preset
   */
  reprocess: async (id: number, request: ReprocessImageRequest): Promise<Image> => {
    const response = await apiClient.post<Image>(
      `/api/images/${id}/reprocess`,
      request
    )
    return response.data
  },

  /**
   * Delete image
   * TODO: Backend endpoint needs to be implemented
   */
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/images/${id}`)
  },

  /**
   * Add tag to image
   * TODO: Backend endpoint needs to be implemented
   */
  addTag: async (id: number, request: AddTagRequest): Promise<void> => {
    await apiClient.post(`/api/images/${id}/tags`, request)
  },

  /**
   * Remove tag from image
   * TODO: Backend endpoint needs to be implemented
   */
  removeTag: async (id: number, tag: string): Promise<void> => {
    await apiClient.delete(`/api/images/${id}/tags/${encodeURIComponent(tag)}`)
  },

  /**
   * Update image metadata
   * TODO: Backend endpoint needs to be implemented
   */
  updateMetadata: async (id: number, request: UpdateMetadataRequest): Promise<void> => {
    await apiClient.patch(`/api/images/${id}/metadata`, request)
  },

  /**
   * Rotate image
   * TODO: Backend endpoint needs to be implemented
   */
  rotate: async (id: number, degrees: number): Promise<void> => {
    await apiClient.post(`/api/images/${id}/rotate`, { degrees })
  },
}
