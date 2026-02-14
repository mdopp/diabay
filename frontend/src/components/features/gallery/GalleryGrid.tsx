import { useNavigate } from 'react-router-dom'
import { GalleryItem } from './GalleryItem'
import type { Image } from '@/types/image'
import { useState } from 'react'

interface GalleryGridProps {
  images: Image[]
  isLoading?: boolean
}

/**
 * Responsive grid of gallery items
 * 2 columns (mobile) → 3 (sm) → 4 (md) → 6 (lg)
 */
export function GalleryGrid({ images, isLoading }: GalleryGridProps) {
  const navigate = useNavigate()
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  const toggleSelection = (id: number) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const handleImageClick = (id: number) => {
    navigate(`/image/${id}`)
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="aspect-square bg-muted animate-pulse rounded-lg" />
        ))}
      </div>
    )
  }

  if (images.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground text-lg">No images found</p>
        <p className="text-muted-foreground text-sm mt-2">
          Place TIFF files in the input directory to start processing
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Selection toolbar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-4 p-4 bg-card border border-border rounded-lg">
          <span className="text-sm text-muted-foreground">
            {selectedIds.size} selected
          </span>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-sm text-accent hover:underline"
          >
            Clear selection
          </button>
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {images.map((image) => (
          <GalleryItem
            key={image.id}
            image={image}
            isSelected={selectedIds.has(image.id)}
            onSelect={toggleSelection}
            onClick={handleImageClick}
          />
        ))}
      </div>
    </div>
  )
}
