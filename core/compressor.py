import os
import shutil
import sys
import subprocess
import tarfile
import zipfile

import py7zr

from core.formats import ArchiveFormat
from core.platform_util import find_rar


def _find_rar() -> str | None:
    return find_rar()


def _find_sfx_stub() -> str:
    from core.platform_util import is_linux
    if is_linux():
        raise RuntimeError("SFX (self-extracting executable) format is not supported on Linux.")

    patched = os.path.join(base, "assets", "sfx", "kouprey.sfx")
    if os.path.isfile(patched):
        return patched

    original = os.path.join(base, "assets", "sfx", "7z.sfx")
    if not os.path.isfile(original):
        prog = os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "7-Zip", "7z.sfx")
        if os.path.isfile(prog):
            original = prog
        else:
            prog86 = os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "7-Zip", "7z.sfx")
            if os.path.isfile(prog86):
                original = prog86

    if not os.path.isfile(original):
        raise RuntimeError("SFX stub not found. Install 7-Zip or place 7z.sfx in assets/sfx/.")

    ico = os.path.join(base, "assets", "icons", "Kouprey Logo Variations.ico")
    if getattr(sys, 'frozen', False):
        try:
            import tempfile
            tmp_stub = os.path.join(tempfile.mkdtemp(), "7z.sfx")
            shutil.copy2(original, tmp_stub)
            from tools.pe_icon import replace_exe_icon
            replace_exe_icon(tmp_stub, ico)
            return tmp_stub
        except Exception:
            return original

    shutil.copy2(original, patched)
    try:
        from tools.pe_icon import replace_exe_icon
        replace_exe_icon(patched, ico)
        return patched
    except Exception:
        os.unlink(patched)
        return original


class CompressResult:
    def __init__(self, success: bool, message: str = ""):
        self.success = success
        self.message = message


class Compressor:
    def __init__(self, output_path: str, source_paths: list[str], password: str = ""):
        self.output_path = output_path
        self.source_paths = source_paths
        self._password = password
        self._fmt = ArchiveFormat.from_extension(output_path)

    def compress(self, progress_callback=None) -> CompressResult:
        try:
            valid = self._all_files()
            if not valid:
                return CompressResult(False, "No valid source files found. Check that the files or folders exist.")
            if self._password:
                if self._fmt and not self._fmt.supports_password:
                    return CompressResult(False, "Password not supported for this format.")
                self._compress_encrypted(progress_callback)
            elif self._fmt in (ArchiveFormat.KPZ, ArchiveFormat.ZIP):
                self._compress_zip(progress_callback)
            elif self._fmt in (ArchiveFormat.TAR, ArchiveFormat.GZIP,
                               ArchiveFormat.BZIP2, ArchiveFormat.XZ, ArchiveFormat.ZSTD):
                self._compress_tar(progress_callback)
            elif self._fmt == ArchiveFormat.BZ2:
                self._compress_bz2(progress_callback)
            elif self._fmt == ArchiveFormat.SEVEN_ZIP:
                self._compress_sevenzip(progress_callback)
            elif self._fmt == ArchiveFormat.RAR:
                self._compress_rar(progress_callback)
            elif self._fmt == ArchiveFormat.SFX:
                self._compress_sfx(progress_callback)
            else:
                return CompressResult(False, f"Format not supported: {self._fmt}")
            return CompressResult(True)
        except Exception as e:
            return CompressResult(False, str(e))

    def _compress_encrypted(self, progress_callback=None) -> None:
        files = self._all_files()
        total = len(files)
        if self._fmt == ArchiveFormat.ZIP:
            import patoolib
            patoolib.create_archive(self.output_path, files, password=self._password)
            if progress_callback:
                progress_callback(total, total)
            return
        if self._fmt == ArchiveFormat.RAR:
            self._compress_rar(progress_callback)
            return
        if self._fmt == ArchiveFormat.SFX:
            self._compress_sfx(progress_callback)
            return
        with py7zr.SevenZipFile(self.output_path, "w", password=self._password) as sz:
            base = self._common_base()
            for i, file_path in enumerate(files):
                arcname = os.path.relpath(file_path, base)
                sz.write(file_path, arcname)
                if progress_callback:
                    progress_callback(i + 1, total)

    def _compress_zip(self, progress_callback=None) -> None:
        with zipfile.ZipFile(self.output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            files = self._all_files()
            total = len(files)
            for i, file_path in enumerate(files):
                arcname = os.path.relpath(file_path, self._common_base())
                zf.write(file_path, arcname)
                if progress_callback:
                    progress_callback(i + 1, total)

    def _compress_tar(self, progress_callback=None) -> None:
        mode_map = {
            ArchiveFormat.TAR: "w",
            ArchiveFormat.GZIP: "w:gz",
            ArchiveFormat.BZIP2: "w:bz2",
            ArchiveFormat.XZ: "w:xz",
        }
        mode = mode_map.get(self._fmt, "w")
        if self._fmt == ArchiveFormat.ZSTD:
            tmp_tar = self.output_path + ".tar"
            try:
                with tarfile.open(tmp_tar, "w") as tf:
                    files = self._all_files()
                    total = len(files)
                    for i, file_path in enumerate(files):
                        arcname = os.path.relpath(file_path, self._common_base())
                        tf.add(file_path, arcname)
                        if progress_callback:
                            progress_callback(i + 1, total)
                result = subprocess.run(
                    ["zstd", "-f", "-q", tmp_tar, "-o", self.output_path],
                    capture_output=True, text=True,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"zstd compression failed: {result.stderr.strip()}")
            finally:
                if os.path.isfile(tmp_tar):
                    os.unlink(tmp_tar)
        else:
            with tarfile.open(self.output_path, mode) as tf:
                files = self._all_files()
                total = len(files)
                for i, file_path in enumerate(files):
                    arcname = os.path.relpath(file_path, self._common_base())
                    tf.add(file_path, arcname)
                    if progress_callback:
                        progress_callback(i + 1, total)

    def _compress_bz2(self, progress_callback=None) -> None:
        import bz2
        files = self._all_files()
        total = len(files)
        if total == 1:
            with open(files[0], "rb") as fin, bz2.open(self.output_path, "wb") as fout:
                shutil.copyfileobj(fin, fout)
        else:
            tmp_tar = self.output_path + ".tar"
            try:
                with tarfile.open(tmp_tar, "w") as tf:
                    base = self._common_base()
                    for i, file_path in enumerate(files):
                        arcname = os.path.relpath(file_path, base)
                        tf.add(file_path, arcname)
                        if progress_callback:
                            progress_callback(i + 1, total)
                with open(tmp_tar, "rb") as fin, bz2.open(self.output_path, "wb") as fout:
                    shutil.copyfileobj(fin, fout)
            finally:
                if os.path.isfile(tmp_tar):
                    os.unlink(tmp_tar)
        if progress_callback:
            progress_callback(total, total)

    def _compress_rar(self, progress_callback=None) -> None:
        rar_exe = _find_rar()
        if not rar_exe:
            raise RuntimeError("RAR compression requires WinRAR installed on your system.")
        if os.path.exists(self.output_path):
            os.unlink(self.output_path)
        files = self._all_files()
        total = len(files)
        pw_args = [f"-p{self._password}"] if self._password else []
        result = subprocess.run(
            [rar_exe, "a", "-ep1", *pw_args, self.output_path, *files],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"RAR compression failed: {result.stderr.strip()}")
        if progress_callback:
            progress_callback(total, total)

    def _compress_sevenzip(self, progress_callback=None) -> None:
        files = self._all_files()
        total = len(files)
        with py7zr.SevenZipFile(self.output_path, "w") as sz:
            base = self._common_base()
            for i, file_path in enumerate(files):
                arcname = os.path.relpath(file_path, base)
                sz.write(file_path, arcname)
                if progress_callback:
                    progress_callback(i + 1, total)

    def _compress_sfx(self, progress_callback=None) -> None:
        import tempfile
        tmp = tempfile.mktemp(suffix=".7z")
        try:
            tmp_compressor = Compressor(tmp, self.source_paths, self._password)
            result = tmp_compressor.compress(progress_callback)
            if not result.success:
                raise RuntimeError(result.message)
            self._make_sfx(tmp)
        finally:
            if os.path.isfile(tmp):
                os.unlink(tmp)

    def _make_sfx(self, archive_7z_path: str) -> None:
        stub = _find_sfx_stub()
        with open(self.output_path, "wb") as dest:
            with open(stub, "rb") as sfx:
                shutil.copyfileobj(sfx, dest)
            with open(archive_7z_path, "rb") as src:
                shutil.copyfileobj(src, dest)

    def _all_files(self) -> list[str]:
        files: list[str] = []
        for path in self.source_paths:
            if os.path.isfile(path):
                files.append(path)
            elif os.path.isdir(path):
                for root, _, filenames in os.walk(path):
                    for f in filenames:
                        files.append(os.path.join(root, f))
        return files

    def _common_base(self) -> str:
        if len(self.source_paths) == 1:
            return os.path.dirname(self.source_paths[0])
        common = os.path.commonpath(self.source_paths)
        if os.path.isdir(common):
            return common
        return os.path.dirname(common)
