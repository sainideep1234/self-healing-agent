#!/bin/bash

# Run the Self-Healing API Gateway
echo "🚀 Starting Self-Healing API Gateway..."
echo "📍 Server will be available at http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run with uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
