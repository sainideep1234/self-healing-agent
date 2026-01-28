#!/bin/bash

# Run the Chaos Playground Frontend
echo "🎮 Starting Chaos Playground Frontend..."
echo "📍 Frontend will be available at http://localhost:3000"
echo ""

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run dev server
npm run dev
