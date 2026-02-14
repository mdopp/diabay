import { NavLink } from 'react-router-dom'
import { StatusIndicator } from './StatusIndicator'
import { cn } from '@/lib/utils'
import { Images, Trash2, BarChart3, HelpCircle } from 'lucide-react'

interface DesktopSidebarProps {
  className?: string
}

/**
 * Desktop sidebar navigation (≥768px)
 * Fixed left sidebar with navigation items and status indicator
 */
export function DesktopSidebar({ className }: DesktopSidebarProps) {
  const navItems = [
    { to: '/', icon: Images, label: 'Gallery' },
    { to: '/duplicates', icon: Trash2, label: 'Cleanup' },
    { to: '/stats', icon: BarChart3, label: 'Statistics' },
    { to: '/help', icon: HelpCircle, label: 'Help' },
  ]

  return (
    <aside
      className={cn(
        'w-60 flex-col border-r border-border bg-card/50 backdrop-blur-sm',
        className
      )}
    >
      {/* Header */}
      <div className="p-6 border-b border-border">
        <h1 className="text-2xl font-bold gradient-text">DiaBay</h1>
        <p className="text-xs text-muted-foreground mt-1">Photo Digitization</p>
      </div>

      {/* Status Indicator */}
      <div className="p-4 border-b border-border">
        <StatusIndicator />
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-accent/10 hover:text-foreground'
              )
            }
          >
            <item.icon className="w-5 h-5" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border text-xs text-muted-foreground">
        <p>v1.0.0 • React + FastAPI</p>
      </div>
    </aside>
  )
}
