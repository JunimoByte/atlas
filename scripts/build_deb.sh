#!/usr/bin/env bash
# Build the Atlas Debian package from the shared Linux PyInstaller payload.

set -Eeuo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
appdir="$project_root/dist/Atlas.AppDir"
metadata_dir="$project_root/installer/debian"
package_name="atlas"
icon_source="$project_root/assets/icons/Icon.svg"


debian_architecture() {
    local python_bits

    python_bits="$(python -c 'import struct; print(struct.calcsize("P") * 8)')"
    case "$(uname -m)" in
        x86_64|amd64)
            if [[ "$python_bits" == "32" ]]; then
                printf '%s\n' "i386"
            else
                printf '%s\n' "amd64"
            fi
            ;;
        i386|i486|i586|i686) printf '%s\n' "i386" ;;
        aarch64|arm64) printf '%s\n' "arm64" ;;
        armv7l|armhf) printf '%s\n' "armhf" ;;
        *)
            echo "Unsupported Debian package architecture: $(uname -m)" >&2
            return 1
            ;;
    esac
}


artifact_architecture() {
    case "$1" in
        amd64) printf '%s\n' "x86_64" ;;
        i386) printf '%s\n' "x86" ;;
        arm64) printf '%s\n' "arm64" ;;
        armhf) printf '%s\n' "armhf" ;;
        *)
            echo "Unsupported release artifact architecture: $1" >&2
            return 1
            ;;
    esac
}


project_version() {
    local pyproject="$project_root/pyproject.toml"
    local line
    local version_pattern='^[[:space:]]*version[[:space:]]*=[[:space:]]*"([^"]+)"'

    if [[ ! -f "$pyproject" ]]; then
        echo "Project metadata file not found: $pyproject" >&2
        return 1
    fi

    while IFS= read -r line || [[ -n "$line" ]]; do
        # A Windows checkout may leave a trailing carriage return here.
        line="${line%$'\r'}"
        if [[ $line =~ $version_pattern ]]; then
            printf '%s\n' "${BASH_REMATCH[1]}"
            return
        fi
    done < "$pyproject"

    echo "Could not read a project version from: $pyproject" >&2
    return 1
}


for command in python install cp; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Required command not found: $command" >&2
        exit 1
    fi
done

if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "Required command not found: dpkg-deb" >&2
    echo "Install the standard dpkg package, then rerun this script." >&2
    exit 1
fi

for file in control atlas.desktop copyright; do
    if [[ ! -f "$metadata_dir/$file" ]]; then
        echo "Required Debian packaging metadata not found: $metadata_dir/$file" >&2
        exit 1
    fi
done

if [[ ! -f "$icon_source" ]]; then
    echo "Required Linux SVG icon not found: $icon_source" >&2
    exit 1
fi

architecture="$(debian_architecture)"
artifact_architecture="$(artifact_architecture "$architecture")"
version="$(project_version)"
output="${1:-$project_root/dist/Atlas-${artifact_architecture}.deb}"
package_root="$project_root/build/deb/${package_name}_${version}_${architecture}"
payload="$appdir/usr/bin/atlas"
output_dir="$(dirname "$output")"
temporary_dir=""

if [[ ! "$version" =~ ^[0-9A-Za-z.+:~_-]+$ ]]; then
    echo "Project version is not valid for a Debian package: $version" >&2
    exit 1
fi

cd "$project_root"
python -m PyInstaller --noconfirm --clean appimage.spec

if [[ ! -x "$payload" ]]; then
    echo "Expected PyInstaller payload was not created: $payload" >&2
    exit 1
fi

# The staging directory is build-only and never becomes part of the package.
rm -rf -- "$package_root"
install -d \
    "$package_root/DEBIAN" \
    "$package_root/opt/atlas" \
    "$package_root/usr/bin" \
    "$package_root/usr/share/applications" \
    "$package_root/usr/share/doc/$package_name"

# Reuse the exact onedir payload built for AppImage. Keeping it under /opt
# prevents application files from spreading through system directories.
cp -a "$appdir/usr/bin/." "$package_root/opt/atlas/"
# Keep desktop integration independent of PyInstaller's private _internal
# layout while remaining SVG-only and avoiding an icon-theme asset tree.
install -Dm644 "$icon_source" "$package_root/opt/atlas/atlas.svg"
install -Dm755 "$metadata_dir/atlas" "$package_root/usr/bin/atlas"
install -Dm644 "$metadata_dir/atlas.desktop" \
    "$package_root/usr/share/applications/atlas.desktop"
install -Dm644 "$metadata_dir/copyright" \
    "$package_root/usr/share/doc/$package_name/copyright"
install -Dm644 "$project_root/LICENSE" \
    "$package_root/usr/share/doc/$package_name/LICENSE"
sed \
    -e "s/@VERSION@/$version/g" \
    -e "s/@ARCHITECTURE@/$architecture/g" \
    "$metadata_dir/control" > "$package_root/DEBIAN/control"

mkdir -p "$output_dir"
temporary_dir="$(mktemp -d "$project_root/build/deb-package.XXXXXX")"
trap 'rm -rf -- "$temporary_dir"' EXIT
temporary_output="$temporary_dir/${package_name}_${version}_${architecture}.deb"

# Build and inspect the archive before replacing an existing release file.
dpkg-deb --root-owner-group --build "$package_root" "$temporary_output"
dpkg-deb --info "$temporary_output" >/dev/null
dpkg-deb --contents "$temporary_output" >/dev/null
mv -f -- "$temporary_output" "$output"
rm -rf -- "$temporary_dir"
trap - EXIT

echo "Created $output"
