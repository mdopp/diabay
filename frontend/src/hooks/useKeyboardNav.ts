import { useEffect } from 'react'

interface UseKeyboardNavOptions {
  onPrevious?: () => void
  onNext?: () => void
  onEscape?: () => void
  enabled?: boolean
}

/**
 * Hook for keyboard navigation
 * Arrow keys: Navigate prev/next
 * Escape: Close/go back
 */
export function useKeyboardNav({
  onPrevious,
  onNext,
  onEscape,
  enabled = true,
}: UseKeyboardNavOptions) {
  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignore if user is typing in an input
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement
      ) {
        return
      }

      switch (event.key) {
        case 'ArrowLeft':
          event.preventDefault()
          onPrevious?.()
          break
        case 'ArrowRight':
          event.preventDefault()
          onNext?.()
          break
        case 'Escape':
          event.preventDefault()
          onEscape?.()
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onPrevious, onNext, onEscape, enabled])
}
