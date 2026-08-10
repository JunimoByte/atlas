# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file for Atlas application.

- Dynamically collects all submodules in 'backup', 'lib', 'display', and 'ui'
  for hidden imports.
- Includes resources and configuration files.
- Detects which Qt binding is installed at build time and excludes the other
  to prevent PyInstaller's 'multiple Qt bindings' error.
"""

import importlib
import pkgutil
import struct
from typing import List

from PyInstaller.building.build_main import EXE, PYZ, Analysis
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

print(f"main.spec: bundling {_active_qt}, excluding {_excluded_qt}")

# PyInstaller builds for the Python interpreter's bitness. This works on
# Windows 7 with Python 3.8 as well as current Windows releases.
_target_arch = "x86_64" if struct.calcsize("P") == 8 else "x86"
_portable_name = f"Atlas-{_target_arch}-Portable"

print(f"main.spec: creating {_portable_name}.exe")

# =============================================================================
# RESOURCES & CONFIGS
# =============================================================================

datas = [
    ('assets/icons/*', 'assets/icons'),
    ('assets/images/*', 'assets/images'),
    ('configs/*', 'configs'),
]

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
    'QtWebEngineWidgets', 'QtWebEngineCore', 'QtWebKit', 'QtWebKitWidgets',
    'QtMultimedia', 'QtNetwork', 'QtNetworkAuth', 'QtSql', 'QtTest',
    'QtTextToSpeech', 'QtWebSockets', 'QtOpenGL', 'QtSerialPort',
    'QtSensors', 'QtNfc', 'QtQuick', 'QtQml', 'Qt3DCore', 'Qt3DRender',
    'Qt3DInput', 'Qt3DLogic', 'Qt3DExtras', 'QtBluetooth', 'QtPositioning',
    'QtPrintSupport', 'QtQuickWidgets', 'QtRemoteObjects', 'QtSerialBus',
    'QtWebChannel',
]

_offline_module_prefixes = (
    'PyQt5.QtNetwork', 'PyQt5.QtNetworkAuth', 'PyQt5.QtWebEngine',
    'PyQt5.QtWebKit', 'PyQt5.QtWebSockets', 'PyQt5.QtBluetooth',
    'PyQt5.QtRemoteObjects', 'PyQt5.QtWebChannel', 'PyQt6.QtNetwork',
    'PyQt6.QtNetworkAuth', 'PyQt6.QtWebEngine', 'PyQt6.QtWebSockets',
    'PyQt6.QtBluetooth', 'PyQt6.QtRemoteObjects', 'PyQt6.QtWebChannel',
    'socket', 'ssl', 'urllib', 'http', 'ftplib', 'imaplib', 'poplib',
    'smtplib', 'telnetlib', 'nntplib', 'wsgiref',
)

_offline_binary_markers = (
    'QtWebEngine', 'QtWebKit', 'QtWebSockets', 'Qt5Bluetooth',
    'Qt6Bluetooth', 'Qt5RemoteObjects', 'Qt6RemoteObjects', 'Qt5WebChannel',
    'Qt6WebChannel',
)

_standard_library_excludes = [
    'tkinter', 'unittest', 'pytest', 'doctest', 'distutils', 'setuptools',
    'email', 'sqlite3', 'concurrent', 'http', 'xml', 'html', 'pydoc',
    'socket', 'ssl', 'urllib', 'uuid', 'pdb', 'optparse', 'getopt',
    'fractions', 'decimal', 'statistics', 'hashlib', 'hmac', 'secrets',
    'ftplib', 'imaplib', 'poplib', 'smtplib', 'telnetlib', 'nntplib', 'cgi',
    'cgitb', 'wsgiref', 'mimetypes',
]

excludes_list = (
    [_excluded_qt]
    + [
        f'{binding}.{module}'
        for binding in ('PyQt5', 'PyQt6')
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
        normalized_path = path.replace('\\', '.').replace('/', '.')
        return any(
            normalized_path == prefix
            or normalized_path.startswith(prefix + '.')
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
            'Offline packaging policy blocked: ' + ', '.join(blocked)
        )


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

enforce_offline_payload(a)

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
    name=_portable_name,
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
