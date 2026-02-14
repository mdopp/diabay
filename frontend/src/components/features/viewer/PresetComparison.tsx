import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Check, Loader2, RefreshCw, ImageIcon, AlertCircle, Maximize2 } from 'lucide-react'
import type { ImageDetail } from '@/types/image'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { API_URL } from '@/lib/api/client'

interface PresetComparisonProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  image: ImageDetail
  onPresetSelected: (preset: string, params: any) => void
}

type Preset = {
  name: string
  label: string
  description: string
  params: {
    histogram_clip: number
    clahe_clip: number
  }
}

const presets: Preset[] = [
  {
    name: 'gentle',
    label: 'Gentle',
    description: 'Subtle enhancement, preserves natural look',
    params: { histogram_clip: 0.3, clahe_clip: 1.0 }
  },
  {
    name: 'balanced',
    label: 'Balanced',
    description: 'Recommended for most images',
    params: { histogram_clip: 0.5, clahe_clip: 1.5 }
  },
  {
    name: 'aggressive',
    label: 'Aggressive',
    description: 'Maximum detail, may over-enhance',
    params: { histogram_clip: 0.7, clahe_clip: 2.0 }
  }
]

/**
 * Preset comparison dialog
 * Shows different enhancement presets side-by-side
 */
export function PresetComparison({ open, onOpenChange, image, onPresetSelected }: PresetComparisonProps) {
  const [selectedPreset, setSelectedPreset] = useState('balanced')
  const [isApplying, setIsApplying] = useState(false)
  const [isLoadingPreviews, setIsLoadingPreviews] = useState(false)
  const [previews, setPreviews] = useState<Record<string, string> | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [fullscreenPreview, setFullscreenPreview] = useState<{ name: string; url: string; label: string } | null>(null)

  // Fetch previews when dialog opens
  useEffect(() => {
    if (open && !previews) {
      fetchPreviews()
    }
  }, [open])

  const fetchPreviews = async () => {
    setIsLoadingPreviews(true)
    setPreviewError(null)

    try {
      const response = await fetch(`${API_URL}/api/images/${image.id}/preview`, {
        method: 'POST'
      })

      if (!response.ok) {
        throw new Error('Failed to generate previews')
      }

      const data = await response.json()
      setPreviews(data.previews)
    } catch (error) {
      console.error('Failed to fetch previews:', error)
      setPreviewError('Failed to generate preview images. You can still apply presets.')
    } finally {
      setIsLoadingPreviews(false)
    }
  }

  const handleApply = async () => {
    const preset = presets.find(p => p.name === selectedPreset)
    if (!preset) return

    setIsApplying(true)
    try {
      await onPresetSelected(preset.name, preset.params)
      onOpenChange(false)
    } finally {
      setIsApplying(false)
    }
  }

  // Current preset (from image metadata)
  const currentPreset = presets.find(p =>
    p.params.histogram_clip === image.enhancement_params?.histogram_clip &&
    p.params.clahe_clip === image.enhancement_params?.clahe_clip
  )

  return (
    <>
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RefreshCw className="w-5 h-5" />
            Reprocess with Different Preset
          </DialogTitle>
          <DialogDescription>
            Choose an enhancement preset to reprocess this image
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Loading state */}
          {isLoadingPreviews && (
            <Alert>
              <Loader2 className="h-4 w-4 animate-spin" />
              <AlertDescription>Generating preview images...</AlertDescription>
            </Alert>
          )}

          {/* Error alert */}
          {previewError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{previewError}</AlertDescription>
            </Alert>
          )}

          {/* Current preset info */}
          {currentPreset && (
            <div className="bg-muted/50 rounded-lg p-3 text-sm">
              <p className="text-muted-foreground">
                Current: <span className="font-medium text-foreground">{currentPreset.label}</span>
                {' '}(Histogram: {image.enhancement_params?.histogram_clip}, CLAHE: {image.enhancement_params?.clahe_clip})
              </p>
            </div>
          )}

          {/* Preset options */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {presets.map((preset) => {
              const isCurrent = preset.name === currentPreset?.name
              const isSelected = preset.name === selectedPreset

              return (
                <Card
                  key={preset.name}
                  className={`p-4 cursor-pointer transition-all ${
                    isSelected
                      ? 'ring-2 ring-primary border-primary'
                      : 'hover:border-primary/50'
                  } ${isCurrent ? 'bg-accent/5' : ''}`}
                  onClick={() => setSelectedPreset(preset.name)}
                >
                  <div className="space-y-3">
                    {/* Header */}
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-medium flex items-center gap-2">
                          {preset.label}
                          {preset.name === 'balanced' && (
                            <Badge variant="secondary" className="text-xs">Recommended</Badge>
                          )}
                          {isCurrent && (
                            <Badge variant="outline" className="text-xs">Current</Badge>
                          )}
                        </h3>
                      </div>
                      {isSelected && (
                        <div className="w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                          <Check className="w-3 h-3 text-primary-foreground" />
                        </div>
                      )}
                    </div>

                    {/* Description */}
                    <p className="text-xs text-muted-foreground">
                      {preset.description}
                    </p>

                    {/* Parameters */}
                    <div className="space-y-1 pt-2 border-t border-border">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Histogram:</span>
                        <span className="font-mono">{preset.params.histogram_clip}</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">CLAHE:</span>
                        <span className="font-mono">{preset.params.clahe_clip}</span>
                      </div>
                    </div>

                    {/* Preview image */}
                    <div className="aspect-video bg-muted rounded-md flex items-center justify-center overflow-hidden relative group">
                      {isLoadingPreviews ? (
                        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                      ) : previews && previews[preset.name] ? (
                        <>
                          <img
                            src={`${API_URL}/${previews[preset.name]}`}
                            alt={`${preset.label} preview`}
                            className="w-full h-full object-contain"
                          />
                          <Button
                            size="icon"
                            variant="secondary"
                            className="absolute top-2 right-2 h-8 w-8 bg-black/70 hover:bg-black/90 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={() => setFullscreenPreview({
                              name: preset.name,
                              url: `${API_URL}/${previews[preset.name]}`,
                              label: preset.label
                            })}
                            title="View fullscreen"
                          >
                            <Maximize2 className="w-4 h-4" />
                          </Button>
                        </>
                      ) : isCurrent ? (
                        <>
                          <img
                            src={`${API_URL}/${image.enhanced_path}`}
                            alt="Current version"
                            className="w-full h-full object-contain"
                          />
                          <Button
                            size="icon"
                            variant="secondary"
                            className="absolute top-2 right-2 h-8 w-8 bg-black/70 hover:bg-black/90 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={() => setFullscreenPreview({
                              name: preset.name,
                              url: `${API_URL}/${image.enhanced_path}`,
                              label: `${preset.label} (Current)`
                            })}
                            title="View fullscreen"
                          >
                            <Maximize2 className="w-4 h-4" />
                          </Button>
                        </>
                      ) : (
                        <div className="flex flex-col items-center gap-2">
                          <ImageIcon className="w-8 h-8 text-muted-foreground" />
                          <span className="text-xs text-muted-foreground text-center px-2">
                            Click Apply to process
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              )
            })}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-4 border-t">
            <div className="text-sm text-muted-foreground">
              {selectedPreset !== currentPreset?.name && (
                <span>This will replace the current enhancement</span>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isApplying}
              >
                Cancel
              </Button>
              <Button
                onClick={handleApply}
                disabled={isApplying || selectedPreset === currentPreset?.name}
              >
                {isApplying ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  'Apply Preset'
                )}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>

    {/* Fullscreen preview dialog */}
    {fullscreenPreview && (
      <Dialog open={!!fullscreenPreview} onOpenChange={() => setFullscreenPreview(null)}>
        <DialogContent className="max-w-[95vw] max-h-[95vh] p-0">
          <div className="relative bg-black rounded-lg overflow-hidden" style={{ height: '90vh' }}>
            <div className="absolute top-4 left-4 z-10">
              <Badge variant="secondary" className="bg-black/70 text-white">
                {fullscreenPreview.label}
              </Badge>
            </div>
            <Button
              size="icon"
              variant="secondary"
              className="absolute top-4 right-4 z-10 h-10 w-10 bg-black/70 hover:bg-black/90"
              onClick={() => setFullscreenPreview(null)}
              title="Close"
            >
              <Maximize2 className="w-5 h-5" />
            </Button>
            <img
              src={fullscreenPreview.url}
              alt={fullscreenPreview.label}
              className="w-full h-full object-contain"
            />
          </div>
        </DialogContent>
      </Dialog>
    )}
  </>
  )
}
