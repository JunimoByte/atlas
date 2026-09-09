#!/usr/bin/env bash
# Build the Atlas FreeBSD package (.pkg) from the PyInstaller payload.
# Compatible with bash and zsh (GhostBSD default), both executed and sourced.

_build_pkg() {
    # Path resolution compatible with bash and zsh (sourced and executed)
    local _script_path=""
    if [ -n "${BASH_SOURCE[0]:-}" ]; then
        _script_path="${BASH_SOURCE[0]}"
    elif [ -n "${ZSH_VERSION:-}" ]; then
        # shellcheck disable=SC2296
        _script_path="${(%):-%x}"
    else
        _script_path="$0"
    fi

    local project_root
    project_root="$(cd "$(dirname "$_script_path")/.." && pwd)"
    local appdir="$project_root/dist/Atlas.AppDir"
    local package_name="atlas"

    project_version() {
        local pyproject="$project_root/pyproject.toml"
        if [[ ! -f "$pyproject" ]]; then
            echo "Project metadata file not found: $pyproject" >&2
            return 1
        fi

        # 1. Try python parsing if available
        if command -v python >/dev/null 2>&1; then
            local py_ver
            py_ver="$(python -c '
import re
with open("pyproject.toml") as f:
    m = re.search(r"^[ \t]*version[ \t]*=[ \t]*\"([^\"]+)\"", f.read(), re.M)
    if m: print(m.group(1))
' 2>/dev/null || true)"
            if [[ -n "$py_ver" ]]; then
                printf '%s\n' "$py_ver"
                return 0
            fi
        fi

        # 2. Shell regex fallback compatible with both bash ($BASH_REMATCH) and zsh ($match)
        local line
        local version_pattern='^[[:space:]]*version[[:space:]]*=[[:space:]]*"([^"]+)"'
        while IFS= read -r line || [[ -n "$line" ]]; do
            line="${line%$'\r'}"
            if [[ $line =~ $version_pattern ]]; then
                if [[ -n "${BASH_REMATCH[1]:-}" ]]; then
                    printf '%s\n' "${BASH_REMATCH[1]}"
                    return 0
                elif [[ -n "${match[1]:-}" ]]; then
                    printf '%s\n' "${match[1]}"
                    return 0
                fi
            fi
        done < "$pyproject"

        echo "Could not read a project version from: $pyproject" >&2
        return 1
    }

    for command in python install cp find sed grep; do
        if ! command -v "$command" >/dev/null 2>&1; then
            echo "Required command not found: $command" >&2
            return 1
        fi
    done

    if ! command -v pkg >/dev/null 2>&1; then
        echo "Required command not found: pkg" >&2
        echo "This script must be run on a FreeBSD system with the pkg command available." >&2
        return 1
    fi

    local version
    version="$(project_version)"
    local architecture
    architecture="$(uname -m)"
    local output="${1:-$project_root/dist/Atlas-${architecture}.pkg}"
    local package_root="$project_root/build/pkg/${package_name}_${version}_${architecture}"
    local payload="$appdir/usr/bin/atlas"
    local output_dir
    output_dir="$(dirname "$output")"

    if [[ ! "$version" =~ ^[0-9A-Za-z.+:~_-]+$ ]]; then
        echo "Project version is not valid for a package: $version" >&2
        return 1
    fi

    cd "$project_root"
    python -m PyInstaller --noconfirm --clean appimage.spec

    if [[ ! -x "$payload" ]]; then
        echo "Expected PyInstaller payload was not created: $payload" >&2
        return 1
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
    local icon_dir="$package_root/usr/local/share/icons/hicolor/scalable/apps"
    mkdir -p "$icon_dir"
    install -m 644 "$project_root/assets/icons/Icon.svg" "$icon_dir/atlas.svg"

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
Icon=/usr/local/share/icons/hicolor/scalable/apps/atlas.svg
Terminal=false
Type=Application
Categories=Utility;Archiving;
EOF

    install -m 644 "$project_root/LICENSE" "$package_root/usr/local/share/doc/$package_name/LICENSE"

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
prefix: "/"
EOF

    mkdir -p "$output_dir"
    local temporary_dir
    temporary_dir="$(mktemp -d "$project_root/build/pkg-package.XXXXXX")"

    local plist_file="$temporary_dir/plist"
    (cd "$package_root" && find . -type f -o -type l | sed -e 's/^\.\///' | grep -v '^+MANIFEST$') > "$plist_file"

    pkg create -M "$package_root/+MANIFEST" -p "$plist_file" -r "$package_root" -o "$temporary_dir"

    local pkg_file
    pkg_file="$(ls "$temporary_dir"/*.pkg 2>/dev/null | head -n 1)"
    if [[ -f "$pkg_file" ]]; then
        mv -f -- "$pkg_file" "$output"
    else
        echo "Failed to create pkg file." >&2
        rm -rf -- "$temporary_dir"
        return 1
    fi

    rm -rf -- "$temporary_dir"
    echo "Created $output"
}

# Run the build function safely without terminating the interactive shell if sourced
_build_pkg "$@"
