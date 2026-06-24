from core.formats import ArchiveFormat


MAGIC_MAP: dict[bytes, ArchiveFormat] = {
    b"PK\x03\x04": ArchiveFormat.ZIP,
    b"PK\x05\x06": ArchiveFormat.ZIP,
    b"PK\x07\x08": ArchiveFormat.ZIP,
    b"37\x7a\xbc\xaf\x27\x1c": ArchiveFormat.SEVEN_ZIP,
    b"Rar!\x1a\x07": ArchiveFormat.RAR,
    b"\x1f\x8b": ArchiveFormat.GZIP,
    b"\xfd7zXZ\x00": ArchiveFormat.XZ,
    b"ustar": ArchiveFormat.TAR,
    b"BZh": ArchiveFormat.BZ2,
}


def detect_format(file_path: str) -> ArchiveFormat | None:
    ext_fmt = ArchiveFormat.from_extension(file_path)
    if ext_fmt == ArchiveFormat.KPZ:
        return ext_fmt
    with open(file_path, "rb") as f:
        header = f.read(32)
    for magic, fmt in MAGIC_MAP.items():
        if header.startswith(magic):
            return fmt
    return ext_fmt


def is_archive(file_path: str) -> bool:
    return detect_format(file_path) is not None
