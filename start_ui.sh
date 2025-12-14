#!/bin/bash

echo "================================================"
echo "  Harmony Scheduler - Starting Full Stack"
echo "================================================"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install from https://nodejs.org"
    exit 1
fi

echo "✓ Node.js found: $(node --version)"
echo ""

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies (this may take 2-3 minutes)..."
    cd frontend
    npm install
    cd ..
    echo ""
fi

echo "✓ Frontend dependencies ready"
echo ""

# Start backend
echo "🚀 Starting backend API (port 8000)..."
python3 run_server.py > backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"
sleep 3

# Check if backend started
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Backend API running"
else
    echo "❌ Backend failed to start. Check backend.log"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo ""

# Start frontend
echo "🎨 Starting frontend UI (port 3000)..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "   Frontend PID: $FRONTEND_PID"
sleep 3

echo ""
echo "================================================"
echo "  ✅ HARMONY SCHEDULER IS RUNNING!"
echo "================================================"
echo ""
echo "🌐 Open in browser: http://localhost:3000"
echo ""
echo "Backend API:  http://localhost:8000"
echo "API Docs:     http://localhost:8000/docs"
echo ""
echo "Logs:"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""
echo "To stop:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Or run: ./stop_ui.sh"
echo ""

# Save PIDs for stop script
echo "$BACKEND_PID" > .pids
echo "$FRONTEND_PID" >> .pids

# Wait a bit and try to open browser
sleep 2
if command -v open &> /dev/null; then
    echo "Opening browser..."
    open http://localhost:3000
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:3000
fi

echo "Press Ctrl+C to stop servers"
wait
