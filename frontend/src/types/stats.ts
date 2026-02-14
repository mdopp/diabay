/**
 * Statistics and pipeline status types
 */

export interface PipelineStats {
  current: {
    is_processing: boolean
    current_file?: string
    current_stage?: string
    progress: number
    error?: string | null
  }

  pipeline: {
    input_queue: number         // TIFFs in input/
    analysed_queue: number      // TIFFs in analysed/
    completed_total: number     // Total JPEGs in output/
    completed_session: number   // JPEGs processed this session
  }

  performance: {
    pictures_per_hour: number
    avg_time_per_image?: number  // seconds
    eta_minutes?: number
    eta_timestamp?: string
    processing_trend?: 'accelerating' | 'stable' | 'degrading'
  }

  history?: {
    session_duration_hours?: number
    error_count?: number
    hourly_timeline?: HourlyCount[]  // Last 48 hours of processing
    error_log?: ErrorLog[]           // Recent errors with details
  }

  alerts?: Alert[]

  tags?: {
    ai_tags: TagCount[]
    user_tags: TagCount[]
    total_tags: number
    total_images_tagged: number
  }
}

export interface TagCount {
  tag: string
  count: number
}

export interface Alert {
  type: 'stall_warning' | 'performance_degradation' | 'high_error_rate' | 'all_errors' | 'error' | 'info'
  message: string
  timestamp: string
  severity?: 'info' | 'warning' | 'error'
}

export interface HourlyCount {
  hour: string          // Display label (e.g., "14:00")
  timestamp: string     // Full timestamp (e.g., "2026-02-11 14:00")
  count: number         // Number of images processed in this hour
}

export interface ErrorLog {
  filename: string      // Name of file that failed
  error: string         // Error message
  timestamp: string     // ISO timestamp
  stage: string         // Processing stage where error occurred
}

/**
 * WebSocket message types
 */
export type WebSocketMessage = PipelineStats | ImageDeletedEvent

export interface ImageDeletedEvent {
  type: 'image_deleted'
  image_id: number
  filename: string
}
