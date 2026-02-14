import { useEffect, useRef } from 'react'

interface UseSwipeGestureOptions {
  onSwipeLeft?: () => void
  onSwipeRight?: () => void
  threshold?: number // Minimum distance in pixels to trigger swipe
  enabled?: boolean
}

/**
 * Hook for detecting swipe gestures on touch devices
 */
export function useSwipeGesture({
  onSwipeLeft,
  onSwipeRight,
  threshold = 120, // Increased from 50 to 120 for less sensitivity
  enabled = true,
}: UseSwipeGestureOptions) {
  const touchStartX = useRef(0)
  const touchStartY = useRef(0)
  const touchEndX = useRef(0)
  const touchEndY = useRef(0)
  const touchStartElement = useRef<EventTarget | null>(null)

  useEffect(() => {
    if (!enabled) return

    const handleTouchStart = (e: TouchEvent) => {
      // Ignore swipes that start on image containers (for zoom/pan)
      const target = e.target as HTMLElement
      if (target.closest('.react-transform-wrapper') || target.closest('img')) {
        touchStartElement.current = null
        return
      }

      touchStartElement.current = e.target
      touchStartX.current = e.touches[0].clientX
      touchStartY.current = e.touches[0].clientY
    }

    const handleTouchMove = (e: TouchEvent) => {
      if (!touchStartElement.current) return
      touchEndX.current = e.touches[0].clientX
      touchEndY.current = e.touches[0].clientY
    }

    const handleTouchEnd = () => {
      if (!touchStartElement.current) return

      const deltaX = touchEndX.current - touchStartX.current
      const deltaY = touchEndY.current - touchStartY.current

      // Only trigger if horizontal swipe is dominant AND exceeds threshold
      // Also require vertical movement to be less than 60% of horizontal
      if (
        Math.abs(deltaX) > threshold &&
        Math.abs(deltaX) > Math.abs(deltaY) * 1.5
      ) {
        if (deltaX > 0) {
          onSwipeRight?.()
        } else {
          onSwipeLeft?.()
        }
      }

      // Reset
      touchStartX.current = 0
      touchStartY.current = 0
      touchEndX.current = 0
      touchEndY.current = 0
      touchStartElement.current = null
    }

    window.addEventListener('touchstart', handleTouchStart)
    window.addEventListener('touchmove', handleTouchMove)
    window.addEventListener('touchend', handleTouchEnd)

    return () => {
      window.removeEventListener('touchstart', handleTouchStart)
      window.removeEventListener('touchmove', handleTouchMove)
      window.removeEventListener('touchend', handleTouchEnd)
    }
  }, [onSwipeLeft, onSwipeRight, threshold, enabled])
}
