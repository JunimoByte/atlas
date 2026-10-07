"""Atlas | Packages | Integration.

User-facing operating system integration helpers for Atlas.

Provides safe, cross-platform access to desktop features such as
opening folders in the system file manager.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
import os
import platform
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set

from atlas.backup import archive as Archive  # noqa: N812
from atlas.display.popup import show_warning

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# DESKTOP ENVIRONMENT DETECTION
# =============================================================================

_TILING_WINDOW_MANAGERS: Set[str] = {
    "amethyst", "awesome", "berry", "bspwm", "cage", "dwl", "dwm",
    "exwm", "herbstluftwm", "hyprland", "i3", "leftwm", "lspwm",
    "niri", "notched", "qtile", "ratpoison", "river", "spectrwm",
    "stumpwm", "sway", "wingo", "worm", "xmonad",
}

_LINUX_SESSION_VARIABLES = (
    "XDG_CURRENT_DESKTOP",
    "XDG_SESSION_DESKTOP",
    "DESKTOP_SESSION",
)


def _is_tiling_window_manager() -> bool:
    """Return True if the current Linux session is a known tiling WM."""
    if not sys.platform.startswith(
        ("linux", "freebsd", "openbsd", "netbsd", "dragonfly", "sunos")
    ):
        return False
    if "SWAYSOCK" in os.environ:
        return True
    session = " ".join(
        os.environ.get(v, "").lower() for v in _LINUX_SESSION_VARIABLES
    )
    return any(wm in session for wm in _TILING_WINDOW_MANAGERS)


def _is_kde() -> bool:
    """Return True if the current desktop environment is KDE Plasma."""
    desktop = ":".join(
        os.environ.get(v, "") for v in _LINUX_SESSION_VARIABLES
    ).lower()
    return (
        "kde" in desktop
        or "plasma" in desktop
        or "KDE_SESSION_VERSION" in os.environ
    )


# =============================================================================
# FILE OPENER TIMEOUT & TERMINAL FILE MANAGERS
# =============================================================================

OPENER_TIMEOUT_SECONDS = 3
"""Timeout in seconds for folder openers to avoid D-Bus/portal hangs."""

_TERMINAL_FILE_MANAGERS = ("ranger", "yazi", "nnn", "lf", "mc")

_TERMINAL_EMULATORS = (
    "foot",
    "alacritty",
    "kitty",
    "wezterm",
    "ghostty",
    "x-terminal-emulator",
    "xfce4-terminal",
    "konsole",
    "gnome-terminal",
    "xterm",
    "urxvt",
)


def _build_terminal_command(term: str, fm: str, path: str) -> List[str]:
    """Build command to run a terminal file manager inside an emulator."""
    if term in ("foot", "kitty"):
        return [term, fm, path]
    if term == "wezterm":
        return ["wezterm", "start", "--", fm, path]
    if term in ("xfce4-terminal", "ghostty"):
        return [term, "-e", f"{fm} {path}"]
    if term == "gnome-terminal":
        return ["gnome-terminal", "--", fm, path]
    return [term, "-e", fm, path]


def _get_terminal_file_manager_candidates(
    target: str, env: Optional[Dict[str, str]] = None
) -> List[List[str]]:
    """Return command candidates for terminal-based file managers."""
    path_env = env.get("PATH") if env else None
    available_fms = [
        fm for fm in _TERMINAL_FILE_MANAGERS
        if shutil.which(fm, path=path_env)
    ]
    if not available_fms:
        return []

    available_terms = [
        t for t in _TERMINAL_EMULATORS
        if shutil.which(t, path=path_env)
    ]
    if not available_terms:
        return []

    term = available_terms[0]
    return [
        _build_terminal_command(term, fm, target) for fm in available_fms
    ]


# =============================================================================
# FUNCTIONS
# =============================================================================


def open_folder(folder_path: Optional[Path] = None) -> None:
    """Resolve and open the selected folder in the file manager.

    If no folder is provided, attempt to open the archive output
    directory.  Display a user-facing warning if the folder does
    not exist or cannot be opened automatically.

    Args:
        folder_path (Optional[Path]): Specific path to open.
            Defaults to None.

    """
    try:
        if folder_path is None:
            # Use the raw stored path or compute the default without calling
            # get_zip_output_dir(), which always calls mkdir() and would
            # silently recreate a folder the user just deleted.
            folder_path = (
                Archive.ZIP_OUTPUT_DIR
                if Archive.ZIP_OUTPUT_DIR is not None
                else Archive._get_default_output_dir()
            )

        if folder_path is None:
            LOGGER.warning("No folder path available to open")
            show_warning(
                title="Caution",
                message="Folder Not Found",
                details=(
                    "The selected folder could not be "
                    "found.\n\n"
                    "It may have been moved or deleted."
                ),
            )
            return

        folder = folder_path.resolve()

        if not folder.exists():
            LOGGER.warning("Selected folder missing: %s", folder)
            show_warning(
                title="Caution",
                message="Folder Not Found",
                details=(
                    "The selected folder could not be "
                    "found.\n\n"
                    "It may have been moved or deleted."
                ),
            )
            return

        _open_folder_platform(folder)
        LOGGER.debug("Dispatched open folder request: %s", folder)

    except FileNotFoundError as error:
        LOGGER.warning(
            "Failed to open folder: %s",
            error,
            exc_info=True,
        )
        show_warning(
            title="Caution",
            message="Failed to Open Folder",
            details=(
                "Atlas could not open the selected folder "
                "automatically.\n\n"
                "Please open it manually using your file "
                "manager."
            ),
        )

    except Exception as error:
        LOGGER.warning(
            "Failed to open folder: %s",
            error,
            exc_info=True,
        )
        show_warning(
            title="Caution",
            message="Failed to Open Folder",
            details=(
                "Atlas ran into an error while trying to "
                "open the selected folder.\n\n"
                "Please try again later."
            ),
        )


def _get_clean_desktop_environment() -> Dict[str, str]:
    """Sanitize environment variables for spawning desktop file managers.

    Frozen builds (PyInstaller/AppImage) and Atlas runtime settings
    modify variables such as ``LD_LIBRARY_PATH``, ``QT_PLUGIN_PATH``,
    ``QT_QPA_PLATFORM``, and ``GIO_MODULE_DIR``. If inherited by system
    utilities like ``xdg-open`` or KDE Dolphin, these overrides cause
    severe ABI mismatches, missing platform plugins, or crashes.

    Returns:
        Dict[str, str]: A cleaned copy of ``os.environ``.

    """
    env = os.environ.copy()

    # Restore the original system library path if PyInstaller modified it.
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env.pop("LD_LIBRARY_PATH_ORIG")
    else:
        env.pop("LD_LIBRARY_PATH", None)

    # Remove Qt and GLib overrides so child processes use host libraries.
    for var in (
        "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM_PLUGIN_PATH",
        "QT_QPA_PLATFORM",
        "QT_STYLE_OVERRIDE",
        "QML_IMPORT_PATH",
        "QML2_IMPORT_PATH",
        "GIO_MODULE_DIR",
        "NO_AT_BRIDGE",
    ):
        env.pop(var, None)

    # Remove frozen Python overrides so host Python helpers execute cleanly.
    if getattr(sys, "frozen", False):
        for var in ("PYTHONPATH", "PYTHONHOME", "_MEIPASS2"):
            env.pop(var, None)

    return env


def _get_linux_file_manager_candidates(
    folder_path: Path,
    env: Optional[Dict[str, str]] = None,
) -> List[List[str]]:
    """Return ordered command candidates to open a folder on Linux.

    Detects the active desktop session (prioritizing KDE Plasma tools
    when running on KDE) and appends generic desktop handlers and
    terminal-based file managers for minimal/tiling setups.

    Args:
        folder_path (Path): Path to the folder to open.
        env (Optional[Dict[str, str]]): Cleaned environment dictionary.

    Returns:
        List[List[str]]: Candidate command arguments.

    """
    target = str(folder_path)
    if _is_kde():
        candidates = [
            ["xdg-open", target],
            ["dolphin", target],
            ["kde-open6", target],
            ["kde-open5", target],
            ["kde-open", target],
            ["kioclient6", "exec", target],
            ["kioclient5", "exec", target],
            ["krusader", target],
            ["gio", "open", target],
        ]
    else:
        candidates = [
            ["xdg-open", target],
            ["gio", "open", target],
            ["dolphin", target],
            ["nautilus", target],
            ["thunar", target],
            ["pcmanfm-qt", target],
            ["pcmanfm", target],
            ["caja", target],
            ["nemo", target],
            ["spacefm", target],
            ["cosmic-files", target],
            ["pantheon-files", target],
            ["doublecmd", target],
        ]

    candidates.extend(
        _get_terminal_file_manager_candidates(target, env=env)
    )
    return candidates


def _run_linux_open(folder_path: Path) -> bool:
    """Execute candidate commands to open a folder on Linux/POSIX.

    Iterates through candidate file openers, executing each with a
    sanitized desktop environment and timeout to prevent D-Bus
    hangs, until one exits successfully.

    Args:
        folder_path (Path): Path to the folder to open.

    Returns:
        bool: True if a file manager was successfully spawned,
            False otherwise.

    """
    env = _get_clean_desktop_environment()
    candidates = _get_linux_file_manager_candidates(folder_path, env=env)

    for cmd in candidates:
        exe = cmd[0]
        # Always attempt xdg-open; for other tools require binary presence.
        if (
            exe != "xdg-open"
            and shutil.which(exe, path=env.get("PATH")) is None
        ):
            continue

        try:
            result = subprocess.run(
                cmd,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=OPENER_TIMEOUT_SECONDS,
            )
            returncode = getattr(result, "returncode", None)
            if returncode == 0 or (
                returncode is not None and not isinstance(returncode, int)
            ):
                LOGGER.info("Opened folder using %s: %s", exe, folder_path)
                return True

            stderr_msg = result.stderr.strip() if result.stderr else ""
            LOGGER.debug(
                "Opener '%s' failed (exit code %s): %s",
                exe,
                returncode,
                stderr_msg,
            )
        except subprocess.TimeoutExpired:
            LOGGER.warning(
                "Opener '%s' timed out after %ds (likely D-Bus/portal hang); "
                "trying next candidate",
                exe,
                OPENER_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            LOGGER.debug("Failed to execute '%s': %s", exe, exc)

    LOGGER.warning(
        "Could not open folder '%s' with any available file manager.",
        folder_path,
    )
    return False


def _show_open_folder_failed(folder_path: Path) -> None:
    """Display warning when no file manager could open the folder."""
    show_warning(
        title="Caution",
        message="Failed to Open Folder",
        details=(
            "Atlas could not find a supported file manager to open:\n\n"
            f"{folder_path}\n\n"
            "Please open this folder manually."
        ),
    )


def _dispatch_open_folder_warning(folder_path: Path) -> None:
    """Safely dispatch open folder warning to the main Qt thread."""
    try:
        from atlas.compatibility.qt import QtCore, QtWidgets

        app = QtWidgets.QApplication.instance()
        if app is not None:
            QtCore.QTimer.singleShot(
                0, app, lambda: _show_open_folder_failed(folder_path)
            )
            return
    except Exception:
        pass

    try:
        _show_open_folder_failed(folder_path)
    except Exception as exc:
        LOGGER.debug("Could not show open folder failure dialog: %s", exc)


def _open_folder_platform(folder_path: Path) -> None:
    """Open a folder using the platform's native file manager.

    Dispatches to the appropriate OS command:
    - Windows: ``os.startfile``
    - macOS:   ``open``
    - Linux:   Candidate search (``xdg-open``, KDE ``dolphin``, etc.)
      in a daemon thread to prevent zombies, with environment
      sanitization for PyInstaller/AppImage compatibility.

    Args:
        folder_path (Path): Absolute path to open.

    """
    system = platform.system().lower()

    if system == "windows":
        start = getattr(os, "startfile", None)
        if start is not None:
            start(folder_path)
            LOGGER.info("Opened folder: %s", folder_path)
        else:
            LOGGER.warning("os.startfile not available on this platform.")
    elif system == "darwin":
        subprocess.call(["open", str(folder_path)])
        LOGGER.info("Opened folder: %s", folder_path)
    else:
        # Linux and other POSIX systems.
        def _run_open() -> None:
            if not _run_linux_open(folder_path):
                _dispatch_open_folder_warning(folder_path)

        threading.Thread(target=_run_open, daemon=True).start()
