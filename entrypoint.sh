#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

# Start FastAPI backend in the background
echo "🚀 Starting FastAPI backend on port 8000..."
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &

# Wait for backend to spin up
echo "⏳ Waiting for backend to initialize..."
sleep 3

# Start Streamlit frontend in the foreground
echo "🚀 Starting Streamlit frontend on port 8501..."
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
