/**
 * API request/response types
 */

export interface ApiError {
  error: string
  details?: string
}

export interface ApiResponse<T> {
  data?: T
  error?: string
}

export interface PaginationParams {
  skip?: number
  limit?: number
}

export interface ReprocessImageRequest {
  preset: 'gentle' | 'balanced' | 'aggressive'
}

export interface FindDuplicatesRequest {
  source: 'input' | 'output'
  threshold: number  // 0.0 - 1.0
}

export interface AddTagRequest {
  tag: string
  category?: string
}

export interface UpdateMetadataRequest {
  rotation?: number
  mirror_h?: boolean
  mirror_v?: boolean
  film_type?: string
  era?: string
}
