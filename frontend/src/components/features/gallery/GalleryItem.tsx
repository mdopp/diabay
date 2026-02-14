import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { Image } from '@/types/image'
import { Check } from 'lucide-react'
import { getAssetUrl } from '@/lib/api/client'

interface GalleryItemProps {
  image: Image
  isSelected?: boolean
  onSelect?: (id: number) => void
  onClick?: (id: number) => void
}

/**
 * Gallery thumbnail item
 * Shows image thumbnail with filename and status
 */
export function GalleryItem({ image, isSelected, onSelect, onClick }: GalleryItemProps) {
  // Use thumbnail if available, otherwise fall back to full image
  const thumbnailUrl = image.thumbnail_url
    ? getAssetUrl(image.thumbnail_url)
    : getAssetUrl(image.enhanced_path)

  return (
    <Card
      className={`group relative overflow-hidden cursor-pointer transition-all hover:ring-2 hover:ring-accent ${
        isSelected ? 'ring-2 ring-accent' : ''
      }`}
      onClick={() => onClick?.(image.id)}
    >
      {/* Checkbox for selection */}
      {onSelect && (
        <button
          className="absolute top-2 left-2 z-10 w-6 h-6 rounded-md bg-card/80 backdrop-blur-sm border border-border flex items-center justify-center hover:bg-accent hover:border-accent transition-colors"
          onClick={(e) => {
            e.stopPropagation()
            onSelect(image.id)
          }}
        >
          {isSelected && <Check className="w-4 h-4 text-accent-foreground" />}
        </button>
      )}

      {/* Status badge */}
      {image.status !== 'complete' && (
        <Badge
          variant="secondary"
          className="absolute top-2 right-2 z-10 text-xs"
        >
          {image.status}
        </Badge>
      )}

      {/* Image */}
      <div className="aspect-square bg-muted relative overflow-hidden">
        <img
          src={thumbnailUrl}
          alt={image.filename}
          className="w-full h-full object-cover transition-transform group-hover:scale-105"
          loading="lazy"
        />
      </div>

      {/* Filename overlay */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2">
        <p className="text-xs text-white truncate">{image.filename}</p>
        <p className="text-[10px] text-white/60">
          {image.width} × {image.height}
        </p>
      </div>
    </Card>
  )
}
