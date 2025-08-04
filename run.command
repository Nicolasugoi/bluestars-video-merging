#!/bin/bash
# BlueStars Video Tool - Run Script for macOS/Linux

echo "🎬 BlueStars Video Tool"
echo "Starting application..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please run install.sh first."
    exit 1
fi

# Check if Streamlit is installed
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "❌ Streamlit is not installed. Please run install.sh first."
    exit 1
fi

# Check if webapp.py exists
if [ ! -f "webapp.py" ]; then
    echo "❌ webapp.py not found. Please make sure you're in the correct directory."
    exit 1
fi

# Get the local IP for network access
LOCAL_IP=$(python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || echo "localhost")

echo "🚀 Starting Streamlit application..."
echo "📍 Local URL: http://localhost:8501"
echo "🌐 Network URL: http://$LOCAL_IP:8501"
echo
echo "Press Ctrl+C to stop the application"
echo

# Run Streamlit
python3 -m streamlit run webapp.py \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --browser.gatherUsageStats false
