import { Outlet } from 'react-router-dom'
import { DesktopSidebar } from '@/components/features/navigation/DesktopSidebar'
import { MobileBottomNav } from '@/components/features/navigation/MobileBottomNav'

/**
 * Main application layout
 * - Desktop: Sidebar (240px) + Content
 * - Mobile: Content + Bottom Nav (64px)
 */
export function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop Sidebar - hidden on mobile */}
      <DesktopSidebar className="hidden md:flex" />

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto pb-16 md:pb-0">
        <Outlet />
      </main>

      {/* Mobile Bottom Navigation - hidden on desktop */}
      <MobileBottomNav className="md:hidden" />
    </div>
  )
}
