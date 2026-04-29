# Creates a virtual environment in the project root

set -e  # Exit immediately if a command fails

# Ensure we are running in bash/zsh
if [ -z "$BASH_VERSION" ] && [ -z "$ZSH_VERSION" ]; then
    echo "Please run this script in bash or zsh:"
    echo "   source scripts/setup_dev.sh"
    return 1
fi

# Get the project root (parent folder of this script)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/venv"

# If venv exists, use it. Otherwise create it.
if [ -f "$VENV_PATH/bin/activate" ]; then
    echo "Existing virtual environment found."
else
    echo "Creating new virtual environment in project root..."
    python3 -m venv "$VENV_PATH"
fi

echo "Activating virtual environment..."
# shellcheck disable=SC1091
source "$VENV_PATH/bin/activate"

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing Atlas in editable dev mode..."
python -m pip install -e "$PROJECT_ROOT"[dev]

echo "Installing dev tools (Black, Ruff, Flake8, PyInstaller, pytest, PyQt6)..."
pip install black ruff flake8 pyinstaller pytest PyQt6

echo "Dev environment ready!"
echo "Your venv is now active in this shell."
echo "Project root: $PROJECT_ROOT"