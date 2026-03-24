@echo off
echo 🚀 DeployBot Desktop - Windows Setup
echo ====================================

:: Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is not installed. Please install Node.js 16+ first:
    echo    https://nodejs.org/
    pause
    exit /b 1
)

echo ✅ Node.js detected: 
node --version

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8+ first:
    echo    https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python detected:
python --version

:: Install Python dependencies
echo.
echo 📦 Installing Python dependencies...
cd ..\deploybot 2>nul || (
    echo ❌ DeployBot CLI not found. Please ensure the deploybot folder is in the parent directory.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install Python dependencies
    pause
    exit /b 1
)

echo ✅ Python dependencies installed

:: Go back to GUI directory
cd ..\deploybot-gui

:: Install Node.js dependencies
echo.
echo 📦 Installing Node.js dependencies...
npm install
if errorlevel 1 (
    echo ❌ Failed to install Node.js dependencies
    pause
    exit /b 1
)

echo ✅ Node.js dependencies installed

echo.
echo 🎉 Installation complete!
echo.
echo To start DeployBot Desktop:
echo    npm start
echo.
echo To build distributable packages:
echo    npm run build
echo.
echo Happy deploying! 🚀
pause
