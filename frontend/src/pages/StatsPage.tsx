import { useStatsStore } from '@/store/useStatsStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { TimelineChart } from '@/components/features/stats/TimelineChart'
import { AlertCircle, TrendingDown, TrendingUp, Minus, ArrowRight, CheckCircle, Clock, Zap, AlertTriangle, RefreshCw, Database } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { rescanOutputDirectory } from '@/lib/api/rescan'
import { useState } from 'react'

export function StatsPage() {
  const stats = useStatsStore((state) => state.stats)
  const connectionStatus = useStatsStore((state) => state.connectionStatus)
  const [isRescanning, setIsRescanning] = useState(false)
  const [rescanResult, setRescanResult] = useState<any>(null)

  const handleRescan = async () => {
    setIsRescanning(true)
    setRescanResult(null)
    try {
      const result = await rescanOutputDirectory(true)
      setRescanResult(result)
    } catch (error) {
      setRescanResult({ error: 'Failed to rescan directory' })
    } finally {
      setIsRescanning(false)
    }
  }

  // Format ETA
  const formatETA = (minutes: number) => {
    if (minutes === 0) return 'N/A'
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    if (hours > 24) {
      const days = Math.floor(hours / 24)
      const remainingHours = hours % 24
      return `${days}d ${remainingHours}h`
    }
    return `${hours}h ${mins}m`
  }

  // Trend icon
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'accelerating':
        return <TrendingUp className="w-4 h-4 text-green-500" />
      case 'degrading':
        return <TrendingDown className="w-4 h-4 text-yellow-500" />
      default:
        return <Minus className="w-4 h-4 text-muted-foreground" />
    }
  }

  return (
    <div className="container mx-auto p-4 md:p-6 space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold">Pipeline Statistics</h1>
        <p className="text-sm md:text-base text-muted-foreground mt-1">Real-time monitoring dashboard</p>
      </div>

      {/* Connection Status Badge */}
      <Badge
        variant={connectionStatus === 'connected' ? 'default' : 'secondary'}
        className={connectionStatus === 'connected' ? 'bg-accent' : 'bg-destructive'}
      >
        {connectionStatus === 'connected' ? '● LIVE' : '○ DISCONNECTED'}
      </Badge>

      {stats && (
        <>
          {/* Alerts */}
          {stats.alerts && stats.alerts.length > 0 && (
            <div className="space-y-2">
              {stats.alerts.map((alert: any, index: number) => (
                <Alert key={index} variant={alert.severity === 'error' ? 'destructive' : 'default'}>
                  {alert.severity === 'error' ? <AlertCircle className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                  <AlertTitle className="capitalize">{alert.type.replace(/_/g, ' ')}</AlertTitle>
                  <AlertDescription>{alert.message}</AlertDescription>
                </Alert>
              ))}
            </div>
          )}

          {/* Current Processing Status */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {stats.current.is_processing ? (
                  <Zap className="w-5 h-5 text-accent animate-pulse" />
                ) : (
                  <CheckCircle className="w-5 h-5 text-muted-foreground" />
                )}
                Current Status
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">State:</span>
                <Badge variant={stats.current.is_processing ? 'default' : 'secondary'}
                       className={stats.current.is_processing ? 'bg-accent' : ''}>
                  {stats.current.is_processing ? 'Processing' : 'Idle'}
                </Badge>
              </div>
              {stats.current.current_file && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Current File:</p>
                  <p className="text-sm font-mono break-all">{stats.current.current_file}</p>
                </div>
              )}
              {stats.current.current_stage && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Stage:</span>
                  <Badge variant="outline" className="capitalize">{stats.current.current_stage}</Badge>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Pipeline Visualization */}
          <Card>
            <CardHeader>
              <CardTitle>Pipeline Flow</CardTitle>
              <CardDescription>Processing stages</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col md:flex-row items-center justify-center gap-3 md:gap-6 py-4">
                {/* Input Stage */}
                <div className="flex flex-col items-center text-center w-full md:w-auto">
                  <div className="w-20 h-20 rounded-lg bg-blue-500/20 border-2 border-blue-500 flex items-center justify-center mb-2">
                    <span className="text-2xl font-bold text-blue-500">{stats.pipeline.input_queue}</span>
                  </div>
                  <p className="text-xs font-medium">INPUT</p>
                  <p className="text-xs text-muted-foreground">Queue</p>
                </div>

                <ArrowRight className="hidden md:block w-6 h-6 text-muted-foreground" />

                {/* Analysed Stage */}
                <div className="flex flex-col items-center text-center w-full md:w-auto">
                  <div className="w-20 h-20 rounded-lg bg-yellow-500/20 border-2 border-yellow-500 flex items-center justify-center mb-2">
                    <span className="text-2xl font-bold text-yellow-500">{stats.pipeline.analysed_queue}</span>
                  </div>
                  <p className="text-xs font-medium">ANALYSED</p>
                  <p className="text-xs text-muted-foreground">Processing</p>
                </div>

                <ArrowRight className="hidden md:block w-6 h-6 text-muted-foreground" />

                {/* Enhanced Stage */}
                <div className="flex flex-col items-center text-center w-full md:w-auto">
                  <div className="w-20 h-20 rounded-lg bg-green-500/20 border-2 border-green-500 flex items-center justify-center mb-2">
                    <span className="text-2xl font-bold text-green-500">{stats.pipeline.completed_total}</span>
                  </div>
                  <p className="text-xs font-medium">ENHANCED</p>
                  <p className="text-xs text-muted-foreground">Complete</p>
                </div>
              </div>

              {/* Session Progress */}
              {stats.pipeline.completed_session > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Session Progress</span>
                    <span className="font-medium">{stats.pipeline.completed_session} processed</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Database Sync */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="w-5 h-5" />
                Database Management
              </CardTitle>
              <CardDescription>Sync output directory with database</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Scan output directory for images not in the database, generate missing thumbnails, and write tags to image metadata.
              </p>
              <Button
                onClick={handleRescan}
                disabled={isRescanning}
                className="w-full"
              >
                {isRescanning ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Scanning...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Rescan & Sync Database
                  </>
                )}
              </Button>

              {rescanResult && (
                <Alert variant={rescanResult.error ? 'destructive' : 'default'} className="mt-3">
                  {rescanResult.error ? (
                    <>
                      <AlertCircle className="h-4 w-4" />
                      <AlertTitle>Error</AlertTitle>
                      <AlertDescription>{rescanResult.error}</AlertDescription>
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-4 w-4" />
                      <AlertTitle>Rescan Complete</AlertTitle>
                      <AlertDescription className="mt-2 space-y-1">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>Total scanned: <strong>{rescanResult.total_scanned}</strong></div>
                          <div>Already in DB: <strong>{rescanResult.already_in_db}</strong></div>
                          <div>Images added: <strong>{rescanResult.images_added}</strong></div>
                          <div>Thumbnails: <strong>{rescanResult.thumbnails_generated}</strong></div>
                          <div className="col-span-2">Tags written to files: <strong>{rescanResult.tags_written}</strong></div>
                        </div>
                      </AlertDescription>
                    </>
                  )}
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Performance Metrics */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5" />
                Performance
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Throughput</p>
                  <p className="text-xl font-bold">{stats.performance.pictures_per_hour.toFixed(1)} <span className="text-sm font-normal text-muted-foreground">pics/hr</span></p>
                </div>
                {stats.performance.avg_time_per_image && stats.performance.avg_time_per_image > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Avg Time</p>
                    <p className="text-xl font-bold">{Math.round(stats.performance.avg_time_per_image / 60)} <span className="text-sm font-normal text-muted-foreground">min/img</span></p>
                  </div>
                )}
              </div>

              {stats.performance.eta_minutes && stats.performance.eta_minutes > 0 && (
                <div className="pt-3 border-t">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      Estimated Completion
                    </span>
                    <span className="text-lg font-bold">{formatETA(stats.performance.eta_minutes)}</span>
                  </div>
                </div>
              )}

              {stats.performance.processing_trend && (
                <div className="pt-3 border-t">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Trend</span>
                    <div className="flex items-center gap-2">
                      {getTrendIcon(stats.performance.processing_trend)}
                      <span className="text-sm capitalize">{stats.performance.processing_trend}</span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Tag Statistics */}
          {stats.tags && (stats.tags.ai_tags.length > 0 || stats.tags.user_tags.length > 0) && (
            <Card>
              <CardHeader>
                <CardTitle>Tags Detected</CardTitle>
                <CardDescription>
                  {stats.tags.total_images_tagged} images tagged with {stats.tags.total_tags} unique tags
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* AI Tags */}
                {stats.tags.ai_tags.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                      <Badge variant="default" className="text-xs">AI</Badge>
                      Auto-detected Tags
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {stats.tags.ai_tags.slice(0, 20).map((tag: any, index: number) => (
                        <Badge
                          key={index}
                          variant="outline"
                          className="text-xs gap-1"
                        >
                          <span>{tag.tag}</span>
                          <span className="text-muted-foreground">({tag.count})</span>
                        </Badge>
                      ))}
                      {stats.tags.ai_tags.length > 20 && (
                        <Badge variant="outline" className="text-xs text-muted-foreground">
                          +{stats.tags.ai_tags.length - 20} more
                        </Badge>
                      )}
                    </div>
                  </div>
                )}

                {/* User Tags */}
                {stats.tags.user_tags.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                      <Badge variant="secondary" className="text-xs">User</Badge>
                      Manual Tags
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {stats.tags.user_tags.map((tag: any, index: number) => (
                        <Badge
                          key={index}
                          variant="outline"
                          className="text-xs gap-1 border-primary"
                        >
                          <span>{tag.tag}</span>
                          <span className="text-muted-foreground">({tag.count})</span>
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Top Tags Summary */}
                {stats.tags.ai_tags.length > 0 && (
                  <div className="pt-3 border-t">
                    <p className="text-xs text-muted-foreground mb-2">Top 5 Tags:</p>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                      {stats.tags.ai_tags.slice(0, 5).map((tag: any, index: number) => (
                        <div key={index} className="flex flex-col items-center text-center p-2 bg-muted/50 rounded-lg">
                          <span className="text-lg font-bold text-primary">{tag.count}</span>
                          <span className="text-xs text-muted-foreground truncate max-w-full">{tag.tag}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Session History */}
          {stats.history && (
            <Card>
              <CardHeader>
                <CardTitle>Session History</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Session Duration:</span>
                  <span className="font-medium">{stats.history.session_duration_hours?.toFixed(1) || '0'}h</span>
                </div>
                {stats.history.error_count && stats.history.error_count > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Errors:</span>
                    <span className="font-medium text-destructive">{stats.history.error_count}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Error Log */}
          {stats.history?.error_log && stats.history.error_log.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-destructive">
                  <AlertCircle className="w-5 h-5" />
                  Error Log
                </CardTitle>
                <CardDescription>Recent processing errors</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {stats.history.error_log.slice().reverse().map((error: any, index: number) => (
                    <div key={index} className="border border-destructive/30 rounded-lg p-3 space-y-1 bg-destructive/5">
                      <div className="flex items-start justify-between gap-2">
                        <p className="font-mono text-sm font-medium break-all">{error.filename}</p>
                        <Badge variant="destructive" className="shrink-0 text-xs">
                          {error.stage}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {new Date(error.timestamp).toLocaleString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit'
                        })}
                      </p>
                      <p className="text-sm text-destructive break-words">{error.error}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Timeline Chart - 48 hours */}
          {stats?.history?.hourly_timeline && stats.history.hourly_timeline.length > 0 && (
            <TimelineChart data={stats.history.hourly_timeline} />
          )}
        </>
      )}
    </div>
  )
}
