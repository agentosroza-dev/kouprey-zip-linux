#!/usr/bin/env bash
set -euo pipefail

# ── Kouprey-Zip Linux Installer ────────────────────────────────────────────
# Usage:
#   curl ... | bash                    # Install interactively
#   curl ... | bash -s -- --uninstall -y  # Uninstall non-interactively

REPO_OWNER="agentosroza-dev"
REPO_NAME="kouprey-zip"
BRANCH="main-linux"
INSTALL_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/kouprey-zip"
BIN_DIR="${HOME}/.local/bin"
BIN_PATH="${BIN_DIR}/kouprey-zip"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="${DESKTOP_DIR}/kouprey-zip.desktop"
MIME_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/mime/packages"
MIME_FILE="${MIME_DIR}/application-x-kouprey-zip.xml"
THUNAR_SENDTO_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/Thunar/sendto"
THUNAR_SENDTO_FILE="${THUNAR_SENDTO_DIR}/thunar-sendto-kouprey.desktop"
ICONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
ICON_SIZES=(16 32 48 64 128 256)

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { printf "${CYAN}[INFO]${NC} %s\n" "$*"; }
success() { printf "${GREEN}[OK]${NC} %s\n" "$*"; }
warn()    { printf "${YELLOW}[WARN]${NC} %s\n" "$*"; }
error()   { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; }

# ── Argument parsing ───────────────────────────────────────────────────────

MODE="install"
ASSUME_YES=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --uninstall) MODE="uninstall"; shift ;;
        -y|--yes)    ASSUME_YES=true; shift ;;
        *)           shift ;;
    esac
done

# ── Uninstall mode ─────────────────────────────────────────────────────────

do_uninstall() {
    if ! $ASSUME_YES; then
        printf "This will remove all Kouprey-Zip files. Continue? [y/N] "
        read -r ans
        [[ "$ans" =~ ^[Yy]$ ]] || { info "Uninstall cancelled."; exit 0; }
    fi

    info "Removing Kouprey-Zip..."

    rm -f "${BIN_PATH}"
    rm -f "${DESKTOP_FILE}"
    rm -f "${MIME_FILE}"
    rm -f "${THUNAR_SENDTO_FILE}"

    for size in "${ICON_SIZES[@]}"; do
        rm -f "${ICONS_DIR}/${size}x${size}/apps/kouprey-zip.png"
    done

    if [[ -d "${INSTALL_ROOT}" ]]; then
        rm -rf "${INSTALL_ROOT}"
    fi

    command -v update-mime-database &>/dev/null && \
        update-mime-database "${XDG_DATA_HOME:-$HOME/.local/share}/mime" 2>/dev/null || true
    command -v update-desktop-database &>/dev/null && \
        update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true

    success "Kouprey-Zip has been uninstalled."
    exit 0
}

[[ "$MODE" == "uninstall" ]] && do_uninstall

# ── Distribution detection ─────────────────────────────────────────────────

detect_distro() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        export ID
        export ID_LIKE
    fi
    if [[ "$(uname -s)" == "FreeBSD" ]]; then
        ID="freebsd"
    fi
    [[ -n "${ID:-}" ]] || ID="unknown"
}

detect_pkg_manager() {
    case "${ID}" in
        debian|ubuntu|zorin|linuxmint|pop|elementary|kali|trisquel|devuan)
            PKG="apt"; INSTALL_CMD="sudo apt install -y"
            QT_DEPS="libxcb-cursor0 libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0"
            VENV_PKG="python3-venv" ;;
        fedora|rhel|centos|almalinux|rocky|ol)
            if command -v dnf &>/dev/null; then PKG="dnf"; INSTALL_CMD="sudo dnf install -y"
            else PKG="yum"; INSTALL_CMD="sudo yum install -y"; fi
            QT_DEPS="libxcb-cursor libxcb xcb-util xcb-util-image xcb-util-keysyms xcb-util-wm"
            VENV_PKG="python3-virtualenv" ;;
        opensuse*|sles|suse)
            PKG="zypper"; INSTALL_CMD="sudo zypper install -y"
            QT_DEPS="libxcb-cursor0 libxcb-xinerama0"
            VENV_PKG="python3-venv" ;;
        arch|manjaro|endeavouros|garuda|arcolinux)
            PKG="pacman"; INSTALL_CMD="sudo pacman -S --noconfirm"
            QT_DEPS="libxcb-cursor xcb-util xcb-util-wm"
            VENV_PKG="python-virtualenv" ;;
        alpine)
            PKG="apk"; INSTALL_CMD="sudo apk add"
            QT_DEPS="libxcb-dev libxcb-cursor-dev"
            VENV_PKG="py3-virtualenv" ;;
        void*)
            PKG="xbps"; INSTALL_CMD="sudo xbps-install -y"
            QT_DEPS="libxcb-cursor"
            VENV_PKG="python3-virtualenv" ;;
        gentoo)
            PKG="emerge"; INSTALL_CMD="sudo emerge --noreplace"
            QT_DEPS="x11-libs/libxcb"
            VENV_PKG="dev-python/virtualenv" ;;
        nixos)
            PKG="nix-env"; INSTALL_CMD="nix-env -iA nixpkgs."
            QT_DEPS="libxcb"
            VENV_PKG="python3-virtualenv" ;;
        freebsd)
            PKG="pkg"; INSTALL_CMD="sudo pkg install -y"
            QT_DEPS="libxcb"
            VENV_PKG="python-virtualenv" ;;
        *)  PKG="unknown"; INSTALL_CMD=""; QT_DEPS=""; VENV_PKG="python3-venv" ;;
    esac
}

# ── Prerequisite checks ────────────────────────────────────────────────────

check_prereqs() {
    local missing=()

    if ! command -v curl &>/dev/null && ! command -v wget &>/dev/null; then
        missing+=("curl or wget")
    fi
    if ! command -v python3 &>/dev/null; then
        missing+=("python3")
    else
        local pyver
        pyver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        local major="${pyver%%.*}"
        local minor="${pyver#*.}"
        if (( major < 3 || (major == 3 && minor < 12) )); then
            error "Python 3.12+ is required (found ${pyver})."
            exit 1
        fi
    fi
    if ! command -v git &>/dev/null; then
        missing+=("git")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        if [[ "$PKG" != "unknown" ]]; then
            warn "Missing: ${missing[*]}"
            info "Install with: ${INSTALL_CMD} ${missing[*]}"
        else
            warn "Missing: ${missing[*]}. Please install manually."
        fi
    fi

    python3 -c 'import ensurepip' 2>/dev/null || {
        if [[ "$PKG" != "unknown" ]]; then
            warn "Missing python3-venv. Install with: ${INSTALL_CMD} ${VENV_PKG}"
        else
            warn "Missing python3-venv. Please install manually."
        fi
    }
}

# ── Download helpers ───────────────────────────────────────────────────────

download() {
    local url="$1" dest="$2"
    if command -v curl &>/dev/null; then
        curl -fsSL "$url" -o "$dest"
    else
        wget -q "$url" -O "$dest"
    fi
}

# ── Source installation ────────────────────────────────────────────────────

install_from_source() {
    info "Installing from source (branch: ${BRANCH})..."
    local tmpdir
    tmpdir=$(mktemp -d)
    trap "rm -rf ${tmpdir}" EXIT

    git clone --depth=1 --branch "${BRANCH}" \
        "https://github.com/${REPO_OWNER}/${REPO_NAME}.git" "${tmpdir}/repo"

    local use_venv=true
    if ! python3 -m venv --help &>/dev/null 2>&1; then
        if [[ "$PKG" == "apt" ]]; then
            warn "python3-venv not found. Installing..."
            sudo apt install -y python3.12-venv 2>/dev/null || sudo apt install -y python3-venv 2>/dev/null || {
                warn "Could not install python3-venv. Falling back to --user install."
                use_venv=false
            }
        else
            warn "python3-venv not found. Falling back to --user install."
            use_venv=false
        fi
    fi

    if $use_venv; then
        info "Creating virtual environment..."
        python3 -m venv "${INSTALL_ROOT}/venv"
        "${INSTALL_ROOT}/venv/bin/pip" install --upgrade pip -q
        "${INSTALL_ROOT}/venv/bin/pip" install -r "${tmpdir}/repo/requirements.txt" -q
    else
        info "Installing dependencies via --user..."
        python3 -m pip install --user --break-system-packages -r "${tmpdir}/repo/requirements.txt" -q
    fi

    cp -r "${tmpdir}/repo"/* "${INSTALL_ROOT}/" 2>/dev/null || true
    cp -r "${tmpdir}/repo"/.[!.]* "${INSTALL_ROOT}/" 2>/dev/null || true

    success "Source installation complete."
}

# ── Local build installation ───────────────────────────────────────────────

install_local() {
    local script_dir
    script_dir="$(cd "$(dirname "$0")" && pwd)"
    local local_dist="${script_dir}/dist/Kouprey-Zip"

    if [[ -f "${local_dist}/Kouprey-Zip" ]]; then
        info "Using local build from ${local_dist}..."
        rm -rf "${INSTALL_ROOT}"
        mkdir -p "${INSTALL_ROOT}"
        cp -r "${local_dist}"/* "${INSTALL_ROOT}/"
        success "Local build installed."
        return 0
    fi
    return 1
}

# ── Binary installation ────────────────────────────────────────────────────

install_binary() {
    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64)  arch="x86_64" ;;
        aarch64) arch="arm64" ;;
        *) return 1 ;;
    esac

    local release_url
    release_url="https://github.com/${REPO_OWNER}/${REPO_NAME}/releases/latest/download/kouprey-zip-linux-${arch}.tar.gz"

    info "Downloading pre-built binary..."
    local tmpdir
    tmpdir=$(mktemp -d)
    trap "rm -rf ${tmpdir}" EXIT

    local tarball="${tmpdir}/kouprey-zip.tar.gz"
    if download "${release_url}" "${tarball}" 2>/dev/null; then
        mkdir -p "${INSTALL_ROOT}"
        tar -xzf "${tarball}" -C "${INSTALL_ROOT}"
        success "Binary installation complete."
    else
        warn "No pre-built binary found. Falling back to source install."
        return 1
    fi
}

# ── Desktop integration ────────────────────────────────────────────────────

install_desktop_entry() {
    info "Installing desktop entry..."
    mkdir -p "${DESKTOP_DIR}"

    cat > "${DESKTOP_FILE}" << DESKTOP_EOF
[Desktop Entry]
Type=Application
Name=Kouprey-Zip
GenericName=File Archiver
Comment=A modern file archiver
Exec=${BIN_PATH} --open %f
TryExec=${BIN_PATH}
Icon=kouprey-zip
Terminal=false
Categories=Utility;Archiving;Compression;
MimeType=application/x-kouprey-zip;inode/directory;
StartupNotify=true
StartupWMClass=Kouprey-Zip
Actions=Compress;ExtractHere;ExtractTo;QuickKPZ;

[Desktop Action Compress]
Name=Add Archive with Kouprey
Exec=${BIN_PATH} --compress %F

[Desktop Action ExtractHere]
Name=Extract Here
Exec=${BIN_PATH} --quick-extract-here %f

[Desktop Action ExtractTo]
Name=Extract to Folder
Exec=${BIN_PATH} --quick-extract-to %f

[Desktop Action QuickKPZ]
Name=Create *.kpz
Exec=${BIN_PATH} --quick-compress %F
DESKTOP_EOF

    chmod 644 "${DESKTOP_FILE}"
    success "Desktop entry installed."
}

install_mime_type() {
    info "Registering .kpz MIME type..."
    mkdir -p "${MIME_DIR}"

    cat > "${MIME_FILE}" << 'MIME_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-kouprey-zip">
    <comment>Kouprey-Zip Archive</comment>
    <glob pattern="*.kpz"/>
    <icon name="kouprey-zip"/>
    <sub-class-of type="application/zip"/>
  </mime-type>
</mime-info>
MIME_EOF

    command -v update-mime-database &>/dev/null && \
        update-mime-database "${XDG_DATA_HOME:-$HOME/.local/share}/mime" 2>/dev/null || \
        info "update-mime-database not found. Install 'shared-mime-info' for full integration." || true

    success "MIME type registered."
}

install_icons() {
    info "Installing app icons..."
    local src_icon=""
    # Check both source-install and PyInstaller-bundled paths
    if [[ -f "${INSTALL_ROOT}/assets/icons/Kouprey Logo Variations.png" ]]; then
        src_icon="${INSTALL_ROOT}/assets/icons/Kouprey Logo Variations.png"
    elif [[ -f "${INSTALL_ROOT}/_internal/assets/icons/Kouprey Logo Variations.png" ]]; then
        src_icon="${INSTALL_ROOT}/_internal/assets/icons/Kouprey Logo Variations.png"
    else
        warn "No icon found in install root. Copying from installer directory..."
        local script_dir
        script_dir="$(cd "$(dirname "$0")" && pwd)"
        if [[ -f "${script_dir}/assets/icons/Kouprey Logo Variations.png" ]]; then
            src_icon="${script_dir}/assets/icons/Kouprey Logo Variations.png"
        fi
    fi

    if [[ -z "${src_icon}" ]]; then
        warn "No icon source found, skipping icon installation."
        return
    fi

    local has_convert=false
    command -v convert &>/dev/null && has_convert=true

    for size in "${ICON_SIZES[@]}"; do
        local icon_dir="${ICONS_DIR}/${size}x${size}/apps"
        mkdir -p "${icon_dir}"
        if $has_convert; then
            convert "${src_icon}" -resize "${size}x${size}" "${icon_dir}/kouprey-zip.png" 2>/dev/null || true
        elif [[ "$size" -eq 256 ]]; then
            cp "${src_icon}" "${icon_dir}/kouprey-zip.png"
        fi
    done
    command -v gtk-update-icon-cache &>/dev/null && \
        gtk-update-icon-cache -f -t "${ICONS_DIR}" 2>/dev/null || true
    success "Icons installed."
}

install_thunar_sendto() {
    mkdir -p "${THUNAR_SENDTO_DIR}"
    cat > "${THUNAR_SENDTO_FILE}" << THUNAR_EOF
[Desktop Entry]
Type=Application
Name=Compress with Kouprey
Exec=${BIN_PATH} --compress %F
Icon=kouprey-zip
THUNAR_EOF
    success "Thunar send-to entry installed."
}

# ── Nautilus (GNOME Files) scripts ──────────────────────────────────────────

NAUTILUS_SCRIPTS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/nautilus/scripts"

install_nautilus_scripts() {
    if [[ ! -d "${NAUTILUS_SCRIPTS_DIR}" ]]; then
        info "Nautilus scripts directory not found, skipping scripts."
        return
    fi

    info "Installing Nautilus context-menu scripts..."
    local subdir="${NAUTILUS_SCRIPTS_DIR}/Kouprey-Zip"
    rm -rf "${subdir}" 2>/dev/null || true
    mkdir -p "${subdir}"

    local launcher="#!/usr/bin/env bash\nexport PATH=\"\${HOME}/.local/bin:\${PATH}\"\n"

    # Open archive in viewer
    printf '%b' "${launcher}exec kouprey-zip --open \"\$@\"\n" > "${subdir}/01_Open in Viewer"
    chmod +x "${subdir}/01_Open in Viewer"

    # Extract Here
    printf '%b' "${launcher}exec kouprey-zip --quick-extract-here \"\$@\"\n" > "${subdir}/02_Extract Here"
    chmod +x "${subdir}/02_Extract Here"

    # Extract to Folder
    printf '%b' "${launcher}exec kouprey-zip --quick-extract-to \"\$@\"\n" > "${subdir}/03_Extract to Folder"
    chmod +x "${subdir}/03_Extract to Folder"

    # Compress (opens GUI)
    printf '%b' "${launcher}exec kouprey-zip --compress \"\$@\"\n" > "${subdir}/04_Compress..."
    chmod +x "${subdir}/04_Compress..."

    # Quick .kpz
    printf '%b' "${launcher}exec kouprey-zip --quick-compress \"\$@\"\n" > "${subdir}/05_Quick .kpz"
    chmod +x "${subdir}/05_Quick .kpz"

    # Clean up old flat scripts from previous install
    rm -f "${NAUTILUS_SCRIPTS_DIR}/Compress with Kouprey-Zip" \
          "${NAUTILUS_SCRIPTS_DIR}/Create .kpz with Kouprey" \
          "${NAUTILUS_SCRIPTS_DIR}/Extract Kouprey Here" \
          "${NAUTILUS_SCRIPTS_DIR}/Open with Kouprey-Zip" 2>/dev/null || true

    success "Nautilus scripts installed (Kouprey-Zip submenu)."
}

# ── CLI launcher ───────────────────────────────────────────────────────────

install_launcher() {
    info "Creating CLI launcher..."
    mkdir -p "${BIN_DIR}"

    if [[ -x "${INSTALL_ROOT}/venv/bin/python3" ]]; then
        local py="${INSTALL_ROOT}/venv/bin/python3"
    elif [[ -f "${INSTALL_ROOT}/Kouprey-Zip" ]]; then
        chmod +x "${INSTALL_ROOT}/Kouprey-Zip" 2>/dev/null || true
        local py="${INSTALL_ROOT}/Kouprey-Zip"
    else
        local py="python3 ${INSTALL_ROOT}/main.py"
    fi

    cat > "${BIN_PATH}" << LAUNCHER_EOF
#!/usr/bin/env bash
cd "${INSTALL_ROOT}"
exec ${py} "\$@"
LAUNCHER_EOF

    chmod +x "${BIN_PATH}"
    success "CLI launcher created at ${BIN_PATH}."
}

# ── Main installation flow ─────────────────────────────────────────────────

main() {
    echo ""
    echo "╔══════════════════════════════════════╗"
    echo "║   Kouprey-Zip Linux Installer v1.3  ║"
    echo "╚══════════════════════════════════════╝"
    echo ""

    detect_distro
    detect_pkg_manager
    info "Detected distribution: ${ID} (package manager: ${PKG})"

    check_prereqs

    mkdir -p "${INSTALL_ROOT}"

    if ! install_local; then
        if ! install_binary; then
            install_from_source
        fi
    fi

    install_launcher
    install_desktop_entry
    install_mime_type
    install_icons
    install_thunar_sendto
    install_nautilus_scripts

    # Register file association
    command -v xdg-mime &>/dev/null && \
        xdg-mime default kouprey-zip.desktop application/x-kouprey-zip 2>/dev/null || true

    command -v update-desktop-database &>/dev/null && \
        update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true

    echo ""
    success "Kouprey-Zip v1.3 installed successfully!"
    info "Run 'kouprey-zip' to start, or double-click any .kpz file."
    info "If the command is not found, add ~/.local/bin to your PATH:"
    info "  export PATH=\"\$PATH:\$HOME/.local/bin\""
    echo ""
}

main "$@"
