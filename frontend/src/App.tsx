import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useWebSocket } from '@/hooks/useWebSocket'
import { AppLayout } from '@/components/layout/AppLayout'
import { GalleryPage } from '@/pages/GalleryPage'
import { ImageDetailPage } from '@/pages/ImageDetailPage'
import { DuplicatesPage } from '@/pages/DuplicatesPage'
import { StatsPage } from '@/pages/StatsPage'
import { HelpPage } from '@/pages/HelpPage'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30000, // 30 seconds
    },
  },
})

function AppContent() {
  // Initialize WebSocket connection
  useWebSocket()

  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<GalleryPage />} />
        <Route path="duplicates" element={<DuplicatesPage />} />
        <Route path="stats" element={<StatsPage />} />
        <Route path="help" element={<HelpPage />} />
      </Route>
      {/* Image detail page - standalone layout */}
      <Route path="/image/:id" element={<ImageDetailPage />} />
    </Routes>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <AppContent />
      </Router>
    </QueryClientProvider>
  )
}

export default App
