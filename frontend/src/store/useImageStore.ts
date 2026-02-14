import { create } from 'zustand'
import type { Image } from '@/types/image'

/**
 * Image gallery store
 */

interface ImageFilters {
  tags: string[]
  search: string
  dateRange?: [Date, Date]
}

interface ImageStore {
  images: Image[]
  filteredImages: Image[]
  filters: ImageFilters
  selectedIds: Set<number>
  newImageIds: Set<number>

  // Actions
  setImages: (images: Image[]) => void
  setFilters: (filters: Partial<ImageFilters>) => void
  applyFilters: () => void
  toggleSelection: (id: number) => void
  selectAll: () => void
  clearSelection: () => void
  markAsNew: (id: number) => void
  clearNewFlags: () => void
}

export const useImageStore = create<ImageStore>((set, get) => ({
  images: [],
  filteredImages: [],
  filters: {
    tags: [],
    search: '',
  },
  selectedIds: new Set(),
  newImageIds: new Set(),

  setImages: (images: Image[]) => {
    set({ images })
    get().applyFilters()
  },

  setFilters: (newFilters: Partial<ImageFilters>) => {
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
    }))
    get().applyFilters()
  },

  applyFilters: () => {
    const { images, filters } = get()

    let filtered = images

    // Filter by tags (AND logic)
    if (filters.tags.length > 0) {
      filtered = filtered.filter((img) =>
        filters.tags.every((tag) =>
          img.filename.toLowerCase().includes(tag.toLowerCase())
        )
      )
    }

    // Filter by search
    if (filters.search) {
      const searchLower = filters.search.toLowerCase()
      filtered = filtered.filter((img) =>
        img.filename.toLowerCase().includes(searchLower)
      )
    }

    // Filter by date range
    if (filters.dateRange) {
      const [start, end] = filters.dateRange
      filtered = filtered.filter((img) => {
        const imgDate = new Date(img.created_at)
        return imgDate >= start && imgDate <= end
      })
    }

    set({ filteredImages: filtered })
  },

  toggleSelection: (id: number) => {
    set((state) => {
      const newSelection = new Set(state.selectedIds)
      if (newSelection.has(id)) {
        newSelection.delete(id)
      } else {
        newSelection.add(id)
      }
      return { selectedIds: newSelection }
    })
  },

  selectAll: () => {
    set((state) => ({
      selectedIds: new Set(state.filteredImages.map((img) => img.id)),
    }))
  },

  clearSelection: () => {
    set({ selectedIds: new Set() })
  },

  markAsNew: (id: number) => {
    set((state) => ({
      newImageIds: new Set(state.newImageIds).add(id),
    }))
  },

  clearNewFlags: () => {
    set({ newImageIds: new Set() })
  },
}))
