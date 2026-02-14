import { useState, useEffect, useRef } from 'react'
import { useImages } from '@/hooks/useImages'
import { useStatsStore } from '@/store/useStatsStore'
import { GalleryGrid } from '@/components/features/gallery/GalleryGrid'
import { GalleryFilters } from '@/components/features/gallery/GalleryFilters'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'

export function GalleryPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)
  const [pullDistance, setPullDistance] = useState(0)
  const limit = 50
  const startY = useRef(0)
  const containerRef = useRef<HTMLDivElement>(null)

  // Listen for deleted images via WebSocket
  const lastDeletedImageId = useStatsStore((state) => state.lastDeletedImageId)

  // Fetch images with pagination
  const { data, isLoading, refetch, isFetching } = useImages({
    skip: (page - 1) * limit,
    limit,
  })

  // Auto-refresh gallery when image is deleted
  useEffect(() => {
    if (lastDeletedImageId !== null) {
      console.log('[GalleryPage] Image deleted, refreshing gallery:', lastDeletedImageId)
      refetch()
    }
  }, [lastDeletedImageId, refetch])

  // Pull-to-refresh for mobile
  useEffect(() => {
    const handleTouchStart = (e: TouchEvent) => {
      if (window.scrollY === 0) {
        startY.current = e.touches[0].clientY
      }
    }

    const handleTouchMove = (e: TouchEvent) => {
      if (window.scrollY > 0) return

      const currentY = e.touches[0].clientY
      const diff = currentY - startY.current

      if (diff > 0 && diff < 100) {
        setPullDistance(diff)
      } else if (diff >= 100) {
        setPullDistance(100)
      }
    }

    const handleTouchEnd = () => {
      if (pullDistance >= 100) {
        refetch()
      }
      setPullDistance(0)
    }

    window.addEventListener('touchstart', handleTouchStart)
    window.addEventListener('touchmove', handleTouchMove)
    window.addEventListener('touchend', handleTouchEnd)

    return () => {
      window.removeEventListener('touchstart', handleTouchStart)
      window.removeEventListener('touchmove', handleTouchMove)
      window.removeEventListener('touchend', handleTouchEnd)
    }
  }, [pullDistance, refetch])

  // Filter images by search query (client-side for now)
  const filteredImages = data?.images.filter((img) =>
    img.filename.toLowerCase().includes(searchQuery.toLowerCase())
  ) ?? []

  const totalImages = data?.total ?? 0
  const totalPages = Math.ceil(totalImages / limit)

  const handleClearFilters = () => {
    setSearchQuery('')
  }

  return (
    <div ref={containerRef} className="container mx-auto p-4 md:p-6 space-y-4 md:space-y-6 pb-20 md:pb-6">
      {/* Pull-to-refresh indicator */}
      {pullDistance > 0 && (
        <div
          className="fixed top-0 left-0 right-0 flex items-center justify-center bg-accent/10 transition-all z-50"
          style={{ height: `${pullDistance}px` }}
        >
          <RefreshCw
            className={`w-6 h-6 text-accent transition-transform ${
              pullDistance >= 100 ? 'animate-spin' : ''
            }`}
            style={{ transform: `rotate(${pullDistance * 3.6}deg)` }}
          />
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl md:text-3xl font-bold">Gallery</h1>
          <p className="text-sm md:text-base text-muted-foreground mt-1">
            {totalImages} {totalImages === 1 ? 'image' : 'images'} processed
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          className="gap-2 shrink-0"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">Refresh</span>
        </Button>
      </div>

      {/* Filters */}
      <GalleryFilters
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onClearFilters={handleClearFilters}
      />

      {/* Grid */}
      <GalleryGrid images={filteredImages} isLoading={isLoading} />

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-6">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1 || isLoading}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground px-4">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages || isLoading}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}
