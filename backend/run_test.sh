#!/bin/bash
# Quick test script for DiaBay

echo "🚀 DiaBay Test Script"
echo "====================="
echo ""

# Activate virtual environment
source venv/bin/activate

# Check if venv is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Virtual environment not activated!"
    exit 1
fi

echo "✓ Virtual environment activated"
echo ""

# Run test pipeline
echo "🧪 Running test pipeline with sample TIFFs..."
echo ""
python test_pipeline.py

echo ""
echo "====================="
echo "✅ Test complete!"
echo ""
echo "Check the output/ directory for enhanced JPEGs"
echo ""
