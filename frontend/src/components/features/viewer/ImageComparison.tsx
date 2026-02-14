import React, { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ZoomIn, ZoomOut, Maximize, ArrowLeftRight } from 'lucide-react'
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch'

interface ImageComparisonProps {
  originalUrl: string
  enhancedUrl: string
  filename: string
  showEnhanced?: boolean // For mobile: true = enhanced, false = original
  onToggleView?: (showEnhanced: boolean) => void // Callback when toggle changes
  onFullscreenChange?: (isFullscreen: boolean) => void
}

/**
 * Side-by-side image comparison
 * Original (left) vs Enhanced (right)
 */
export function ImageComparison({ originalUrl, enhancedUrl, filename, showEnhanced = true, onToggleView, onFullscreenChange }: ImageComparisonProps) {
  const [isFullscreen, setIsFullscreen] = useState(false)

  const toggleFullscreen = () => {
    const newState = !isFullscreen
    if (newState) {
      document.documentElement.requestFullscreen()
    } else {
      document.exitFullscreen()
    }
    setIsFullscreen(newState)
    onFullscreenChange?.(newState)
  }

  // Expose toggle function to parent via ref or callback
  React.useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).__toggleImageFullscreen = toggleFullscreen
    return () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (window as any).__toggleImageFullscreen
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isFullscreen])

  // Image panel with zoom controls
  const ImagePanel = ({
    url,
    label,
    showMobileToggle
  }: {
    url: string
    label: string
    isEnhanced?: boolean
    showMobileToggle?: boolean
  }) => (
    <Card className="overflow-hidden">
      {/* Header with toggle buttons (mobile only) */}
      {showMobileToggle && (
        <div className="p-2 border-b bg-muted/50 border-border flex gap-1">
          <Button
            variant={!showEnhanced ? 'default' : 'ghost'}
            size="sm"
            onClick={() => onToggleView?.(false)}
            className="flex-1 h-8 text-xs"
          >
            Original
          </Button>
          <Button
            variant={showEnhanced ? 'default' : 'ghost'}
            size="sm"
            onClick={() => onToggleView?.(true)}
            className="flex-1 h-8 text-xs gap-1"
          >
            <ArrowLeftRight className="w-3 h-3" />
            Enhanced
          </Button>
        </div>
      )}
      <div className="p-1 bg-muted/30">
        <div className="relative bg-black rounded-lg overflow-hidden">
          <TransformWrapper
            initialScale={1}
            minScale={0.5}
            maxScale={5}
            doubleClick={{ mode: 'reset' }}
            wheel={{ step: 0.1 }}
          >
            {({ zoomIn, zoomOut, resetTransform }) => (
              <>
                {/* Label overlay (desktop only) */}
                {!showMobileToggle && (
                  <div className="absolute top-2 left-2 z-10">
                    <Badge variant="secondary" className="bg-black/70 text-white hover:bg-black/70">
                      {label}
                    </Badge>
                  </div>
                )}

                {/* Zoom controls overlay */}
                <div className="absolute top-2 right-2 z-10 flex gap-1">
                  <Button
                    size="icon"
                    variant="secondary"
                    className="h-8 w-8 bg-black/70 hover:bg-black/90"
                    onClick={() => zoomIn()}
                    title="Zoom in"
                  >
                    <ZoomIn className="w-4 h-4" />
                  </Button>
                  <Button
                    size="icon"
                    variant="secondary"
                    className="h-8 w-8 bg-black/70 hover:bg-black/90"
                    onClick={() => zoomOut()}
                    title="Zoom out"
                  >
                    <ZoomOut className="w-4 h-4" />
                  </Button>
                  <Button
                    size="icon"
                    variant="secondary"
                    className="h-8 w-8 bg-black/70 hover:bg-black/90"
                    onClick={() => resetTransform()}
                    title="Reset zoom"
                  >
                    <Maximize className="w-4 h-4" />
                  </Button>
                </div>

                {/* Zoomable image - all served as JPEGs now */}
                <TransformComponent
                  wrapperStyle={{ width: '100%', height: '70vh' }}
                  contentStyle={{ width: '100%', height: '100%' }}
                >
                  <img
                    src={url}
                    alt={`${label} - ${filename}`}
                    className="w-full h-full object-contain"
                    draggable={false}
                  />
                </TransformComponent>
              </>
            )}
          </TransformWrapper>
        </div>
      </div>
    </Card>
  )

  return (
    <div className="p-2 md:p-0">
      {/* Desktop: Side-by-side comparison */}
      <div className="hidden lg:grid lg:grid-cols-2 gap-2">
        <ImagePanel url={originalUrl} label="Original" />
        <ImagePanel url={enhancedUrl} label="Enhanced" isEnhanced />
      </div>

      {/* Mobile: Single image with toggle in card header */}
      <div className="lg:hidden">
        {showEnhanced ? (
          <ImagePanel url={enhancedUrl} label="Enhanced" isEnhanced showMobileToggle />
        ) : (
          <ImagePanel url={originalUrl} label="Original" showMobileToggle />
        )}
      </div>
    </div>
  )
}
