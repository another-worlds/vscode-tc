#!/usr/bin/env bash
# Grand Contract v1.0 — Google VM Bootstrap Script
# Target: Debian Trixie (13), NVIDIA L4 GPU
# Usage:  sudo bash setup-gvm.sh
# Effect: Installs CUDA toolkit, Docker CE, nvidia-container-toolkit,
#         then launches the stack via docker compose up -d
set -euo pipefail
REPO_DIR="${REPO_DIR:-/opt/vscode-tc}"
COMPOSE_FILE="${REPO_DIR}/docker-compose.yml"
MIN_CUDA_MAJOR=12

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[SETUP]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
die()  { echo -e "${RED}[FAIL]${NC}  $*" >&2; exit 1; }

# ── 1. Privilege check ────────────────────────────────────────────
check_root() {
    # Invariant: must run as root for package installation
    [[ $EUID -eq 0 ]] || die "Run with sudo: sudo bash $0"
}

# ── 2. OS verification ────────────────────────────────────────────
check_os() {
    # Invariant: Debian Trixie (13)
    local codename
    codename=$(. /etc/os-release && echo "${VERSION_CODENAME:-unknown}")
    [[ "$codename" == "trixie" ]] \
        || warn "Expected Debian trixie, got: $codename. Proceeding anyway."
    log "OS: $(. /etc/os-release && echo "$PRETTY_NAME")"
}

# ── 3. NVIDIA GPU & driver check ──────────────────────────────────
check_gpu() {
    # Invariant: nvidia-smi must be present with CUDA >= MIN_CUDA_MAJOR
    command -v nvidia-smi &>/dev/null || {
        warn "nvidia-smi not found. Installing NVIDIA drivers..."
        install_nvidia_driver
    }
    local cuda_ver
    cuda_ver=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)
    log "NVIDIA driver: $cuda_ver"

    # Check CUDA major via nvcc or nvidia-smi CUDA version field
    local cuda_major
    cuda_major=$(nvidia-smi 2>/dev/null | grep -oP 'CUDA Version: \K[0-9]+' | head -1 || echo 0)
    (( cuda_major >= MIN_CUDA_MAJOR )) \
        || warn "CUDA $cuda_major < required $MIN_CUDA_MAJOR. Consider upgrading driver."

    # List detected GPUs
    log "Detected GPUs:"
    nvidia-smi -L
}

# ── 4. Install NVIDIA driver (if absent) ─────────────────────────
install_nvidia_driver() {
    # Uses Debian non-free firmware + nvidia-detect
    apt-get update -qq
    apt-get install -y --no-install-recommends \
        nvidia-detect linux-headers-$(uname -r) || true
    local suggested
    suggested=$(nvidia-detect 2>/dev/null | grep 'Recommended' | awk '{print $NF}' || echo "nvidia-driver")
    log "Installing driver package: $suggested"
    apt-get install -y --no-install-recommends "$suggested"
    log "Driver installed. A reboot may be required if this is a fresh install."
}

# ── 5. Install Docker CE ──────────────────────────────────────────
install_docker() {
    if command -v docker &>/dev/null; then
        log "Docker already installed: $(docker --version)"
        return
    fi
    log "Installing Docker CE..."
    apt-get update -qq
    apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg lsb-release
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
    log "Docker CE installed: $(docker --version)"
}

# ── 6. Install nvidia-container-toolkit ──────────────────────────
install_nvidia_container_toolkit() {
    if dpkg -l | grep -q nvidia-container-toolkit 2>/dev/null; then
        log "nvidia-container-toolkit already installed."
        return
    fi
    log "Installing nvidia-container-toolkit..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
        | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
        | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
        > /etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get update -qq
    apt-get install -y --no-install-recommends nvidia-container-toolkit
    # Configure Docker runtime to use nvidia
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker
    log "nvidia-container-toolkit installed and Docker runtime configured."
}

# ── 7. Verify Docker GPU access ───────────────────────────────────
verify_docker_gpu() {
    log "Verifying Docker GPU access..."
    docker run --rm --gpus all nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi \
        || die "Docker GPU access failed. Check nvidia-container-toolkit setup."
    log "Docker GPU access: OK"
}

# ── 8. Install git (if absent) ────────────────────────────────────
install_git() {
    command -v git &>/dev/null || apt-get install -y --no-install-recommends git
}

# ── 9. Clone or update repo ───────────────────────────────────────
setup_repo() {
    # Invariant: REPO_URL env must be set, or repo already cloned at REPO_DIR
    if [[ -d "$REPO_DIR/.git" ]]; then
        log "Repo exists at $REPO_DIR — pulling latest..."
        git -C "$REPO_DIR" pull --ff-only
    else
        [[ -n "${REPO_URL:-}" ]] || die "Set REPO_URL env to clone the repository."
        log "Cloning $REPO_URL → $REPO_DIR"
        git clone "$REPO_URL" "$REPO_DIR"
    fi
}

# ── 10. Create .env from example (if missing) ────────────────────
setup_env() {
    local env_file="${REPO_DIR}/.env"
    if [[ ! -f "$env_file" ]]; then
        cp "${REPO_DIR}/.env.example" "$env_file"
        warn ".env created from .env.example — EDIT secrets before using in production!"
    else
        log ".env already exists — skipping copy."
    fi
}

# ── 11. Pre-pull images for faster startup ────────────────────────
prepull_images() {
    log "Pre-pulling base images..."
    docker compose -f "$COMPOSE_FILE" pull --ignore-pull-failures || true
}

# ── 12. Build and launch ──────────────────────────────────────────
launch() {
    log "Building and launching stack (docker compose up -d)..."
    docker compose -f "$COMPOSE_FILE" up --build -d
    log "Stack launched. Check status with: docker compose -f $COMPOSE_FILE ps"
}

# ── Main ──────────────────────────────────────────────────────────
main() {
    check_root
    check_os
    install_git
    install_docker
    check_gpu
    install_nvidia_container_toolkit
    verify_docker_gpu
    setup_repo
    setup_env
    prepull_images
    launch
    log "Setup complete. App available at http://$(hostname -I | awk '{print $1}')/"
}

main "$@"
