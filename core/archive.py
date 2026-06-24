import os
import tarfile
import time
import zipfile

import py7zr
import rarfile

from core.formats import ArchiveFormat
from core.platform_util import find_unrar


def _find_unrar() -> str | None:
    return find_unrar()


def _ensure_unrar():
    exe = _find_unrar()
    if exe:
        rarfile.UNRAR_TOOL = exe


class ArchiveEntry:
    def __init__(
        self, name: str, size: int,
        compressed_size: int, is_dir: bool,
        modified: float = 0.0,
    ):
        self.name = name
        self.size = size
        self.compressed_size = compressed_size
        self.is_dir = is_dir
        self.modified = modified

    @property
    def extension(self) -> str:
        _, ext = os.path.splitext(self.name)
        return ext.lower()


def archive_requires_password(path: str) -> bool:
    fmt = ArchiveFormat.from_extension(path)
    if fmt is None:
        return False
    if fmt in (ArchiveFormat.KPZ, ArchiveFormat.ZIP):
        try:
            with zipfile.ZipFile(path) as zf:
                for info in zf.infolist():
                    if info.flag_bits & 0x1:
                        return True
                return False
        except zipfile.BadZipFile:
            if fmt == ArchiveFormat.ZIP:
                return False
        except Exception:
            return False
        if fmt == ArchiveFormat.KPZ:
            try:
                with py7zr.SevenZipFile(path, "r") as sz:
                    return bool(sz.password_protected)
            except Exception:
                return False
        return False
    if fmt == ArchiveFormat.SEVEN_ZIP:
        try:
            with py7zr.SevenZipFile(path, "r") as sz:
                return bool(sz.password_protected)
        except Exception:
            return False
    if fmt == ArchiveFormat.RAR:
        try:
            _ensure_unrar()
            with rarfile.RarFile(path) as rf:
                return rf.needs_password()
        except (rarfile.RarCannotExec, Exception):
            return False
    return False


class Archive:
    def __init__(self, path: str):
        self.path = path
        self.format = ArchiveFormat.from_extension(path)

    def list_entries(self) -> list[ArchiveEntry]:
        fmt = self.format
        if fmt == ArchiveFormat.KPZ:
            return self._list_kpz()
        if fmt == ArchiveFormat.ZIP:
            return self._list_zip()
        if fmt in (ArchiveFormat.TAR, ArchiveFormat.GZIP,
                   ArchiveFormat.BZIP2, ArchiveFormat.XZ, ArchiveFormat.ZSTD):
            return self._list_tar()
        if fmt in (ArchiveFormat.SEVEN_ZIP, ArchiveFormat.ISO):
            return self._list_sevenzip()
        if fmt == ArchiveFormat.RAR:
            return self._list_rar()
        if fmt == ArchiveFormat.BZ2:
            return self._list_bz2()
        raise NotImplementedError(f"Cannot list {fmt}")

    def _list_kpz(self) -> list[ArchiveEntry]:
        try:
            return self._list_zip()
        except zipfile.BadZipFile:
            return self._list_sevenzip()

    def _list_zip(self) -> list[ArchiveEntry]:
        entries = []
        with zipfile.ZipFile(self.path, "r") as zf:
            for info in zf.infolist():
                dt = info.date_time
                modified = time.mktime(dt + (0, 0, -1)) if len(dt) == 6 else 0.0
                entries.append(ArchiveEntry(
                    name=info.filename,
                    size=info.file_size,
                    compressed_size=info.compress_size,
                    is_dir=info.filename.endswith("/"),
                    modified=modified,
                ))
        return entries

    def _list_tar(self) -> list[ArchiveEntry]:
        entries = []
        with tarfile.open(self.path, "r:*") as tf:
            for m in tf.getmembers():
                entries.append(ArchiveEntry(
                    name=m.name,
                    size=m.size,
                    compressed_size=0,
                    is_dir=m.isdir(),
                    modified=m.mtime or 0.0,
                ))
        return entries

    def _list_sevenzip(self) -> list[ArchiveEntry]:
        entries = []
        with py7zr.SevenZipFile(self.path, "r") as sz:
            for info in sz.list():
                entries.append(ArchiveEntry(
                    name=info.filename,
                    size=info.uncompressed,
                    compressed_size=info.compressed,
                    is_dir=info.is_directory,
                    modified=0.0,
                ))
        return entries

    def _list_rar(self) -> list[ArchiveEntry]:
        try:
            _ensure_unrar()
            entries = []
            with rarfile.RarFile(self.path) as rf:
                for info in rf.infolist():
                    entries.append(ArchiveEntry(
                        name=info.filename,
                        size=info.file_size,
                        compressed_size=info.compress_size,
                        is_dir=info.is_dir,
                        modified=0.0,
                    ))
            return entries
        except rarfile.RarCannotExec:
            raise RuntimeError(
                "RAR extraction requires WinRAR or unrar.exe installed on your system."
            )

    def _list_bz2(self) -> list[ArchiveEntry]:
        import bz2
        import os as _os
        name = _os.path.splitext(_os.path.basename(self.path))[0]
        try:
            with bz2.open(self.path, "rb") as f:
                data = f.read()
            return [ArchiveEntry(name=name, size=len(data), compressed_size=_os.path.getsize(self.path), is_dir=False)]
        except Exception:
            return []

    @property
    def entry_count(self) -> int:
        if self.format is None:
            return 0
        try:
            return len(self.list_entries())
        except Exception:
            return 0

    @property
    def total_size(self) -> int:
        if self.format is None:
            return 0
        try:
            return sum(e.size for e in self.list_entries())
        except Exception:
            return 0
