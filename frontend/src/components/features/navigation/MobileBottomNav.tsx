import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { Images, Trash2, BarChart3, Menu } from 'lucide-react'

interface MobileBottomNavProps {
  className?: string
}

/**
 * Mobile bottom navigation (<768px)
 * Sticky bottom bar with 4 main navigation items
 */
export function MobileBottomNav({ className }: MobileBottomNavProps) {
  const navItems = [
    { to: '/', icon: Images, label: 'Gallery' },
    { to: '/duplicates', icon: Trash2, label: 'Cleanup' },
    { to: '/stats', icon: BarChart3, label: 'Stats' },
    { to: '/help', icon: Menu, label: 'More' },
  ]

  return (
    <nav
      className={cn(
        'fixed bottom-0 left-0 right-0 h-16 bg-card/95 backdrop-blur-md border-t border-border',
        'flex items-center justify-around px-2',
        'safe-area-inset-bottom', // PWA safe area
        className
      )}
    >
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            cn(
              'flex flex-col items-center justify-center gap-1 px-4 py-2 rounded-md',
              'min-w-[64px] min-h-[48px]', // Touch target size
              'transition-colors',
              isActive
                ? 'text-accent'
                : 'text-muted-foreground active:text-foreground'
            )
          }
        >
          <item.icon className="w-6 h-6" />
          <span className="text-[10px] font-medium">{item.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
