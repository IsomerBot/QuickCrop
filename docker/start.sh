#!/bin/sh

# Start script for QuickCrop production container

set -e

echo "Starting QuickCrop Application..."

# Function to handle graceful shutdown
cleanup() {
    echo "Shutting down services..."
    kill -TERM "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
    wait "$BACKEND_PID" "$FRONTEND_PID"
    echo "Services stopped."
    exit 0
}

# Trap termination signals
trap cleanup SIGTERM SIGINT

# Start backend server
echo "Starting backend server..."
cd /app/backend
python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    --access-log &
BACKEND_PID=$!

# Give backend time to start
sleep 3

# Start frontend server (production mode)
echo "Starting frontend server..."
cd /app/frontend

# Check if node_modules exists for production start
if [ -d "node_modules" ]; then
    # If node_modules exists, use npm start
    NODE_ENV=production npm start &
else
    # For Next.js production build, start directly with node
    NODE_ENV=production node node_modules/.bin/next start -p 3000 &
fi
FRONTEND_PID=$!

# Wait for both processes
echo "QuickCrop is running. Backend PID: $BACKEND_PID, Frontend PID: $FRONTEND_PID"
wait "$BACKEND_PID" "$FRONTEND_PID"