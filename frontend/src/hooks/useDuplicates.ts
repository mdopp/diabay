import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { duplicatesApi } from '@/lib/api/duplicates'
import type { FindDuplicatesRequest } from '@/types/api'

/**
 * React Query hooks for duplicate detection
 */

export function useDuplicates(request: FindDuplicatesRequest) {
  return useQuery({
    queryKey: ['duplicates', request],
    queryFn: () => duplicatesApi.find(request),
    enabled: false, // Manual trigger only
    staleTime: 60000, // 1 minute
  })
}

export function useDeleteDuplicates() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (imageIds: number[]) => duplicatesApi.deleteDuplicates(imageIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['images'] })
      queryClient.invalidateQueries({ queryKey: ['duplicates'] })
    },
  })
}
