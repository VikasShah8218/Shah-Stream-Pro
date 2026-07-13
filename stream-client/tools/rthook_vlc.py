"""PyInstaller runtime hook: point python-vlc at bundled libVLC + plugins.

Only relevant for a fully standalone build (one that bundles libVLC — see
BUILD.md). This is a safe no-op when those files are not bundled: python-vlc
then falls back to a system-installed VLC as usual.
"""

import os
import sys

_base = getattr(sys, "_MEIPASS", None)
if _base:
    _lib = os.path.join(_base, "libvlc.dll")
    _plugins = os.path.join(_base, "vlc", "plugins")
    if os.path.isfile(_lib):
        os.environ.setdefault("PYTHON_VLC_LIB_PATH", _lib)
    if os.path.isdir(_plugins):
        os.environ.setdefault("PYTHON_VLC_MODULE_PATH", _plugins)
