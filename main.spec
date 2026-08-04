# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file for Atlas application.

- Dynamically collects all submodules in 'backup', 'lib', 'display', and 'ui'
  for hidden imports.
- Includes resources and configuration files.
- Compatible with Windows 7+, Linux, and PyInstaller onefile builds.
- Detects the active Qt binding at build time and excludes the other to
  prevent PyInstaller's 'multiple Qt bindings' build error.
"""

import ctypes.util
import importlib
import os
import pkgutil
import sys
from typing import List

from PyInstaller.building.build_main import EXE, PYZ, Analysis
from PyInstaller.utils.hooks import collect_data_files

# =============================================================================
# QT BINDING DETECTION
# =============================================================================

# Determine which Qt binding is active using the same logic as qt.py so that
# PyInstaller only bundles one binding and avoids the
# "multiple Qt bindings" build error.

_py_ver = sys.version_info[:2]
_is_win = sys.platform == "win32"
_is_linux = sys.platform.startswith("linux")
_has_xcb_cursor = bool(ctypes.util.find_library("xcb-cursor"))

if (_is_win and _py_ver <= (3, 8)) or (
    _is_linux and (not _has_xcb_cursor or _py_ver < (3, 8))
):
    _active_qt = "PyQt5"
    _excluded_qt = "PyQt6"
else:
    _active_qt = "PyQt6"
    _excluded_qt = "PyQt5"

print(f"main.spec: active Qt binding = {_active_qt} (excluding {_excluded_qt})")

# =============================================================================
# RESOURCES & CONFIGS
# =============================================================================

datas = [
    ('assets/icons/*', 'assets/icons'),
    ('assets/images/*', 'assets/images'),
    ('configs/*', 'configs'),
]

# Collect Qt platform plugins for the active binding
if _active_qt == "PyQt6":
    qt_plugin_subdirs = [
        'Qt6/plugins/styles',
        'Qt6/plugins/platformthemes',
        'Qt6/plugins/platforms',
        'Qt6/plugins/iconengines',
        'Qt6/plugins/imageformats',
        'Qt6/plugins/wayland-decoration-client',
        'Qt6/plugins/xcbglintegrations',
        'Qt6/plugins/generic',
        'Qt6/plugins/egldeviceintegrations',
        'Qt6/plugins/wayland-graphics-integration-client',
    ]
    for subdir in qt_plugin_subdirs:
        try:
            datas += collect_data_files('PyQt6', subdir=subdir)
        except Exception:
            pass


# =============================================================================
# DYNAMIC HIDDEN IMPORTS
# =============================================================================

def collect_submodules(package_name: str) -> List[str]:
    """Recursively collect all submodules in a package for hiddenimports.

    Args:
        package_name (str): Dotted package name to walk.

    Returns:
        List[str]: List of fully-qualified module names.

    """
    hidden = []
    try:
        package = importlib.import_module(package_name)
        for _, modname, _ in pkgutil.walk_packages(
            package.__path__, package.__name__ + "."
        ):
            hidden.append(modname)
    except Exception as error:
        print(
            f"Warning: failed to collect submodules for "
            f"{package_name}: {error}"
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

excludes_list = [
    # Exclude the unused Qt binding to prevent PyInstaller build error
    _excluded_qt,

    # Unused PyQt6 modules (no-ops when PyQt5 is active)
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebEngineCore',
    'PyQt6.QtMultimedia',
    'PyQt6.QtNetwork',
    'PyQt6.QtSql',
    'PyQt6.QtTest',
    'PyQt6.QtTextToSpeech',
    'PyQt6.QtWebSockets',
    'PyQt6.QtOpenGL',
    'PyQt6.QtSerialPort',
    'PyQt6.QtSensors',
    'PyQt6.QtNfc',
    'PyQt6.QtQuick',
    'PyQt6.QtQml',
    'PyQt6.Qt3DCore',
    'PyQt6.Qt3DRender',
    'PyQt6.Qt3DInput',
    'PyQt6.Qt3DLogic',
    'PyQt6.Qt3DExtras',
    'PyQt6.QtBluetooth',
    'PyQt6.QtPositioning',
    'PyQt6.QtPrintSupport',
    'PyQt6.QtQuickWidgets',
    'PyQt6.QtRemoteObjects',
    'PyQt6.QtSerialBus',
    'PyQt6.QtWebChannel',

    # Unused standard library modules
    'tkinter',
    'unittest',
    'pytest',
    'doctest',
    'distutils',
    'setuptools',
    'email',
    'sqlite3',
    'concurrent',
    'http',
    'xml',
    'html',
    'pydoc',
    'ssl',
    'uuid',
    'pdb',
    'optparse',
    'getopt',
    'fractions',
    'decimal',
    'statistics',
    'hashlib',
    'hmac',
    'secrets',
    'ftplib',
    'imaplib',
    'poplib',
    'smtplib',
    'telnetlib',
    'nntplib',
    'cgi',
    'cgitb',
    'wsgiref',
    'mimetypes',
]

# =============================================================================
# ANALYSIS
# =============================================================================

a = Analysis(
    ['src/atlas/main.py'],
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes_list,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)


# =============================================================================
# EXECUTABLE
# =============================================================================

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Atlas_Portable_x64',
    debug=False,
    onefile=True,
    bootloader_ignore_signals=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/Icon.ico',
)
