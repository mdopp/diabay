import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { useDuplicates } from '@/hooks/useDuplicates'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { Scan, CheckCircle, Image as ImageIcon } from 'lucide-react'
import { API_URL, getAssetUrl } from '@/lib/api/client'

interface ScanProgress {
  is_scanning: boolean
  current: number
  total: number
  percent: number
  message: string
}

export function DuplicatesPage() {
  const [source, setSource] = useState<'input' | 'output'>('output')
  const [threshold, setThreshold] = useState(0.95)
  const [scanProgress, setScanProgress] = useState<ScanProgress | null>(null)
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean
    groupId: string
    duplicateCount: number
    duplicateImages: any[]
  }>({
    open: false,
    groupId: '',
    duplicateCount: 0,
    duplicateImages: []
  })

  const { data, refetch, isLoading, isFetching } = useDuplicates({ source, threshold })

  // Poll for progress while scanning
  useEffect(() => {
    if (!isFetching) {
      setScanProgress(null)
      return
    }

    const pollProgress = async () => {
      try {
        const response = await fetch(`${API_URL}/api/duplicates/progress')
        const progress: ScanProgress = await response.json()
        setScanProgress(progress)
      } catch (error) {
        console.error('Failed to fetch progress:', error)
      }
    }

    // Poll every 500ms while scanning
    const interval = setInterval(pollProgress, 500)
    pollProgress() // Initial poll

    return () => clearInterval(interval)
  }, [isFetching])

  const handleScan = () => {
    refetch()
  }

  const duplicateGroups = data?.groups || []
  const totalDuplicates = data?.total_duplicates || 0

  return (
    <div className="container mx-auto p-4 md:p-6 space-y-4 md:space-y-6 pb-20 md:pb-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-bold">Duplicate Cleanup</h1>
        <p className="text-sm md:text-base text-muted-foreground mt-1">Find and remove duplicate images</p>
      </div>

      {/* Scan Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Duplicate Detection</CardTitle>
          <CardDescription>
            Scan for duplicate or similar images based on visual similarity
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Source selector */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Scan Location</label>
            <div className="flex gap-2">
              <Button
                variant={source === 'input' ? 'default' : 'outline'}
                onClick={() => setSource('input')}
                className={`flex-1 ${source === 'input' ? 'ring-2 ring-primary ring-offset-2' : ''}`}
              >
                {source === 'input' && <CheckCircle className="w-4 h-4 mr-2" />}
                Input TIFFs
              </Button>
              <Button
                variant={source === 'output' ? 'default' : 'outline'}
                onClick={() => setSource('output')}
                className={`flex-1 ${source === 'output' ? 'ring-2 ring-primary ring-offset-2' : ''}`}
              >
                {source === 'output' && <CheckCircle className="w-4 h-4 mr-2" />}
                Enhanced JPEGs
              </Button>
            </div>
            <p className="text-xs text-accent-foreground font-medium break-words">
              <span className="hidden md:inline">Currently scanning: </span>
              {source === 'input' ? 'Input TIFFs (raw scans)' : 'Enhanced JPEGs (output)'}
            </p>
          </div>

          {/* Threshold slider */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-sm font-medium">Similarity Threshold</label>
              <Badge variant="outline" className="text-base font-bold">
                {(threshold * 100).toFixed(0)}%
              </Badge>
            </div>
            <div className="relative w-full">
              <input
                type="range"
                min="90"
                max="99"
                step="1"
                value={threshold * 100}
                onChange={(e) => setThreshold(parseInt(e.target.value) / 100)}
                className="w-full h-3 bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 rounded-lg cursor-pointer slider-thumb"
                style={{
                  background: `linear-gradient(to right,
                    #22c55e 0%,
                    #eab308 50%,
                    #ef4444 100%)`
                }}
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>90% (Loose)</span>
                <span>95% (Balanced)</span>
                <span>99% (Strict)</span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Lower values find more duplicates (including similar images), higher values only find exact matches
            </p>
          </div>

          {/* Scan button */}
          <Button
            onClick={handleScan}
            disabled={isFetching}
            className="w-full gap-2"
          >
            {isFetching ? (
              <>
                <span className="animate-spin">⏳</span>
                Scanning...
              </>
            ) : (
              <>
                <Scan className="w-4 h-4" />
                Scan for Duplicates
              </>
            )}
          </Button>

          {/* Progress indicator */}
          {scanProgress && scanProgress.is_scanning && (
            <div className="space-y-2 pt-2">
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">{scanProgress.message}</span>
                <Badge variant="outline" className="font-mono">
                  {scanProgress.percent}%
                </Badge>
              </div>
              <Progress value={scanProgress.percent} className="h-2" />
              {scanProgress.total > 0 && (
                <p className="text-xs text-muted-foreground text-center">
                  {scanProgress.current} of {scanProgress.total} images
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {!isLoading && data && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Scan Results</CardTitle>
              {duplicateGroups.length > 0 ? (
                <Badge variant="destructive">
                  {totalDuplicates} duplicates found
                </Badge>
              ) : (
                <Badge variant="outline" className="gap-2">
                  <CheckCircle className="w-3 h-3" />
                  No duplicates
                </Badge>
              )}
            </div>
            <CardDescription>
              Found {duplicateGroups.length} groups of similar images
            </CardDescription>
          </CardHeader>
          <CardContent>
            {duplicateGroups.length === 0 ? (
              <div className="text-center py-12">
                <CheckCircle className="w-12 h-12 mx-auto text-green-500 mb-4" />
                <p className="text-muted-foreground">
                  No duplicate images found at {(threshold * 100).toFixed(0)}% similarity threshold
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {duplicateGroups.map((group) => {
                  const [originalImage, ...duplicateImages] = group.images
                  const duplicateCount = duplicateImages.length

                  return (
                    <Card key={group.id} className="overflow-hidden">
                      <div className="p-3 md:p-4 bg-muted/50 border-b border-border flex flex-col md:flex-row items-start md:items-center justify-between gap-3 md:gap-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {(group.similarity * 100).toFixed(1)}% similar
                          </Badge>
                          <Badge variant="secondary" className="text-xs">{group.type}</Badge>
                          <span className="text-xs md:text-sm text-muted-foreground">
                            1 original + {duplicateCount} duplicate{duplicateCount !== 1 ? 's' : ''}
                          </span>
                        </div>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => {
                            setConfirmDialog({
                              open: true,
                              groupId: group.id,
                              duplicateCount,
                              duplicateImages
                            })
                          }}
                          className="gap-2"
                        >
                          <span className="hidden sm:inline">Delete {duplicateCount} Duplicate{duplicateCount !== 1 ? 's' : ''}</span>
                          <span className="sm:hidden">Delete {duplicateCount}</span>
                        </Button>
                      </div>
                      <div className="p-4">
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                          {/* Original Image - KEEP */}
                          <div key={originalImage.id} className="relative">
                            <div className="aspect-square bg-muted rounded-lg overflow-hidden border-2 border-green-500">
                              <img
                                src={
                                  originalImage.thumbnail_url
                                    ? `${API_URL}${originalImage.thumbnail_url}`
                                    : `${API_URL}/${originalImage.enhanced_path}`
                                }
                                alt={originalImage.filename}
                                className="w-full h-full object-cover"
                              />
                            </div>
                            <Badge className="absolute top-2 left-2 bg-green-600 text-white">
                              KEEP
                            </Badge>
                            <p className="text-xs text-muted-foreground mt-1 truncate">
                              {originalImage.filename}
                            </p>
                          </div>

                          {/* Duplicate Images - DELETE */}
                          {duplicateImages.map((image) => (
                            <div key={image.id} className="relative opacity-75">
                              <div className="aspect-square bg-muted rounded-lg overflow-hidden border-2 border-red-500">
                                <img
                                  src={
                                    image.thumbnail_url
                                      ? `${API_URL}${image.thumbnail_url}`
                                      : `${API_URL}/${image.enhanced_path}`
                                  }
                                  alt={image.filename}
                                  className="w-full h-full object-cover"
                                />
                              </div>
                              <Badge variant="destructive" className="absolute top-2 left-2">
                                DELETE
                              </Badge>
                              <p className="text-xs text-muted-foreground mt-1 truncate">
                                {image.filename}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </Card>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Empty state */}
      {!isLoading && !data && (
        <Card className="p-12">
          <div className="text-center space-y-4">
            <ImageIcon className="w-16 h-16 mx-auto text-muted-foreground" />
            <div>
              <p className="text-lg font-medium">No scan performed yet</p>
              <p className="text-sm text-muted-foreground mt-1">
                Configure your scan settings and click "Scan for Duplicates" to find similar images
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Confirmation Dialog */}
      <ConfirmDialog
        open={confirmDialog.open}
        onOpenChange={(open) => setConfirmDialog({ ...confirmDialog, open })}
        title="Delete Duplicates"
        description={`Are you sure you want to delete ${confirmDialog.duplicateCount} duplicate image${confirmDialog.duplicateCount !== 1 ? 's' : ''}? This action cannot be undone. The original image will be kept.`}
        confirmLabel={`Delete ${confirmDialog.duplicateCount} Duplicate${confirmDialog.duplicateCount !== 1 ? 's' : ''}`}
        cancelLabel="Cancel"
        variant="destructive"
        onConfirm={async () => {
          // Delete all duplicate images (keep the first one)
          for (const image of confirmDialog.duplicateImages) {
            try {
              await fetch(`${API_URL}/api/images/${image.id}`, {
                method: 'DELETE'
              })
            } catch (error) {
              console.error(`Failed to delete image ${image.id}:`, error)
            }
          }

          // Refresh the duplicate scan
          refetch()
        }}
      />
    </div>
  )
}
