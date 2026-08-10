#!/usr/bin/env bash
# Build a Linux AppImage from Atlas's PyInstaller AppDir.

set -Eeuo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
appdir="$project_root/dist/Atlas.AppDir"
metadata_dir="$project_root/installer/appimage"
icon_source="$project_root/assets/icons/Icon.svg"
appimagetool=""


appimage_architecture() {
    case "$(uname -m)" in
        x86_64|amd64) printf '%s\n' "x86_64" ;;
        aarch64|arm64) printf '%s\n' "aarch64" ;;
        armv7l|armhf) printf '%s\n' "armhf" ;;
        *)
            echo "Unsupported AppImage architecture: $(uname -m)" >&2
            return 1
            ;;
    esac
}


download_appimagetool() {
    local architecture="$1"
    local local_bin_dir="$HOME/.local/bin"
    local destination="$local_bin_dir/appimagetool"
    local download_url="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${architecture}.AppImage"
    local temporary_file

    if ! command -v curl >/dev/null 2>&1 \
        && ! command -v wget >/dev/null 2>&1; then
        echo "Neither curl nor wget is available for the appimagetool download."
        return 1
    fi

    mkdir -p "$local_bin_dir"
    temporary_file="$(mktemp "${TMPDIR:-/tmp}/atlas-appimagetool.XXXXXX")"
    echo "Downloading appimagetool to $destination..."

    if command -v curl >/dev/null 2>&1; then
        curl --fail --location --retry 3 --output "$temporary_file" \
            "$download_url" || {
                rm -f -- "$temporary_file"
                return 1
            }
    else
        wget --output-document="$temporary_file" "$download_url" || {
            rm -f -- "$temporary_file"
            return 1
        }
    fi

    chmod 755 "$temporary_file"
    mv "$temporary_file" "$destination"
    appimagetool="$destination"
}


find_appimagetool() {
    local architecture="$1"
    local response

    if command -v appimagetool >/dev/null 2>&1; then
        appimagetool="$(command -v appimagetool)"
        return
    fi

    if [[ -x "$HOME/.local/bin/appimagetool" ]]; then
        appimagetool="$HOME/.local/bin/appimagetool"
        return
    fi

    echo "appimagetool is required only to turn the prepared AppDir into an AppImage."
    printf "Download the official appimagetool release now? [Y/n] "
    if ! read -r response; then
        response="n"
    fi

    case "${response:-Y}" in
        Y|y|YES|yes|Yes)
            if download_appimagetool "$architecture"; then
                return
            fi
            echo "Could not download appimagetool. Install it manually, then rerun this script."
            ;;
        *)
            echo "Skipping appimagetool download."
            ;;
    esac

    echo "The AppDir will still be built at $appdir."
}


architecture="$(appimage_architecture)"
output="${1:-$project_root/dist/Atlas-${architecture}.AppImage}"

for command in python install; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Required command not found: $command" >&2
        exit 1
    fi
done

for file in AppRun atlas.desktop; do
    if [[ ! -f "$metadata_dir/$file" ]]; then
        echo "Required AppImage metadata not found: $metadata_dir/$file" >&2
        exit 1
    fi
done

if [[ ! -f "$icon_source" ]]; then
    echo "Required Linux SVG icon not found: $icon_source" >&2
    exit 1
fi

find_appimagetool "$architecture"

cd "$project_root"
python -m PyInstaller --noconfirm --clean appimage.spec

# appimagetool discovers these conventional files at the AppDir root.
install -Dm755 "$metadata_dir/AppRun" "$appdir/AppRun"
install -Dm644 "$metadata_dir/atlas.desktop" "$appdir/atlas.desktop"
# The root icon matches Icon=atlas and is deliberately vector-first. This is
# the icon AppImage desktop integration and .DirIcon should prefer.
install -Dm644 "$icon_source" "$appdir/atlas.svg"

if [[ -z "$appimagetool" ]]; then
    echo "AppDir prepared: $appdir"
    exit 0
fi

# Extract-and-run avoids requiring FUSE to run the packaging tool itself.
ARCH="$architecture" APPIMAGE_EXTRACT_AND_RUN=1 "$appimagetool" \
    "$appdir" "$output"

echo "Created $output"
