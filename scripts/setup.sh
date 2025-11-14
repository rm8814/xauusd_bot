#!/bin/bash

# Setup script for XAU/USD Trading Bot

echo "🚀 Setting up XAU/USD Trading Bot..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.template .env
    echo "⚠️  Please edit .env with your credentials"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs database data/cache data/exports data/backups

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your Telegram and API credentials"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Run the bot: python main.py"
