#!/usr/bin/env bash
# install.sh — Add docforge to any repository as a git submodule or vendor copy.
#
# Usage:
#   ./install.sh                  Add as git submodule at vendor/docforge (default)
#   ./install.sh --vendor         Copy files into vendor/docforge (no git submodule)
#   ./install.sh --target /path   Target repository path (default: current directory)
#
# After running, add your config:
#   cp vendor/docforge/docforge.example.yml .docforge.yml
#   # Edit .docforge.yml with your project details
#
# Then add the GitHub Actions workflow:
#   cp vendor/docforge/templates/workflow.yml .github/workflows/docs.yml
#   git add .docforge.yml .github/workflows/docs.yml vendor/docforge
#   git commit -m "chore: add docforge documentation generator"

set -euo pipefail

# ── Logging ──────────────────────────────────────────────────────────────────
# Use script-helpers if available, otherwise fall back to plain echo.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_HELPERS_LOADED=0

if [ -f "${SCRIPT_DIR}/lib/logging.sh" ]; then
    # shellcheck source=/dev/null
    source "${SCRIPT_DIR}/lib/logging.sh"
    _HELPERS_LOADED=1
elif [ -f "${SCRIPT_DIR}/../script-helpers/lib/logging.sh" ]; then
    # shellcheck source=/dev/null
    source "${SCRIPT_DIR}/../script-helpers/lib/logging.sh"
    _HELPERS_LOADED=1
fi

_log_info() {
    if [ "${_HELPERS_LOADED}" -eq 1 ] && command -v log_info &>/dev/null; then
        log_info "$1"
    else
        echo "[docforge] $1"
    fi
}

_log_success() {
    if [ "${_HELPERS_LOADED}" -eq 1 ] && command -v log_success &>/dev/null; then
        log_success "$1"
    else
        echo "[docforge] ✓ $1"
    fi
}

_log_warn() {
    if [ "${_HELPERS_LOADED}" -eq 1 ] && command -v log_warn &>/dev/null; then
        log_warn "$1"
    else
        echo "[docforge] WARNING: $1" >&2
    fi
}

_log_error() {
    if [ "${_HELPERS_LOADED}" -eq 1 ] && command -v log_error &>/dev/null; then
        log_error "$1"
    else
        echo "[docforge] ERROR: $1" >&2
    fi
}

# ── Argument parsing ──────────────────────────────────────────────────────────
VENDOR_COPY=0
TARGET_REPO="."

while [[ $# -gt 0 ]]; do
    case "$1" in
        --vendor)
            VENDOR_COPY=1
            shift
            ;;
        --target)
            TARGET_REPO="${2:?--target requires a path argument}"
            shift 2
            ;;
        -h|--help)
            sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            _log_error "Unknown argument: $1"
            exit 1
            ;;
    esac
done

TARGET_REPO="$(cd "${TARGET_REPO}" && pwd)"
DOCFORGE_REPO="https://github.com/nikolareljin/docforge.git"
VENDOR_DIR="${TARGET_REPO}/vendor/docforge"

# ── Checks ────────────────────────────────────────────────────────────────────
if [ ! -d "${TARGET_REPO}/.git" ]; then
    _log_error "${TARGET_REPO} is not a git repository."
    exit 1
fi

if [ -d "${VENDOR_DIR}" ]; then
    _log_warn "vendor/docforge already exists in target repository."
    _log_warn "Remove it first if you want a fresh install."
    exit 1
fi

mkdir -p "${TARGET_REPO}/vendor"

# ── Install ───────────────────────────────────────────────────────────────────
if [ "${VENDOR_COPY}" -eq 1 ]; then
    _log_info "Copying docforge to vendor/docforge (--vendor mode)..."
    cp -r "${SCRIPT_DIR}" "${VENDOR_DIR}"
    # Remove .git from the copy to keep it a plain directory.
    rm -rf "${VENDOR_DIR}/.git"
    _log_success "Copied docforge to vendor/docforge"
else
    _log_info "Adding docforge as a git submodule at vendor/docforge..."
    git -C "${TARGET_REPO}" submodule add \
        --branch main \
        "${DOCFORGE_REPO}" \
        vendor/docforge
    _log_success "Added git submodule: vendor/docforge"
fi

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_FILE="${TARGET_REPO}/.docforge.yml"
if [ ! -f "${CONFIG_FILE}" ]; then
    _log_info "Creating .docforge.yml from example config..."
    cp "${VENDOR_DIR}/docforge.example.yml" "${CONFIG_FILE}"
    _log_success "Created .docforge.yml — edit it with your project details"
else
    _log_warn ".docforge.yml already exists — skipping config creation"
fi

# ── GitHub Actions workflow ───────────────────────────────────────────────────
WORKFLOWS_DIR="${TARGET_REPO}/.github/workflows"
WORKFLOW_FILE="${WORKFLOWS_DIR}/docs.yml"

mkdir -p "${WORKFLOWS_DIR}"

if [ ! -f "${WORKFLOW_FILE}" ]; then
    _log_info "Creating .github/workflows/docs.yml..."
    cp "${VENDOR_DIR}/templates/workflow.yml" "${WORKFLOW_FILE}"
    _log_success "Created .github/workflows/docs.yml"
else
    _log_warn ".github/workflows/docs.yml already exists — skipping workflow creation"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
_log_success "docforge installed successfully!"
echo ""
echo "  Next steps:"
echo "  1. Edit .docforge.yml with your project name and description"
echo "  2. No secrets needed — the default GitHub provider uses GITHUB_TOKEN automatically"
echo "  3. Commit everything:"
echo ""
echo "     git add .docforge.yml .github/workflows/docs.yml vendor/docforge"
echo "     git add .gitmodules  # if using submodule mode"
echo "     git commit -m \"chore: add docforge documentation generator\""
echo ""
echo "  4. Push to main/master — documentation will be generated automatically"
echo "  5. Or run locally:"
echo ""
echo "     pip install httpx pyyaml"
echo "     GITHUB_TOKEN=ghp_... python vendor/docforge/generate.py"
echo ""
