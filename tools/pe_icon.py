import os
import struct
import sys


def replace_exe_icon(exe_path: str, ico_path: str, max_icons: int = 5) -> None:
    if sys.platform != "win32":
        return

    import ctypes
    from ctypes import wintypes

    MI = lambda v: ctypes.cast(ctypes.c_void_p(v), wintypes.LPCWSTR)

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
    kernel32.BeginUpdateResourceW.restype = wintypes.HANDLE
    kernel32.UpdateResourceW.argtypes = [
        wintypes.HANDLE, wintypes.LPCWSTR, wintypes.LPCWSTR,
        wintypes.WORD, wintypes.LPVOID, wintypes.DWORD,
    ]
    kernel32.UpdateResourceW.restype = wintypes.BOOL
    kernel32.EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
    kernel32.EndUpdateResourceW.restype = wintypes.BOOL

    with open(ico_path, "rb") as f:
        ico_data = f.read()

    count = struct.unpack_from("<H", ico_data, 4)[0]

    icon_entries = []
    off = 6
    for i in range(count):
        w, h, colors, _rsv, planes, bpp, sz, img_off = struct.unpack_from(
            "<BBBBHHII", ico_data, off
        )
        actual_w = w if w != 0 else 256
        icon_entries.append((actual_w, bpp, sz, img_off, list(ico_data[off:off+12])))
        off += 16

    icon_entries.sort(key=lambda x: (-x[0], -x[1]))
    seen = set()
    chosen = []
    for w, bpp, sz, img_off, entry12 in icon_entries:
        if w in seen:
            continue
        seen.add(w)
        chosen.append((w, bpp, sz, img_off, bytes(entry12)))
        if len(chosen) >= max_icons:
            break

    new_count = len(chosen)
    group_dir = struct.pack("<HHH", 0, 1, new_count)

    icon_images = []
    for idx, (w, bpp, sz, img_off, entry12) in enumerate(chosen, 1):
        group_dir += entry12 + struct.pack("<H", idx)
        icon_images.append(ico_data[img_off : img_off + sz])

    h = kernel32.BeginUpdateResourceW(exe_path, False)
    if not h:
        raise OSError(f"BeginUpdateResourceW error: {ctypes.get_last_error()}")

    try:
        for i, img in enumerate(icon_images, 1):
            buf = ctypes.create_string_buffer(img, len(img))
            if not kernel32.UpdateResourceW(h, MI(3), MI(i), 0, buf, len(img)):
                raise OSError(f"UpdateResourceW icon {i}: {ctypes.get_last_error()}")

        gbuf = ctypes.create_string_buffer(group_dir, len(group_dir))
        if not kernel32.UpdateResourceW(h, MI(14), MI(1), 0, gbuf, len(group_dir)):
            raise OSError(f"UpdateResourceW group: {ctypes.get_last_error()}")

        if not kernel32.EndUpdateResourceW(h, False):
            raise OSError(f"EndUpdateResourceW: {ctypes.get_last_error()}")
    except Exception:
        kernel32.EndUpdateResourceW(h, True)
        raise
