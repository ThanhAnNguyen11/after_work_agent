#!/bin/bash
set -e

echo "Starting FastAPI backend on port 8080..."
uvicorn backend.app.main:app --host 0.0.0.0 --port 8080
