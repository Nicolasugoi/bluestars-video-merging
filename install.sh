#!/bin/bash
# BlueStars Video Tool - Installation Script for macOS/Linux

echo "================================================"
echo "  BlueStars Video Tool - Installation Script"
echo "  Platform: $(uname -s)"
echo "================================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    case $1 in
        "error") echo -e "${RED}[ERROR]${NC} $2" ;;
        "success") echo -e "${GREEN}[SUCCESS]${NC} $2" ;;
        "warning") echo -e "${YELLOW}[WARNING]${NC} $2" ;;
        "info") echo -e "${BLUE}[INFO]${NC} $2" ;;
    esac
}

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    print_status "error" "Python 3 is not installed or not in PATH"
    print_status "info" "Please install Python 3.8+ first:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  brew install python3"
    else
        echo "  sudo apt update && sudo apt install python3 python3-pip"
    fi
    exit 1
fi

print_status "success" "Python 3 found: $(python3 --version)"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    print_status "error" "pip3 is not installed"
    print_status "info" "Installing pip..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        python3 -m ensurepip --default-pip
    else
        sudo apt install python3-pip
    fi
fi

echo
echo "================================================"
echo "  Installing FFmpeg"
echo "================================================"

# Install FFmpeg based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if command -v brew &> /dev/null; then
        print_status "info" "Installing FFmpeg via Homebrew..."
        brew install ffmpeg
        if [ $? -eq 0 ]; then
            print_status "success" "FFmpeg installed successfully"
        else
            print_status "error" "Failed to install FFmpeg via Homebrew"
        fi
    else
        print_status "error" "Homebrew not found. Please install Homebrew first:"
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    print_status "info" "Installing FFmpeg..."
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y ffmpeg
    elif command -v yum &> /dev/null; then
        sudo yum install -y ffmpeg
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y ffmpeg
    elif command -v pacman &> /dev/null; then
        sudo pacman -S ffmpeg
    else
        print_status "warning" "Could not detect package manager. Please install FFmpeg manually"
    fi
    
    if command -v ffmpeg &> /dev/null; then
        print_status "success" "FFmpeg installed successfully"
    else
        print_status "error" "Failed to install FFmpeg"
    fi
else
    print_status "warning" "Unsupported OS. Please install FFmpeg manually"
fi

echo
echo "================================================"
echo "  Installing Python Packages"
echo "================================================"

# Upgrade pip first
print_status "info" "Upgrading pip..."
python3 -m pip install --upgrade pip

# Install packages with error checking
packages=(
    "pandas==2.2.3"
    "streamlit==1.46.1"
    "openpyxl==3.1.5"
    "moviepy==1.0.3"
    "Pillow==11.1.0"
    "librosa==0.11.0"
    "soundfile==0.13.1"
    "requests==2.32.3"
    "beautifulsoup4==4.12.3"
    "opencv-python"
    "lxml"
    "selenium"
    "webdriver-manager"
    "google-generativeai"
    "google-cloud-texttospeech"
    "google-api-python-client"
    "google-auth-oauthlib"
    "google-auth"
    "streamlit-sortables"
    "fonttools"
)

failed_packages=()

for package in "${packages[@]}"; do
    print_status "info" "Installing $package..."
    if python3 -m pip install "$package" > /dev/null 2>&1; then
        print_status "success" "✓ $package"
    else
        print_status "error" "✗ $package"
        failed_packages+=("$package")
    fi
done

echo
echo "================================================"
echo "  Installation Summary"
echo "================================================"

if [ ${#failed_packages[@]} -eq 0 ]; then
    print_status "success" "All packages installed successfully!"
else
    print_status "warning" "Some packages failed to install:"
    for pkg in "${failed_packages[@]}"; do
        echo "  - $pkg"
    done
    echo
    print_status "info" "You can try installing failed packages manually:"
    echo "  python3 -m pip install <package_name>"
fi

# Verify critical packages
echo
print_status "info" "Verifying critical packages..."
if python3 -c "import streamlit, pandas, moviepy; print('✅ Core packages working!')" 2>/dev/null; then
    print_status "success" "Core packages verified successfully!"
else
    print_status "error" "Some critical packages are not working properly"
fi

echo
echo "================================================"
echo "  Next Steps"
echo "================================================"
print_status "info" "To run the application:"
echo "  streamlit run webapp.py"
echo
print_status "info" "Or use the run script:"
echo "  chmod +x run.sh"
echo "  ./run.sh"
echo
print_status "success" "Installation completed!"
