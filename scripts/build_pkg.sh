#!/usr/bin/env bash
# Build the Atlas FreeBSD package (.pkg) from the PyInstaller payload.

set -Eeuo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
appdir="$project_root/dist/Atlas.AppDir"
package_name="atlas"

project_version() {
    local pyproject="$project_root/pyproject.toml"
    local line
    local version_pattern='^[[:space:]]*version[[:space:]]*=[[:space:]]*"([^"]+)"'

    if [[ ! -f "$pyproject" ]]; then
        echo "Project metadata file not found: $pyproject" >&2
        return 1
    fi

    while IFS= read -r line || [[ -n "$line" ]]; do
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

if ! command -v pkg >/dev/null 2>&1; then
    echo "Required command not found: pkg" >&2
    echo "This script must be run on a FreeBSD system with the pkg command available." >&2
    exit 1
fi

version="$(project_version)"
architecture="$(uname -m)"
output="${1:-$project_root/dist/Atlas-${architecture}.pkg}"
package_root="$project_root/build/pkg/${package_name}_${version}_${architecture}"
payload="$appdir/usr/bin/atlas"
output_dir="$(dirname "$output")"

if [[ ! "$version" =~ ^[0-9A-Za-z.+:~_-]+$ ]]; then
    echo "Project version is not valid for a package: $version" >&2
    exit 1
fi

cd "$project_root"
python -m PyInstaller --noconfirm --clean appimage.spec

if [[ ! -x "$payload" ]]; then
    echo "Expected PyInstaller payload was not created: $payload" >&2
    exit 1
fi

rm -rf -- "$package_root"
install -d \
    "$package_root/usr/local/atlas" \
    "$package_root/usr/local/bin" \
    "$package_root/usr/local/share/applications" \
    "$package_root/usr/local/share/doc/$package_name"

# Reuse the exact onedir payload built for AppImage.
cp -a "$appdir/usr/bin/." "$package_root/usr/local/atlas/"

# Desktop integration
install -Dm644 "$project_root/assets/icons/Icon.svg" "$package_root/usr/local/atlas/atlas.svg"

# Create a shell wrapper for launching the application
cat << 'EOF' > "$package_root/usr/local/bin/atlas"
#!/bin/sh
exec /usr/local/atlas/atlas "$@"
EOF
chmod +x "$package_root/usr/local/bin/atlas"

# Create a basic .desktop file for DEs on FreeBSD
cat << 'EOF' > "$package_root/usr/local/share/applications/atlas.desktop"
[Desktop Entry]
Name=Atlas
Comment=Browser profile backup application
Exec=/usr/local/bin/atlas
Icon=/usr/local/atlas/atlas.svg
Terminal=false
Type=Application
Categories=Utility;Archiving;
EOF

install -Dm644 "$project_root/LICENSE" "$package_root/usr/local/share/doc/$package_name/LICENSE"

# Generate the FreeBSD pkg +MANIFEST dynamically to avoid bloating the root repository
cat << EOF > "$package_root/+MANIFEST"
name: "${package_name}"
version: "${version}"
origin: "sysutils/${package_name}"
comment: "Browser profile backup application"
desc: "Atlas is a browser profile backup application."
maintainer: "Atlas Developers"
categories: ["sysutils"]
www: "https://github.com/JunimoByte/atlas"
prefix: "/usr/local"
EOF

mkdir -p "$output_dir"
temporary_dir="$(mktemp -d "$project_root/build/pkg-package.XXXXXX")"
trap 'rm -rf -- "$temporary_dir"' EXIT

pkg create -M "$package_root/+MANIFEST" -r "$package_root" -o "$temporary_dir"

pkg_file=\$(ls "$temporary_dir"/*.pkg 2>/dev/null | head -n 1)
if [[ -f "$pkg_file" ]]; then
    mv -f -- "$pkg_file" "$output"
else
    echo "Failed to create pkg file." >&2
    exit 1
fi

rm -rf -- "$temporary_dir"
trap - EXIT

echo "Created $output"
