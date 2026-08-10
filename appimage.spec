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

from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ
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
    # Keep the platform and image plugins Atlas needs when it forces the XCB
    # backend on Linux. Missing optional directories vary by PyQt6 release,
    # hence the deliberately non-fatal collection attempts.
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
        print(f"Warning: failed to collect submodules for {package_name}: {error}")
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

excludes_list = [
    _excluded_qt,
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtMultimedia",
    "PyQt6.QtNetwork",
    "PyQt6.QtSql",
    "PyQt6.QtTest",
    "PyQt6.QtTextToSpeech",
    "PyQt6.QtWebSockets",
    "PyQt6.QtOpenGL",
    "PyQt6.QtSerialPort",
    "PyQt6.QtSensors",
    "PyQt6.QtNfc",
    "PyQt6.QtQuick",
    "PyQt6.QtQml",
    "PyQt6.Qt3DCore",
    "PyQt6.Qt3DRender",
    "PyQt6.Qt3DInput",
    "PyQt6.Qt3DLogic",
    "PyQt6.Qt3DExtras",
    "PyQt6.QtBluetooth",
    "PyQt6.QtPositioning",
    "PyQt6.QtPrintSupport",
    "PyQt6.QtQuickWidgets",
    "PyQt6.QtRemoteObjects",
    "PyQt6.QtSerialBus",
    "PyQt6.QtWebChannel",
    "tkinter",
    "unittest",
    "pytest",
    "doctest",
    "distutils",
    "setuptools",
    "email",
    "sqlite3",
    "concurrent",
    "http",
    "xml",
    "html",
    "pydoc",
    "ssl",
    "uuid",
    "pdb",
    "optparse",
    "getopt",
    "fractions",
    "decimal",
    "statistics",
    "hashlib",
    "hmac",
    "secrets",
    "ftplib",
    "imaplib",
    "poplib",
    "smtplib",
    "telnetlib",
    "nntplib",
    "cgi",
    "cgitb",
    "wsgiref",
    "mimetypes",
]


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
