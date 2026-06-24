import os
import shutil
import subprocess
import sys


_DATA_HOME = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
_HOME_BIN = os.path.join(os.path.expanduser("~"), ".local", "bin")

_BIN_DIR = _HOME_BIN
_BIN_PATH = os.path.join(_BIN_DIR, "kouprey-zip")

_DESKTOP_DIR = os.path.join(_DATA_HOME, "applications")
_DESKTOP_FILE = os.path.join(_DESKTOP_DIR, "kouprey-zip.desktop")

_MIME_DIR = os.path.join(_DATA_HOME, "mime", "packages")
_MIME_FILE = os.path.join(_MIME_DIR, "application-x-kouprey-zip.xml")

_ICONS_DIR = os.path.join(_DATA_HOME, "icons", "hicolor")

_THUNAR_SENDTO_DIR = os.path.join(_DATA_HOME, "Thunar", "sendto")
_THUNAR_SENDTO_FILE = os.path.join(_THUNAR_SENDTO_DIR, "thunar-sendto-kouprey.desktop")

_ICON_SIZES = [16, 32, 48, 64, 128, 256]

_INSTALL_ROOT = os.path.join(_DATA_HOME, "kouprey-zip")


def _app_executable() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    py = sys.executable
    script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"
    )
    return f'"{py}" "{script}"'


def _install_launcher() -> None:
    os.makedirs(_BIN_DIR, exist_ok=True)

    if getattr(sys, "frozen", False):
        exe = sys.executable
        app_dir = os.path.dirname(exe)
    else:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if getattr(sys, "frozen", False):
        py = f'"{exe}"'
    elif os.path.isfile(os.path.join(app_dir, "main.py")):
        py = f'"{sys.executable}" "{os.path.join(app_dir, "main.py")}"'
    else:
        py = f'"{sys.executable}" "{os.path.join(_INSTALL_ROOT, "main.py")}"'

    with open(_BIN_PATH, "w") as f:
        f.write(f'#!/usr/bin/env bash\ncd "{app_dir}"\nexec {py} "$@"\n')
    os.chmod(_BIN_PATH, 0o755)

    if getattr(sys, "frozen", False):
        exe_path = exe
        if not os.access(exe_path, os.X_OK):
            try:
                os.chmod(exe_path, 0o755)
            except Exception:
                pass


_ARCHIVE_EXTS = [
    ".kpz", ".zip", ".7z", ".rar",
    ".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst", ".iso",
]


def _desktop_content() -> str:
    return f"""[Desktop Entry]
Type=Application
Name=Kouprey-Zip
GenericName=File Archiver
Comment=A modern file archiver
Exec={_BIN_PATH} --open %f
TryExec={_BIN_PATH}
Icon=kouprey-zip
Terminal=false
Categories=Utility;Archiving;Compression;
MimeType=application/x-kouprey-zip;
StartupNotify=true
StartupWMClass=Kouprey-Zip
Actions=Compress;ExtractHere;ExtractTo;QuickKPZ;

[Desktop Action Compress]
Name=Add Archive with Kouprey
Exec={_BIN_PATH} --compress %F

[Desktop Action ExtractHere]
Name=Extract Here
Exec={_BIN_PATH} --quick-extract-here %f

[Desktop Action ExtractTo]
Name=Extract to Folder
Exec={_BIN_PATH} --quick-extract-to %f

[Desktop Action QuickKPZ]
Name=Create *.kpz
Exec={_BIN_PATH} --quick-compress %F
"""


def _mime_content() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-kouprey-zip">
    <comment>Kouprey-Zip Archive</comment>
    <glob pattern="*.kpz"/>
    <icon name="kouprey-zip"/>
    <sub-class-of type="application/zip"/>
  </mime-type>
</mime-info>
"""


def _install_icons() -> None:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(base, "assets", "icons", "Kouprey Logo Variations.png")
    if not os.path.isfile(src):
        return

    for size in _ICON_SIZES:
        icon_dir = os.path.join(_ICONS_DIR, f"{size}x{size}", "apps")
        os.makedirs(icon_dir, exist_ok=True)
        dest = os.path.join(icon_dir, "kouprey-zip.png")
        try:
            shutil.copy2(src, dest)
        except Exception:
            pass

    try:
        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", _ICONS_DIR],
            capture_output=True,
        )
    except Exception:
        pass


def _install_thunar_sendto() -> None:
    os.makedirs(_THUNAR_SENDTO_DIR, exist_ok=True)
    with open(_THUNAR_SENDTO_FILE, "w") as f:
        f.write("""[Desktop Entry]
Type=Application
Name=Compress with Kouprey
Exec=k"""
                f"""ouprey-zip --compress %F
Icon=kouprey-zip
""")
    os.chmod(_THUNAR_SENDTO_FILE, 0o644)


def _uninstall_icons() -> None:
    for size in _ICON_SIZES:
        icon_dir = os.path.join(_ICONS_DIR, f"{size}x{size}", "apps")
        icon_file = os.path.join(icon_dir, "kouprey-zip.png")
        try:
            os.remove(icon_file)
        except OSError:
            pass

    try:
        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", _ICONS_DIR],
            capture_output=True,
        )
    except Exception:
        pass


def _uninstall_thunar_sendto() -> None:
    try:
        os.remove(_THUNAR_SENDTO_FILE)
    except OSError:
        pass


def install_desktop() -> None:
    _install_launcher()

    os.makedirs(_DESKTOP_DIR, exist_ok=True)
    with open(_DESKTOP_FILE, "w") as f:
        f.write(_desktop_content())
    os.chmod(_DESKTOP_FILE, 0o644)

    os.makedirs(_MIME_DIR, exist_ok=True)
    with open(_MIME_FILE, "w") as f:
        f.write(_mime_content())

    _install_icons()
    _install_thunar_sendto()

    try:
        subprocess.run(
            ["update-mime-database", os.path.join(_DATA_HOME, "mime")],
            capture_output=True,
        )
    except Exception:
        pass

    try:
        subprocess.run(
            ["update-desktop-database", _DESKTOP_DIR],
            capture_output=True,
        )
    except Exception:
        pass


def uninstall_desktop() -> None:
    for f in (_DESKTOP_FILE, _MIME_FILE, _BIN_PATH):
        try:
            os.remove(f)
        except OSError:
            pass

    _uninstall_icons()
    _uninstall_thunar_sendto()

    try:
        subprocess.run(
            ["update-mime-database", os.path.join(_DATA_HOME, "mime")],
            capture_output=True,
        )
    except Exception:
        pass

    try:
        subprocess.run(
            ["update-desktop-database", _DESKTOP_DIR],
            capture_output=True,
        )
    except Exception:
        pass


def is_installed() -> bool:
    return os.path.isfile(_DESKTOP_FILE)
