# Linux Port Plan

## Step 1 — Create `core/platform_util.py` (shared platform abstraction)
- `is_linux()` / `is_windows()` — sys.platform checks
- `get_system_fonts()` — Linux: Cantarell/Noto Sans/DejaVu Sans, Windows: Segoe UI
- `find_rar()` / `find_unrar()` — cross-platform shutil.which() + platform paths
- `create_app_lock()` — fcntl.flock on Linux, Win32 mutex on Windows

## Step 2 — Fix font stacks
Update `core/language.py`, `core/theme.py`, `ui/about_dialog.py` to use platform fonts.

## Step 3 — Fix single-instance locking
Replace `main.py:_is_first_instance()` with platform_util.create_app_lock().

## Step 4 — Fix RAR/unrar path detection
Update `core/compressor.py:_find_rar()` and `core/archive.py:_find_unrar()`.

## Step 5 — Remove SFX on Linux
Guard formats.py, compressor.py, compress_page.py to exclude SFX on Linux.

## Step 6 — Create `core/desktop.py` (Linux desktop integration)
- .desktop file + MIME type registration via freedesktop.org standards
- install_desktop(), uninstall_desktop(), is_installed()

## Step 7 — Update settings integration page
Platform-aware UI: core.desktop on Linux, core.registry on Windows.

## Step 8 — Guard platform-specific modules
- tools/pe_icon.py: add platform check
- core/registry.py: guard imports

## Step 9 — Build scripts
Create build.sh, update .spec, keep Windows scripts.

## Step 10 — Update README for Linux

## Step 11 — Test
