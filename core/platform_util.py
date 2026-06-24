import fcntl
import os
import shutil
import sys


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_windows() -> bool:
    return sys.platform == "win32"


def _linux_data_dir() -> str:
    return os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))


def _linux_runtime_dir() -> str:
    return os.environ.get("XDG_RUNTIME_DIR", os.environ.get("TMPDIR", "/tmp"))


def get_system_fonts() -> list[str]:
    if is_linux():
        return [
            "AgentosUI",
            "Cantarell",
            "Noto Sans",
            "DejaVu Sans",
            "Ubuntu",
            "FreeSans",
            "sans-serif",
        ]
    return [
        "AgentosUI",
        "Segoe UI Variable Display",
        "Segoe UI",
        "sans-serif",
    ]


def find_rar() -> str | None:
    exe = shutil.which("rar")
    if exe:
        return exe
    if is_windows():
        for root in filter(os.path.isdir, [
            os.environ.get("PROGRAMFILES", "C:\\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"),
        ]):
            path = os.path.join(root, "WinRAR", "rar.exe")
            if os.path.isfile(path):
                return path
    return None


def find_unrar() -> str | None:
    exe = shutil.which("unrar")
    if exe:
        return exe
    if is_windows():
        for root in filter(os.path.isdir, [
            os.environ.get("PROGRAMFILES", "C:\\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"),
        ]):
            path = os.path.join(root, "WinRAR", "unrar.exe")
            if os.path.isfile(path):
                return path
    return None


def _get_lock_path() -> str:
    if is_linux():
        runtime = _linux_runtime_dir()
        return os.path.join(runtime, "kouprey_zip_instance.lock")
    return os.path.join(os.environ.get("TEMP", os.environ.get("TMP", "/tmp")), "kouprey_zip_instance.lock")


def create_app_lock() -> bool:
    if is_linux():
        lock_path = _get_lock_path()
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        try:
            global _lock_fd
            _lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
            fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (OSError, IOError):
            return False
    else:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        mutex = kernel32.CreateMutexW(None, False, "KoupreyZip_SingleInstance")
        if not mutex:
            return True
        return ctypes.get_last_error() != 183


def release_app_lock() -> None:
    if is_linux():
        try:
            global _lock_fd
            fcntl.flock(_lock_fd, fcntl.LOCK_UN)
            os.close(_lock_fd)
        except Exception:
            pass
