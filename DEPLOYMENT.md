# DiaBay Deployment Guide

DiaBay supports two deployment modes: **Development** and **Production**.

## 🛠️ Development Mode (Current)

**What it is:**
- Frontend: Vite dev server with Hot Module Replacement (HMR)
- Backend: FastAPI server
- **Two separate servers running**

**Ports:**
- Frontend: `http://0.0.0.0:5000` (Vite)
- Backend: `http://0.0.0.0:8000` (FastAPI)

**When to use:**
- Active development
- Need instant UI updates (HMR)
- Want React DevTools and debugging features

**How to run:**

```bash
# Terminal 1: Backend
cd diabay/backend
source venv/bin/activate
python main.py

# Terminal 2: Frontend
cd diabay/frontend
npm run dev
```

**Access:**
- Frontend UI: http://localhost:5000 or http://192.168.178.63:5000
- Backend API: http://localhost:8000/api

**Port forwarding needed:**
- ⚠️ BOTH ports 5000 AND 8000 (not recommended for production)

---

## 🚀 Production Mode (Recommended for Deployment)

**What it is:**
- Frontend: Built static files (optimized, minified)
- Backend: FastAPI serves both API AND frontend
- **Single server, one port**

**Ports:**
- Everything: `http://0.0.0.0:8000` (just backend)

**When to use:**
- Production deployment
- Remote access (e.g., from phone while scanning)
- Minimal port forwarding
- Better security (smaller attack surface)
- Better performance (no dev overhead)

**How to run:**

```bash
# Option 1: Using deployment script (easiest)
cd diabay
./deploy-production.sh

# Option 2: Manual steps
cd diabay/frontend
npm run build
cd ../backend
source venv/bin/activate
python main.py
```

**Access:**
- Everything: http://localhost:8000 or http://192.168.178.63:8000
- Frontend UI: http://192.168.178.63:8000
- API: http://192.168.178.63:8000/api
- WebSocket: ws://192.168.178.63:8000/ws/status

**Port forwarding needed:**
- ✅ ONLY port 8000 (one port, easy!)

---

## 📊 Comparison

| Feature | Development Mode | Production Mode |
|---------|------------------|-----------------|
| Ports to forward | 2 (5000, 8000) | 1 (8000 only) |
| Performance | Slower (dev overhead) | Fast (optimized build) |
| Bundle size | Large (dev dependencies) | Small (minified, tree-shaken) |
| Hot reload | ✅ Yes | ❌ No (rebuild needed) |
| Security | Lower (dev tools exposed) | Higher (minimal surface) |
| Setup complexity | Medium (two terminals) | Easy (one command) |
| Use case | Active development | Production, remote access |

---

## 🔄 Switching Between Modes

### Development → Production

```bash
cd diabay/frontend
npm run build
# Backend automatically detects frontend/dist and switches to production mode
```

### Production → Development

```bash
# Just start Vite dev server again
cd diabay/frontend
npm run dev
# Backend will show: "Development mode: Frontend NOT served from backend"
```

---

## 🌐 Remote Access Setup

### For Production Mode (Recommended)

1. Build frontend:
   ```bash
   cd diabay/frontend
   npm run build
   ```

2. Start backend:
   ```bash
   cd diabay/backend
   source venv/bin/activate
   python main.py
   ```

3. Configure router:
   - Forward port 8000 → your PC's IP (192.168.178.63)

4. Access from anywhere:
   - http://your-public-ip:8000

### For Development Mode (Not Recommended)

1. Start both servers (as shown above)

2. Configure router:
   - Forward port 5000 → 192.168.178.63:5000 (frontend)
   - Forward port 8000 → 192.168.178.63:8000 (backend)

3. Access:
   - Frontend: http://your-public-ip:5000
   - Backend: http://your-public-ip:8000

⚠️ **Security Warning:** Exposing dev servers to the internet is not recommended!

---

## 🎯 Recommended Workflow

**During Development:**
- Use Development Mode for fast iteration
- Keep both terminals open
- Make changes, see instant updates

**For Remote Monitoring (e.g., overnight scanning):**
- Build once: `npm run build`
- Deploy Production Mode
- Forward only port 8000
- Monitor from phone/laptop anywhere

**When Making Changes:**
- Switch back to Development Mode
- Make changes
- Test
- Build for production again when ready

---

## 🔍 How to Check Current Mode

Look at backend startup logs:

**Development Mode:**
```
INFO - Development mode: Frontend NOT served from backend (use Vite dev server)
INFO - To enable production mode, build frontend: cd frontend && npm run build
```

**Production Mode:**
```
INFO - Production mode: Serving frontend from /path/to/frontend/dist
```

---

## 🐛 Troubleshooting

### "Frontend not found" error

```bash
# Solution: Build the frontend
cd diabay/frontend
npm run build
```

### Changes not showing up

**In Development Mode:**
- Changes should appear instantly (HMR)
- If not, restart Vite dev server

**In Production Mode:**
- Rebuild frontend: `cd frontend && npm run build`
- Restart backend

### CORS errors

**Development Mode:**
- Normal (different ports) - Vite proxy handles it

**Production Mode:**
- Should not happen (same origin)
- If it does, check frontend built correctly

---

## 📝 Summary

**Use Production Mode when:**
- Deploying for real use
- Need remote access
- Want single port
- Performance matters

**Use Development Mode when:**
- Actively coding
- Need fast refresh
- Debugging React components

**Default recommendation:** Use Production Mode for everything except active development.
