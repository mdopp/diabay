import { useQuery } from '@tanstack/react-query'
import { statsApi } from '@/lib/api/stats'
import { useStatsStore } from '@/store/useStatsStore'

/**
 * React Query hook for stats (fallback when WebSocket disconnected)
 */

export function useStats() {
  const isConnected = useStatsStore((state) => state.isConnected)

  return useQuery({
    queryKey: ['stats'],
    queryFn: () => statsApi.get(),
    enabled: !isConnected, // Only fetch when WebSocket disconnected
    refetchInterval: isConnected ? false : 5000, // Poll every 5s when disconnected
  })
}
