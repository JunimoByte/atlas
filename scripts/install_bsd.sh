#!/usr/bin/env sh
# ==============================================================================
# Atlas Portable Installer (FreeBSD / GhostBSD)
# ==============================================================================

# 1. Ensure the script is run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Atlas requires root privileges to install to /usr/local/."
    echo "Elevating permissions via sudo..."
    exec sudo sh "$0" "$@"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BINARY_NAME="Atlas-x86_64-Portable"
ICON_NAME="Icon.svg"

# Ensure the executable exists next to this script
if [ ! -f "$SCRIPT_DIR/$BINARY_NAME" ]; then
    echo "ERROR: $BINARY_NAME not found in $SCRIPT_DIR."
    echo "Please extract the entire zip file before running install.sh."
    exit 1
fi

# ==============================================================================
# OS COMPATIBILITY CHECK
# ==============================================================================
# Check if the system has the older libutil.so.9 required by this binary.
# If not, install the compat13x-amd64 package automatically.
if ! grep -q "libutil.so.9" /var/run/ld-elf.so.hints 2>/dev/null; then
    echo "Missing FreeBSD 13 ABI libraries (libutil.so.9)."
    echo "Installing compat13x-amd64..."
    pkg install -y compat13x-amd64 || {
        echo "Failed to install compatibility libraries."
        exit 1
    }
fi

# ==============================================================================
# INSTALLATION
# ==============================================================================
echo "Installing Atlas binary..."
install -d -m 755 "/usr/local/bin"
# Copy the single-file binary directly to /usr/local/bin
install -m 755 "$SCRIPT_DIR/$BINARY_NAME" "/usr/local/bin/atlas"

echo "Installing Desktop Integration..."
ICON_DIR="/usr/local/share/icons/hicolor/scalable/apps"
install -d -m 755 "$ICON_DIR"

if [ -f "$SCRIPT_DIR/$ICON_NAME" ]; then
    install -m 644 "$SCRIPT_DIR/$ICON_NAME" "$ICON_DIR/atlas.svg"
else
    echo "Warning: $ICON_NAME not found. Skipping icon."
fi

DESKTOP_DIR="/usr/local/share/applications"
install -d -m 755 "$DESKTOP_DIR"

cat << 'EOF' > "$DESKTOP_DIR/atlas.desktop"
[Desktop Entry]
Name=Atlas
Comment=Browser profile backup application
Exec=/usr/local/bin/atlas
Icon=/usr/local/share/icons/hicolor/scalable/apps/atlas.svg
Terminal=false
Type=Application
Categories=Utility;Archiving;
EOF
chmod 644 "$DESKTOP_DIR/atlas.desktop"

echo ""
echo "=============================================================================="
echo "Installation Complete!"
echo "Atlas is now installed. You can launch it from your Application Menu."
echo "=============================================================================="
