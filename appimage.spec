# -*- mode: python ; coding: utf-8 -*-

"""PyInstaller spec for the Atlas Linux AppImage payload.

This spec intentionally builds *onedir*, not onefile.  The output is placed
directly in an AppImage-compatible AppDir at ``dist/Atlas.AppDir/usr/bin``.
AppImage tools can package that directory without first wrapping and then
extracting a PyInstaller one-file executable at every launch.

``noarchive=True`` also keeps pure Python modules as files in the onedir
payload rather than putting them into PyInstaller's compressed PYZ archive.
That trades a modestly larger AppImage for a simpler runtime layout with no
second application-level decompression layer.
"""

import importlib
import os
import pkgutil
from typing import List

from PyInstaller.building.build_main import COLLECT, EXE, PYZ, Analysis
from PyInstaller.config import CONF
from PyInstaller.utils.hooks import collect_data_files

# =============================================================================
# QT BINDING DETECTION
# =============================================================================

try:
    import PyQt6.QtCore  # noqa: F401

    _active_qt = "PyQt6"
    _excluded_qt = "PyQt5"
except ImportError:
    _active_qt = "PyQt5"
    _excluded_qt = "PyQt6"

print(f"appimage.spec: bundling {_active_qt}, excluding {_excluded_qt}")


# =============================================================================
# RESOURCES & CONFIGS
# =============================================================================

datas = [
    ("assets/icons/*", "assets/icons"),
    ("assets/images/*", "assets/images"),
    ("configs/*", "configs"),
]

if _active_qt == "PyQt6":
    # Keep the platform and image plugins needed by both the regular-desktop
    # XCB path and native Wayland tiling-WM path. Missing optional directories
    # vary by PyQt6 release, hence the deliberately non-fatal attempts.
    qt_plugin_subdirs = [
        "Qt6/plugins/styles",
        "Qt6/plugins/platformthemes",
        "Qt6/plugins/platforms",
        "Qt6/plugins/iconengines",
        "Qt6/plugins/imageformats",
        "Qt6/plugins/wayland-decoration-client",
        "Qt6/plugins/xcbglintegrations",
        "Qt6/plugins/generic",
        "Qt6/plugins/egldeviceintegrations",
        "Qt6/plugins/wayland-graphics-integration-client",
    ]
    for subdir in qt_plugin_subdirs:
        try:
            datas += collect_data_files("PyQt6", subdir=subdir)
        except Exception:
            pass


# =============================================================================
# DYNAMIC HIDDEN IMPORTS
# =============================================================================


def collect_submodules(package_name: str) -> List[str]:
    """Recursively collect every importable submodule in ``package_name``."""
    hidden = []
    try:
        package = importlib.import_module(package_name)
        for _, modname, _ in pkgutil.walk_packages(
            package.__path__, package.__name__ + "."
        ):
            hidden.append(modname)
    except Exception as error:
        print(
            f"Warning: failed to collect submodules for {package_name}: "
            f"{error}"
        )
    return hidden


hiddenimports = (
    collect_submodules("atlas.backup")
    + collect_submodules("atlas.lib")
    + collect_submodules("atlas.display")
    + collect_submodules("atlas.ui")
)


# =============================================================================
# EXCLUDES
# =============================================================================

_unused_qt_modules = [
    "QtWebEngineWidgets", "QtWebEngineCore", "QtWebKit", "QtWebKitWidgets",
    "QtMultimedia", "QtNetwork", "QtNetworkAuth", "QtSql", "QtTest",
    "QtTextToSpeech", "QtWebSockets", "QtOpenGL", "QtSerialPort",
    "QtSensors", "QtNfc", "QtQuick", "QtQml", "Qt3DCore", "Qt3DRender",
    "Qt3DInput", "Qt3DLogic", "Qt3DExtras", "QtBluetooth", "QtPositioning",
    "QtPrintSupport", "QtQuickWidgets", "QtRemoteObjects", "QtSerialBus",
    "QtWebChannel",
]

_offline_module_prefixes = (
    "PyQt5.QtNetwork", "PyQt5.QtNetworkAuth", "PyQt5.QtWebEngine",
    "PyQt5.QtWebKit", "PyQt5.QtWebSockets", "PyQt5.QtBluetooth",
    "PyQt5.QtRemoteObjects", "PyQt5.QtWebChannel", "PyQt6.QtNetwork",
    "PyQt6.QtNetworkAuth", "PyQt6.QtWebEngine", "PyQt6.QtWebSockets",
    "PyQt6.QtBluetooth", "PyQt6.QtRemoteObjects", "PyQt6.QtWebChannel",
    "socket", "ssl", "urllib.request", "http", "ftplib", "imaplib", "poplib",
    "smtplib", "telnetlib", "nntplib", "wsgiref",
)

_offline_binary_markers = (
    "QtWebEngine", "QtWebKit", "QtWebSockets", "Qt5Bluetooth",
    "Qt6Bluetooth", "Qt5RemoteObjects", "Qt6RemoteObjects", "Qt5WebChannel",
    "Qt6WebChannel",
)

_standard_library_excludes = [
    "tkinter", "unittest", "pytest", "doctest", "distutils", "setuptools",
    "email", "sqlite3", "concurrent", "http", "xml", "html", "pydoc",
    # pathlib imports urllib.parse on current Python releases. Keep that
    # non-network parser available, while excluding urllib.request below.
    "socket", "ssl", "uuid", "pdb", "optparse", "getopt",
    "fractions", "decimal", "statistics", "hashlib", "hmac", "secrets",
    "ftplib", "imaplib", "poplib", "smtplib", "telnetlib", "nntplib", "cgi",
    "cgitb", "wsgiref", "mimetypes",
]

excludes_list = (
    [_excluded_qt]
    + [
        f"{binding}.{module}"
        for binding in ("PyQt5", "PyQt6")
        for module in _unused_qt_modules
    ]
    + _standard_library_excludes
)


def enforce_offline_payload(analysis: Analysis) -> None:
    """Fail the build if a blocked network-capable component is collected."""
    # PyInstaller's graph contains excluded modules, so inspect only entries
    # that will be placed in the shipped Python/extension payload.
    payload_paths = [entry[0] for entry in analysis.pure + analysis.binaries]

    def is_blocked_module(path: str) -> bool:
        normalized_path = path.replace("\\", ".").replace("/", ".")
        return any(
            normalized_path == prefix
            or normalized_path.startswith(prefix + ".")
            for prefix in _offline_module_prefixes
        )

    blocked_modules = sorted(
        path for path in payload_paths if is_blocked_module(path)
    )
    blocked_payload = sorted(
        path for path in payload_paths
        if any(marker.lower() in path.lower()
               for marker in _offline_binary_markers)
    )
    if blocked_modules or blocked_payload:
        blocked = blocked_modules + blocked_payload
        raise SystemExit(
            "Offline packaging policy blocked: " + ", ".join(blocked)
        )


# =============================================================================
# APPIMAGE PAYLOAD
# =============================================================================

a = Analysis(
    ["src/atlas/main.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes_list,
    noarchive=True,
    optimize=0,
)

enforce_offline_payload(a)

pyz = PYZ(a.pure)

# Do not pass binaries or data files here: COLLECT writes those as normal
# files in the AppDir. Passing them to EXE would recreate a one-file payload.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="atlas",
    debug=False,
    bootloader_ignore_signals=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

# COLLECT intentionally accepts only a basename and silently discards parent
# directories. Point its distpath at the AppDir's ``usr`` directory first, so
# the output lands at exactly ``dist/Atlas.AppDir/usr/bin/atlas``.
CONF["distpath"] = os.path.join(CONF["distpath"], "Atlas.AppDir", "usr")

# linuxdeploy/appimagetool expect the program below usr/bin in an AppDir.
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="bin",
)
