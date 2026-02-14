import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { imagesApi } from '@/lib/api/images'
import type { PaginationParams, ReprocessImageRequest } from '@/types/api'

/**
 * React Query hooks for image operations
 */

export function useImages(params: PaginationParams = {}) {
  return useQuery({
    queryKey: ['images', params],
    queryFn: () => imagesApi.list(params),
    staleTime: 10000, // 10 seconds
    refetchInterval: 30000, // Refetch every 30 seconds
  })
}

export function useImageDetail(id: number) {
  return useQuery({
    queryKey: ['images', id],
    queryFn: () => imagesApi.getById(id),
    enabled: id > 0,
  })
}

export function useReprocessImage() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, request }: { id: number; request: ReprocessImageRequest }) =>
      imagesApi.reprocess(id, request),
    onSuccess: (_, variables) => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['images', variables.id] })
      queryClient.invalidateQueries({ queryKey: ['images'] })
    },
  })
}

export function useDeleteImage() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => imagesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['images'] })
    },
  })
}

export function useAddTag() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, tag, category }: { id: number; tag: string; category?: string }) =>
      imagesApi.addTag(id, { tag, category }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['images', variables.id] })
    },
  })
}

export function useRemoveTag() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, tag }: { id: number; tag: string }) =>
      imagesApi.removeTag(id, tag),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['images', variables.id] })
    },
  })
}
