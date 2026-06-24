# Context Menu Integration Plan

## Problem
Desktop file only registers `.kpz` MIME type. Right-click Extract/Open actions don't appear for other archive formats (.zip, .7z, .rar, .tar, etc.). Nautilus scripts cluttered flat in Scripts menu.

## Solution
1. **Desktop file**: Keep `MimeType=application/x-kouprey-zip;inode/directory;` only — to not override system defaults for .zip/.tar/etc.
2. **Nautilus scripts submenu**: Move scripts into `~/.local/share/nautilus/scripts/Kouprey-Zip/` — Nautilus renders subdirectories as nested submenus, giving a clean "Kouprey-Zip >" context menu for ALL file types.

## Result: Context menu behavior

| File type | Main context menu | Kouprey-Zip submenu |
|-----------|------------------|---------------------|
| .kpz | Open with Kouprey-Zip (default handler) + Desktop Actions | Open in Viewer, Extract Here, Extract to Folder, Compress..., Quick .kpz |
| .zip, .7z, .rar, .tar, .gz, etc. | Open with system default (File Roller etc.) | Extract Here, Extract to Folder |
| Regular files / dirs | — | Compress..., Quick .kpz |

## Nautilus submenu scripts
```
~/.local/share/nautilus/scripts/Kouprey-Zip/
├── 01_Open in Viewer      → kouprey-zip --open
├── 02_Extract Here         → kouprey-zip --quick-extract-here
├── 03_Extract to Folder    → kouprey-zip --quick-extract-to
├── 04_Compress...          → kouprey-zip --compress
└── 05_Quick .kpz           → kouprey-zip --quick-compress
```

## Files Modified
- `install.sh`: `install_desktop_entry()` (MimeType kept minimal), `install_nautilus_scripts()` (subdirectory + cleanup)
- `installer/kouprey-zip.desktop`: Same MimeType
- Old flat scripts cleaned up on reinstall
