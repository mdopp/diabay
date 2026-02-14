import { apiClient } from './client'

export interface RescanResult {
  success: boolean
  images_added: number
  thumbnails_generated: number
  tags_written: number
  total_scanned: number
  already_in_db: number
}

/**
 * Rescan output directory and sync with database
 */
export async function rescanOutputDirectory(writeTagsToFiles: boolean = true): Promise<RescanResult> {
  const response = await apiClient.post<RescanResult>('/api/rescan', null, {
    params: { write_tags_to_files: writeTagsToFiles }
  })
  return response.data
}
