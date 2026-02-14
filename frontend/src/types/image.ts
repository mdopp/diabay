/**
 * Image type definitions matching backend API
 */

export type ImageStatus = 'pending' | 'processing' | 'complete' | 'error'
export type ProcessingStage = 'ingestion' | 'enhancement' | 'tagging' | 'saving'
export type EnhancementPreset = 'gentle' | 'balanced' | 'aggressive' | 'auto'

export interface Image {
  id: number
  filename: string
  original_path?: string
  original_preview_url?: string  // URL to downscaled JPEG preview of TIFF original (2000px, cacheable)
  enhanced_path: string
  thumbnail_url?: string  // URL to thumbnail (400px max)
  width: number
  height: number
  file_size?: number
  status: ImageStatus
  stage?: ProcessingStage
  progress?: number

  // Enhancement parameters
  enhancement_params?: {
    histogram_clip: number
    clahe_clip: number
    face_detected: boolean
    preset_used?: EnhancementPreset
  }

  // Timestamps
  created_at: string
  processed_at?: string
  updated_at?: string
  exif_date?: string
}

export interface ImageTag {
  tag: string
  source: 'ai' | 'manual'
  confidence?: number
  category?: 'scene' | 'era' | 'film_stock' | 'custom'
}

export interface ImageMetadata {
  rotation: number  // 0, 90, 180, 270
  mirror_h: boolean
  mirror_v: boolean
  film_type?: string
  era?: string
  ocr_text?: string
}

export interface ImageDetail extends Image {
  tags: ImageTag[]
  metadata?: ImageMetadata
}

export interface ImageListResponse {
  total: number
  images: Image[]
}

export interface DuplicateGroup {
  id: string
  images: Image[]
  similarity: number
  type: 'exact' | 'near' | 'similar'
  source: 'input' | 'output'
}
