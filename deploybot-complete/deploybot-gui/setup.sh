#!/bin/bash
# DeployBot Desktop Setup Script

echo "🚀 DeployBot Desktop - Installation Script"
echo "==========================================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first:"
    echo "   https://nodejs.org/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | sed 's/v//')
REQUIRED_VERSION="16.0.0"

if ! node -p "process.version" | grep -q "v1[6-9]\|v[2-9]"; then
    echo "❌ Node.js version $NODE_VERSION is too old. Please install version 16 or higher."
    exit 1
fi

echo "✅ Node.js $(node -v) detected"

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.8+ first:"
    echo "   https://www.python.org/downloads/"
    exit 1
fi

# Try python3 first, then python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "✅ Python $($PYTHON_CMD --version) detected"

# Install Python dependencies for CLI
echo ""
echo "📦 Installing Python dependencies..."
cd ../deploybot 2>/dev/null || {
    echo "❌ DeployBot CLI not found. Please ensure the deploybot folder is in the parent directory."
    exit 1
}

$PYTHON_CMD -m pip install -r requirements.txt --break-system-packages 2>/dev/null || \
$PYTHON_CMD -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

echo "✅ Python dependencies installed"

# Go back to GUI directory
cd ../deploybot-gui

# Install Node.js dependencies
echo ""
echo "📦 Installing Node.js dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Node.js dependencies"
    exit 1
fi

echo "✅ Node.js dependencies installed"

# Create desktop shortcut (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo "🖥️ Creating desktop shortcut..."
    
    DESKTOP_FILE="$HOME/.local/share/applications/deploybot.desktop"
    CURRENT_DIR="$(pwd)"
    
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=DeployBot Desktop
Comment=Visual deployment automation tool
Exec=cd "$CURRENT_DIR" && npm start
Icon=$CURRENT_DIR/assets/icon.png
Terminal=false
StartupWMClass=DeployBot
Categories=Development;
EOF
    
    chmod +x "$DESKTOP_FILE"
    echo "✅ Desktop shortcut created"
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "To start DeployBot Desktop:"
echo "   npm start"
echo ""
echo "To build distributable packages:"
echo "   npm run build"
echo ""
echo "Happy deploying! 🚀"
