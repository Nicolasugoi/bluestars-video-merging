@echo off
echo ================================================
echo  BlueStars Video Tool - Installation Script
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python first: https://python.org
    pause
    exit /b 1
)

echo [INFO] Python found, proceeding with installation...
echo.

REM Optionally, activate your virtual environment here
REM if exist venv\Scripts\activate.bat (
REM     echo [INFO] Activating virtual environment...
REM     call venv\Scripts\activate.bat
REM )

echo ================================================
echo  Installing FFmpeg 
echo ================================================

choco install ffmpeg-full
scoop install ffmpeg
winget install ffmpeg


echo ================================================
echo  Installing Python Packages
echo ================================================

REM Upgrade pip first
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

echo [INFO] Installing core packages...
python -m pip install pandas==2.2.3
if errorlevel 1 echo [WARNING] Failed to install pandas

python -m pip install streamlit==1.46.1
if errorlevel 1 echo [WARNING] Failed to install streamlit

python -m pip install openpyxl==3.1.5
if errorlevel 1 echo [WARNING] Failed to install openpyxl

echo [INFO] Installing video/audio processing packages...
python -m pip install moviepy==1.0.3
if errorlevel 1 echo [WARNING] Failed to install moviepy

python -m pip install Pillow==11.1.0
if errorlevel 1 echo [WARNING] Failed to install Pillow

python -m pip install librosa==0.11.0
if errorlevel 1 echo [WARNING] Failed to install librosa

python -m pip install soundfile==0.13.1
if errorlevel 1 echo [WARNING] Failed to install soundfile

echo [INFO] Installing web scraping packages...
python -m pip install requests==2.32.3
if errorlevel 1 echo [WARNING] Failed to install requests

python -m pip install beautifulsoup4==4.12.3
if errorlevel 1 echo [WARNING] Failed to install beautifulsoup4

python -m pip install lxml
if errorlevel 1 echo [WARNING] Failed to install lxml

python -m pip install selenium
if errorlevel 1 echo [WARNING] Failed to install selenium

python -m pip install webdriver-manager
if errorlevel 1 echo [WARNING] Failed to install webdriver-manager

echo [INFO] Installing Google API packages...
python -m pip install google-generativeai
if errorlevel 1 echo [WARNING] Failed to install google-generativeai

python -m pip install google-cloud-texttospeech
if errorlevel 1 echo [WARNING] Failed to install google-cloud-texttospeech

python -m pip install google-api-python-client
if errorlevel 1 echo [WARNING] Failed to install google-api-python-client

python -m pip install google-auth-oauthlib
if errorlevel 1 echo [WARNING] Failed to install google-auth-oauthlib

python -m pip install google-auth
if errorlevel 1 echo [WARNING] Failed to install google-auth

echo [INFO] Installing UI components...
python -m pip install streamlit-sortables
if errorlevel 1 echo [WARNING] Failed to install streamlit-sortables

echo.
echo ================================================
echo  Installation Complete!
echo ================================================
echo.
echo [INFO] Verifying critical packages...
python -c "import streamlit, pandas, moviepy; print('✅ Core packages working!')" 2>nul
if errorlevel 1 (
    echo [ERROR] Some critical packages failed to install
    echo Please check the warnings above and install manually
) else (
    echo ✅ All critical packages installed successfully!
)

echo.
echo To run the application:
echo   streamlit run webapp.py
echo.
echo Press any key to exit...
pause >nul