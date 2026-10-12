#!/usr/bin/env bash
# Build a standalone Flatpak bundle (.flatpak) for Atlas.

set -Eeuo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$project_root/installer/flatpak/io.github.junimobyte.Atlas.yml"
app_id="io.github.junimobyte.Atlas"


flatpak_architecture() {
    case "$(uname -m)" in
        x86_64|amd64) printf '%s\n' "x86_64" ;;
        aarch64|arm64) printf '%s\n' "aarch64" ;;
        *)
            echo "Unsupported Flatpak architecture: $(uname -m)" >&2
            return 1
            ;;
    esac
}


for command in flatpak flatpak-builder; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Required command not found: $command" >&2
        echo "Install flatpak and flatpak-builder, then rerun." >&2
        exit 1
    fi
done

if [[ ! -f "$manifest" ]]; then
    echo "Required Flatpak manifest not found: $manifest" >&2
    exit 1
fi

architecture="$(flatpak_architecture)"
dist_dir="$project_root/dist"
output="${1:-$dist_dir/Atlas-${architecture}.flatpak}"
build_dir="$project_root/build/flatpak/build-dir"
repo_dir="$project_root/build/flatpak/repo"

mkdir -p "$dist_dir" "$project_root/build/flatpak"

echo "Building Flatpak bundle for $app_id ($architecture)..."

flatpak-builder \
    --force-clean \
    --user \
    --install-deps-from=flathub \
    --default-branch=stable \
    --repo="$repo_dir" \
    "$build_dir" \
    "$manifest"

flatpak build-bundle \
    "$repo_dir" \
    "$output" \
    "$app_id"

echo "Flatpak bundle successfully created: $output"
