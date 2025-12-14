#!/bin/bash

echo "Stopping Harmony Scheduler..."

if [ -f .pids ]; then
    while read pid; do
        if ps -p $pid > /dev/null 2>&1; then
            kill $pid
            echo "  Stopped process $pid"
        fi
    done < .pids
    rm .pids
fi

# Cleanup
rm -f backend.log frontend.log

# Also kill by port just in case
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null

echo "✓ All servers stopped"
