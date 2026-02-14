import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Search, X } from 'lucide-react'

interface GalleryFiltersProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  onClearFilters: () => void
}

/**
 * Filter bar for gallery
 * Search, tag filters, date range
 */
export function GalleryFilters({
  searchQuery,
  onSearchChange,
  onClearFilters,
}: GalleryFiltersProps) {
  const hasActiveFilters = searchQuery.length > 0

  return (
    <div className="flex flex-col sm:flex-row gap-4">
      {/* Search */}
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          type="text"
          placeholder="Search by filename..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Clear filters */}
      {hasActiveFilters && (
        <Button
          variant="outline"
          size="sm"
          onClick={onClearFilters}
          className="gap-2"
        >
          <X className="w-4 h-4" />
          Clear
        </Button>
      )}
    </div>
  )
}
