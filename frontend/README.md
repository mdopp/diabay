# DiaBay Frontend

Modern TypeScript React frontend for the DiaBay analog slide digitization system.

## Tech Stack

- **React 18.3** - UI framework
- **TypeScript 5.3** - Type safety
- **Vite 5** - Build tool & dev server
- **Tailwind CSS 3.4** - Utility-first styling
- **shadcn/ui** - Accessible component primitives
- **React Query 5** - Server state management
- **Zustand 4.5** - Client state management
- **React Router v6** - Routing
- **lucide-react** - Icons

## Development

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:5173)
npm run dev

# Type check
npm run type-check

# Build for production
npm run build

# Preview production build
npm run preview
```

## Architecture

```
src/
├── components/
│   ├── ui/              # shadcn/ui primitives (button, card, etc.)
│   ├── features/        # Feature-specific components
│   └── layout/          # Layout components
├── pages/               # Route pages
├── hooks/               # Custom React hooks
├── lib/
│   ├── api/             # API client & endpoints
│   ├── websocket/       # WebSocket manager
│   └── utils/           # Utility functions
├── store/               # Zustand stores
├── types/               # TypeScript type definitions
└── styles/              # Global styles
```

## Features

- ✅ Real-time status updates via WebSocket
- ✅ Virtual scrolling for 1000+ images
- ✅ Mobile-responsive (desktop sidebar, mobile bottom nav)
- ✅ PWA support (installable on mobile)
- ✅ Dark theme with glassmorphism effects
- ✅ Touch gestures (swipe, pinch-to-zoom)
- ✅ Keyboard shortcuts
- ✅ Accessible (WCAG 2.1 AA)

## Development Workflow

The frontend proxies API requests to the backend:
- `/api/*` → `http://localhost:8000/api/*`
- `/ws/*` → `ws://localhost:8000/ws/*`

Make sure the backend is running before starting the frontend.

## Environment Variables

Create `.env.local` for local overrides:

```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/status
```

## Design System

- **Colors**: `#1a1a2e` (primary), `#16213e` (light), `#0f3460` (dark), `#4ecdc4` (accent)
- **Font**: Inter (Google Fonts)
- **Breakpoint**: `768px` (desktop sidebar)
- **Thumbnail size**: `200×200px`
- **Sidebar width**: `240px`
- **Bottom nav height**: `64px`

## Browser Support

- Chrome 113+ (for JPEG XL support)
- Firefox 120+
- Safari 16.4+
- Edge 113+

## Performance Targets

- First Contentful Paint: <1.5s
- Time to Interactive: <3s
- Bundle size: <500KB gzipped
- Gallery scroll: 60fps
- WebSocket latency: <100ms

## License

MIT
