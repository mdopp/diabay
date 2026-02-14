import { useStatsStore } from '@/store/useStatsStore'
import { Badge } from '@/components/ui/badge'
import { Activity, Loader2, WifiOff } from 'lucide-react'

/**
 * Real-time status indicator showing WebSocket connection and pipeline state
 */
export function StatusIndicator() {
  const stats = useStatsStore((state) => state.stats)
  const connectionStatus = useStatsStore((state) => state.connectionStatus)

  const isProcessing = stats?.current.is_processing ?? false
  const isConnected = connectionStatus === 'connected'

  // Determine status color and icon
  const getStatusConfig = () => {
    if (!isConnected) {
      return {
        color: 'text-destructive',
        bgColor: 'bg-destructive/10',
        icon: <WifiOff className="w-4 h-4" />,
        label: 'Disconnected',
      }
    }

    if (isProcessing) {
      return {
        color: 'text-accent',
        bgColor: 'bg-accent/10',
        icon: <Loader2 className="w-4 h-4 animate-spin" />,
        label: 'Processing',
      }
    }

    return {
      color: 'text-muted-foreground',
      bgColor: 'bg-muted',
      icon: <Activity className="w-4 h-4" />,
      label: 'Idle',
    }
  }

  const config = getStatusConfig()

  return (
    <Badge
      variant="outline"
      className={`flex items-center gap-2 ${config.bgColor} ${config.color} border-border`}
    >
      {config.icon}
      <span className="hidden md:inline">{config.label}</span>
    </Badge>
  )
}
