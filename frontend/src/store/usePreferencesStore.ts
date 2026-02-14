import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * User preferences store - persisted to localStorage
 */

type ThumbnailSize = 'sm' | 'md' | 'lg'
type ViewMode = 'grid' | 'list'

interface PreferencesStore {
  theme: 'dark' // Only dark theme for now
  thumbnailSize: ThumbnailSize
  sidebarCollapsed: boolean
  viewMode: ViewMode
  autoPlaySlideshow: boolean

  // Actions
  setThumbnailSize: (size: ThumbnailSize) => void
  toggleSidebar: () => void
  setViewMode: (mode: ViewMode) => void
  setAutoPlaySlideshow: (value: boolean) => void
}

export const usePreferencesStore = create<PreferencesStore>()(
  persist(
    (set) => ({
      theme: 'dark',
      thumbnailSize: 'md',
      sidebarCollapsed: false,
      viewMode: 'grid',
      autoPlaySlideshow: false,

      setThumbnailSize: (size: ThumbnailSize) => {
        set({ thumbnailSize: size })
      },

      toggleSidebar: () => {
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }))
      },

      setViewMode: (mode: ViewMode) => {
        set({ viewMode: mode })
      },

      setAutoPlaySlideshow: (value: boolean) => {
        set({ autoPlaySlideshow: value })
      },
    }),
    {
      name: 'diabay-preferences',
    }
  )
)
