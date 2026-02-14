import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useImageDetail, useImages, useDeleteImage } from '@/hooks/useImages'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, ChevronLeft, ChevronRight, Download, RotateCw, Trash2, Sliders, Undo2, Maximize2, Menu } from 'lucide-react'
import { ImageComparison } from '@/components/features/viewer/ImageComparison'
import { ImageMetadataPanel } from '@/components/features/viewer/ImageMetadataPanel'
import { PresetComparison } from '@/components/features/viewer/PresetComparison'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { useKeyboardNav } from '@/hooks/useKeyboardNav'
import { useSwipeGesture } from '@/hooks/useSwipeGesture'
import { useQueryClient } from '@tanstack/react-query'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

export function ImageDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const imageId = parseInt(id || '0', 10)
  const queryClient = useQueryClient()

  const { data: image, isLoading, error } = useImageDetail(imageId)
  const { data: imagesResponse } = useImages({ limit: 1000 }) // Fetch all images for navigation
  const deleteMutation = useDeleteImage()

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showErrorDialog, setShowErrorDialog] = useState(false)
  const [showPresetDialog, setShowPresetDialog] = useState(false)
  const [showMobileMenu, setShowMobileMenu] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [showEnhanced, setShowEnhanced] = useState(true) // Mobile: true = enhanced, false = original

  // Find current image index and get prev/next IDs
  const images = imagesResponse?.images || []
  const currentIndex = images.findIndex((img) => img.id === imageId)
  const prevImage = currentIndex > 0 ? images[currentIndex - 1] : null
  const nextImage = currentIndex < images.length - 1 ? images[currentIndex + 1] : null

  // Keyboard navigation
  useKeyboardNav({
    onPrevious: () => prevImage && navigate(`/image/${prevImage.id}`),
    onNext: () => nextImage && navigate(`/image/${nextImage.id}`),
    onEscape: () => navigate('/'),
    enabled: !isLoading && !error,
  })

  // Touch swipe navigation for mobile
  useSwipeGesture({
    onSwipeLeft: () => nextImage && navigate(`/image/${nextImage.id}`),
    onSwipeRight: () => prevImage && navigate(`/image/${prevImage.id}`),
    enabled: !isLoading && !error,
  })

  // Actions
  const handleDownload = () => {
    if (!image) return
    const url = `http://localhost:8000/${image.enhanced_path}`
    const link = document.createElement('a')
    link.href = url
    link.download = image.filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleRotate = async () => {
    if (!image) return

    try {
      // Call rotation API (90 degrees clockwise)
      await fetch(`http://localhost:8000/api/images/${imageId}/rotate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ degrees: 90 })
      })

      // Force reload the page to show rotated image
      window.location.reload()
    } catch (error) {
      console.error('Failed to rotate image:', error)
      setErrorMessage('Failed to rotate image. Please try again.')
      setShowErrorDialog(true)
    }
  }

  const handleDeleteClick = () => {
    if (!image) return
    setShowDeleteConfirm(true)
  }

  const handleDeleteConfirm = async () => {
    if (!image) return

    try {
      await deleteMutation.mutateAsync(imageId)
      // Navigate to next or previous image, or back to gallery
      if (nextImage) {
        navigate(`/image/${nextImage.id}`)
      } else if (prevImage) {
        navigate(`/image/${prevImage.id}`)
      } else {
        navigate('/')
      }
    } catch (error) {
      console.error('Failed to delete image:', error)
      setErrorMessage('Failed to delete image. Please try again.')
      setShowErrorDialog(true)
    }
  }

  const handlePresetSelected = async (preset: string, params: any) => {
    try {
      // Call reprocess API
      const response = await fetch(`http://localhost:8000/api/images/${imageId}/reprocess`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset, ...params })
      })

      if (!response.ok) {
        throw new Error('Reprocess failed')
      }

      // Invalidate queries to reload image data
      queryClient.invalidateQueries({ queryKey: ['image', imageId] })
      queryClient.invalidateQueries({ queryKey: ['images'] })

      // Force reload to show new image
      window.location.reload()
    } catch (error) {
      console.error('Failed to reprocess image:', error)
      setErrorMessage('Failed to reprocess image. Please try again.')
      setShowErrorDialog(true)
    }
  }

  const handleUseOriginal = async () => {
    if (!image) return

    try {
      const response = await fetch(`http://localhost:8000/api/images/${imageId}/use-original`, {
        method: 'POST'
      })

      if (!response.ok) {
        throw new Error('Use original failed')
      }

      // Invalidate queries and reload
      queryClient.invalidateQueries({ queryKey: ['image', imageId] })
      queryClient.invalidateQueries({ queryKey: ['images'] })
      window.location.reload()
    } catch (error) {
      console.error('Failed to use original:', error)
      setErrorMessage('Failed to revert to original. Please try again.')
      setShowErrorDialog(true)
    }
  }

  const handleToggleFullscreen = () => {
    // Call the global toggle function exposed by ImageComparison
    if ((window as any).__toggleImageFullscreen) {
      (window as any).__toggleImageFullscreen()
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-32 bg-muted rounded" />
          <div className="h-[600px] bg-muted rounded" />
        </div>
      </div>
    )
  }

  if (error || !image) {
    return (
      <div className="container mx-auto p-6">
        <Card className="p-12 text-center">
          <p className="text-muted-foreground text-lg">Image not found</p>
          <Button
            variant="outline"
            onClick={() => navigate('/')}
            className="mt-4"
          >
            Back to Gallery
          </Button>
        </Card>
      </div>
    )
  }

  const enhancedUrl = `http://localhost:8000/${image.enhanced_path}`

  // Use preview URL for TIFF originals (much faster than 100MB TIFF)
  // Falls back to original_path, then enhanced if neither available
  const originalUrl = image.original_preview_url
    ? `http://localhost:8000${image.original_preview_url}`
    : image.original_path
      ? `http://localhost:8000/${image.original_path}`
      : enhancedUrl

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <div className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-2 md:px-4 py-2 md:py-3 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 md:gap-4 min-w-0 flex-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/')}
              className="gap-1 md:gap-2 shrink-0"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="hidden sm:inline">Gallery</span>
            </Button>
            <div className="text-xs md:text-sm min-w-0">
              <p className="font-medium truncate">{image.filename}</p>
              <p className="text-muted-foreground text-xs hidden md:block">
                {image.width} × {image.height}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1 md:gap-2 shrink-0">
            {/* Navigation arrows */}
            <Button
              variant="ghost"
              size="icon"
              disabled={!prevImage}
              onClick={() => prevImage && navigate(`/image/${prevImage.id}`)}
              title="Previous (←)"
            >
              <ChevronLeft className="w-5 h-5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              disabled={!nextImage}
              onClick={() => nextImage && navigate(`/image/${nextImage.id}`)}
              title="Next (→)"
            >
              <ChevronRight className="w-5 h-5" />
            </Button>

            <div className="w-px h-6 bg-border mx-1 md:mx-2 hidden sm:block" />

            <Button
              variant="ghost"
              size="icon"
              title="Download"
              onClick={handleDownload}
              className="hidden md:flex"
            >
              <Download className="w-4 md:w-5 h-4 md:h-5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              title="Rotate 90°"
              onClick={handleRotate}
              className="hidden sm:flex"
            >
              <RotateCw className="w-4 md:w-5 h-4 md:h-5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              title="Reprocess with preset"
              onClick={() => setShowPresetDialog(true)}
              className="hidden sm:flex"
            >
              <Sliders className="w-4 md:w-5 h-4 md:h-5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              title="Use original (remove enhancement)"
              onClick={handleUseOriginal}
              className="hidden md:flex"
            >
              <Undo2 className="w-4 md:w-5 h-4 md:h-5" />
            </Button>

            <div className="w-px h-6 bg-border mx-1 md:mx-2 hidden md:block" />

            <Button
              variant="ghost"
              size="icon"
              title="Fullscreen"
              onClick={handleToggleFullscreen}
              className="hidden md:flex"
            >
              <Maximize2 className="w-4 md:w-5 h-4 md:h-5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              title="Delete"
              onClick={handleDeleteClick}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="w-4 md:w-5 h-4 md:h-5" />
            </Button>

            {/* Mobile menu button */}
            <Button
              variant="ghost"
              size="icon"
              title="Menu"
              onClick={() => setShowMobileMenu(true)}
              className="md:hidden"
            >
              <Menu className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Image comparison - takes most space */}
        <div className="flex-1 overflow-auto">
          <ImageComparison
            originalUrl={originalUrl}
            enhancedUrl={enhancedUrl}
            filename={image.filename}
            showEnhanced={showEnhanced}
            onToggleView={setShowEnhanced}
          />
        </div>

        {/* Metadata panel at bottom - full panel on desktop, tags only on mobile */}
        <div className="border-t border-border overflow-auto max-h-64">
          <div className="hidden md:block">
            <ImageMetadataPanel image={image} />
          </div>
          {/* Mobile: Show only tags */}
          <div className="md:hidden p-4">
            <div className="flex flex-wrap gap-2">
              {image.tags && image.tags.length > 0 ? (
                image.tags.map((tag, index) => (
                  <Badge key={index} variant="outline" className="text-xs">
                    {tag.tag}
                  </Badge>
                ))
              ) : (
                <p className="text-xs text-muted-foreground">No tags</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={showDeleteConfirm}
        onOpenChange={setShowDeleteConfirm}
        title="Delete Image"
        description={`Are you sure you want to delete "${image?.filename}"? This action cannot be undone.`}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="destructive"
        onConfirm={handleDeleteConfirm}
      />

      {/* Error Dialog */}
      <AlertDialog open={showErrorDialog} onOpenChange={setShowErrorDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Error</AlertDialogTitle>
            <AlertDialogDescription>{errorMessage}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction onClick={() => setShowErrorDialog(false)}>
              OK
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Preset Comparison Dialog */}
      {image && (
        <PresetComparison
          open={showPresetDialog}
          onOpenChange={setShowPresetDialog}
          image={image}
          onPresetSelected={handlePresetSelected}
        />
      )}

      {/* Mobile Menu Sheet */}
      <Sheet open={showMobileMenu} onOpenChange={setShowMobileMenu}>
        <SheetContent side="right" className="w-[300px] sm:w-[400px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Image Details & Actions</SheetTitle>
            <SheetDescription>View metadata and perform actions</SheetDescription>
          </SheetHeader>

          <div className="mt-6 space-y-6">
            {/* Actions Section */}
            <div className="space-y-2">
              <h3 className="font-medium text-sm text-muted-foreground">Actions</h3>
              <div className="space-y-2">
                <Button
                  variant="outline"
                  className="w-full justify-start gap-2"
                  onClick={() => {
                    handleDownload()
                    setShowMobileMenu(false)
                  }}
                >
                  <Download className="w-4 h-4" />
                  Download Image
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start gap-2"
                  onClick={() => {
                    handleRotate()
                    setShowMobileMenu(false)
                  }}
                >
                  <RotateCw className="w-4 h-4" />
                  Rotate 90°
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start gap-2"
                  onClick={() => {
                    setShowPresetDialog(true)
                    setShowMobileMenu(false)
                  }}
                >
                  <Sliders className="w-4 h-4" />
                  Reprocess with Preset
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start gap-2"
                  onClick={() => {
                    handleUseOriginal()
                    setShowMobileMenu(false)
                  }}
                >
                  <Undo2 className="w-4 h-4" />
                  Use Original
                </Button>
              </div>
            </div>

            {/* Image Details Section */}
            <div className="space-y-3">
              <h3 className="font-medium text-sm text-muted-foreground">Image Details</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Filename:</span>
                  <span className="font-mono text-xs">{image.filename}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Dimensions:</span>
                  <span>{image.width} × {image.height}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Created:</span>
                  <span className="text-xs">{new Date(image.created_at).toLocaleString()}</span>
                </div>
              </div>
            </div>

            {/* Enhancement Details Section */}
            {image.enhancement_params && (
              <div className="space-y-3">
                <h3 className="font-medium text-sm text-muted-foreground">Enhancement Details</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Histogram Clip:</span>
                    <span className="font-medium">{image.enhancement_params.histogram_clip}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">CLAHE Clip:</span>
                    <span className="font-medium">{image.enhancement_params.clahe_clip}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Face Detected:</span>
                    <Badge variant={image.enhancement_params.face_detected ? 'default' : 'secondary'}>
                      {image.enhancement_params.face_detected ? 'Yes' : 'No'}
                    </Badge>
                  </div>
                </div>
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
