#!/usr/bin/env python3
"""
Harmony Scheduler API Server
Run with: python run_server.py
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from api.main import app
import uvicorn

if __name__ == "__main__":
    print("Starting Harmony Scheduler API...")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("\nPress CTRL+C to stop\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
