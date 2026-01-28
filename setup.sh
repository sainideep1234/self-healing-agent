#!/bin/bash

# Setup script for the Self-Healing API Gateway

echo "🔧 Setting up Self-Healing API Gateway..."
echo ""

# Check Python version
python_version=$(python3 --version 2>&1)
echo "📌 Python version: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Copy env file if not exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your LLM_API_KEY"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Start Redis and MongoDB: docker-compose up -d"
echo "2. Edit .env and add your LLM_API_KEY"
echo "3. Run the mock API: ./run_mock_api.sh"
echo "4. Run the gateway: ./run_gateway.sh"
echo "5. Test with: python test_healing.py"
