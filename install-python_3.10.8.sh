#!/usr/bin/env bash
#set -euo pipefail

TARGET_VERSION="3.10.8"
VERSION="$TARGET_VERSION"
PREFIX="${PREFIX:-/opt/python/${VERSION}}"
BIN_LINK_DIR="${BIN_LINK_DIR:-/usr/local/bin}"
SRC_URL="https://www.python.org/ftp/python/${VERSION}/Python-${VERSION}.tar.xz"
SRC_MD5="e92356b012ed4d0e09675131d39b1bde"
BUILD_JOBS="${BUILD_JOBS:-$(nproc)}"

log() {
  printf '[install-python_3.10.8] %s\n' "$*"
}

fail() {
  printf '[install-python_3.10.8] ERROR: %s\n' "$*" >&2
  exit 1
}

run_as_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    fail "This step requires root privileges, but sudo is not installed."
  fi
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

verify_supported_os() {
  if [[ ! -r /etc/os-release ]]; then
    fail "Cannot determine OS. This installer is intended for Ubuntu/Debian systems."
  fi

  # shellcheck disable=SC1091
  source /etc/os-release
  case "${ID:-}" in
    ubuntu|debian)
      ;;
    *)
      fail "Unsupported OS: ${PRETTY_NAME:-unknown}. This installer currently supports Ubuntu/Debian."
      ;;
  esac
}

install_build_dependencies() {
  log "Installing build dependencies with apt."
  run_as_root apt-get update
  run_as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    libbz2-dev \
    libffi-dev \
    libgdbm-compat-dev \
    libgdbm-dev \
    liblzma-dev \
    libncursesw5-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    tk-dev \
    uuid-dev \
    xz-utils \
    zlib1g-dev
}

ensure_symlinks() {
  run_as_root install -d "${BIN_LINK_DIR}"
  run_as_root ln -sfn "${PREFIX}/bin/python3.10" "${BIN_LINK_DIR}/python3.10"
  run_as_root ln -sfn "${PREFIX}/bin/pip3.10" "${BIN_LINK_DIR}/pip3.10"
}

main() {
  require_command md5sum
  require_command tar
  verify_supported_os

  if [[ -x "${PREFIX}/bin/python3.10" ]]; then
    installed_version="$("${PREFIX}/bin/python3.10" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
    if [[ "${installed_version}" == "${TARGET_VERSION}" ]]; then
      log "Python ${TARGET_VERSION} is already installed at ${PREFIX}."
      ensure_symlinks
      log "Verified: $("${BIN_LINK_DIR}/python3.10" --version)"
      exit 0
    fi
  fi

  install_build_dependencies
  require_command curl
  require_command make
  require_command gcc

  workdir="$(mktemp -d)"
  trap 'rm -rf "${workdir}"' EXIT

  tarball="${workdir}/Python-${VERSION}.tar.xz"
  src_dir="${workdir}/Python-${TARGET_VERSION}"

  log "Downloading Python ${TARGET_VERSION} source from python.org."
  curl -fsSL "${SRC_URL}" -o "${tarball}"

  log "Verifying archive checksum."
  actual_md5="$(md5sum "${tarball}" | awk '{print $1}')"
  if [[ "${actual_md5}" != "${SRC_MD5}" ]]; then
    fail "Checksum mismatch for ${tarball}. Expected ${SRC_MD5}, got ${actual_md5}."
  fi

  log "Extracting source archive."
  tar -xJf "${tarball}" -C "${workdir}"

  log "Configuring build under ${PREFIX}."
  echo tarball=$tarball workdir=$workdir src_dir=$src_dir PREFIX=$PREFIX
  cd "${src_dir}"
  ./configure --prefix="${PREFIX}" --with-ensurepip=install

  log "Building Python ${TARGET_VERSION} with ${BUILD_JOBS} parallel job(s)."
  make -j"${BUILD_JOBS}"

  log "Installing Python ${TARGET_VERSION} into ${PREFIX}."
  run_as_root mkdir -p "${PREFIX}"
  run_as_root make altinstall

  ensure_symlinks

  installed_version="$("${PREFIX}/bin/python3.10" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
  if [[ "${installed_version}" != "$TARGET_VERSION" ]]; then
    fail "Installed version mismatch. Expected ${TARGET_VERSION}, got ${installed_version}."
  fi

  log "Installation complete."
  log "python3.10: $("${BIN_LINK_DIR}/python3.10" --version)"
  log "pip3.10: $("${BIN_LINK_DIR}/pip3.10" --version)"
  log "This does not replace /usr/bin/python3."
}

main "$@"
