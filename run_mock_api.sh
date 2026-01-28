#!/bin/bash

# Run the Mock Legacy API
echo "🏛️  Starting Mock Legacy API..."
echo "📍 Server will be available at http://localhost:8001"
echo "📚 API Docs: http://localhost:8001/docs"
echo ""
echo "💡 Tip: Use POST /mode to switch between 'stable' and 'drifted' schemas"
echo ""

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run with uvicorn
python -m uvicorn mock_api.main:app --host 0.0.0.0 --port 8001 --reload
