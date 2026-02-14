#!/bin/bash
# Production Deployment Script for DiaBay
# This builds the frontend and runs the backend in production mode

set -e  # Exit on error

echo "🚀 Building DiaBay for Production..."
echo ""

# Build frontend
echo "📦 Building frontend..."
cd frontend
npm run build
cd ..
echo "✅ Frontend built successfully"
echo ""

# Start backend (which will serve the built frontend)
echo "🔥 Starting backend in production mode..."
cd backend
source venv/bin/activate
python main.py

# Note: Backend will automatically detect and serve frontend/dist
