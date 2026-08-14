#!/usr/bin/env bash
set -euo pipefail

PINNED_VERSION="v1.1.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AGENTFIT_ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel)"
AGENTTEAMS_REPO="${AGENTFIT_ROOT}/../AgentTeams"
ENV_FILE="${AGENTFIT_ROOT}/.local-demo/agentteams/private.env"
INSTALL_LOG="${AGENTFIT_ROOT}/.local-demo/agentteams/install.log"
CHECK_ONLY=0

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  printf '%s\n' \
    'Usage: runtime/agentteams/install-prebuilt.sh [--check] [--env-file PATH] [--log-file PATH]' \
    '' \
    'Uses AgentTeams v1.1.2 official prebuilt images. It never builds images.' \
    'Full installer output is written to an ignored, mode-0600 private log.'
}

while (($#)); do
  case "$1" in
    --check)
      CHECK_ONLY=1
      shift
      ;;
    --env-file)
      (($# >= 2)) || die '--env-file requires a path'
      ENV_FILE="$2"
      shift 2
      ;;
    --log-file)
      (($# >= 2)) || die '--log-file requires a path'
      INSTALL_LOG="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

file_mode() {
  if stat -f '%Lp' -- "$1" >/dev/null 2>&1; then
    stat -f '%Lp' -- "$1"
  else
    stat -c '%a' -- "$1"
  fi
}

test -f "${ENV_FILE}" || die "private env file does not exist: ${ENV_FILE}"
test "$(file_mode "${ENV_FILE}")" = "600" || die 'private env file must have mode 0600'
git -C "${AGENTFIT_ROOT}" check-ignore -q -- "${ENV_FILE}" || die 'private env file must be ignored by Git'
[[ "${INSTALL_LOG}" != "${ENV_FILE}" ]] || die 'install log must not overwrite the private env file'
git -C "${AGENTFIT_ROOT}" check-ignore -q -- "${INSTALL_LOG}" || die 'install log must be ignored by Git'

set -a
# The file is owner-controlled, ignored, and mode 0600. Do not enable shell tracing.
# shellcheck disable=SC1090
. "${ENV_FILE}"
set +a

if [[ -n "${AGENTTEAMS_VERSION:-}" && "${AGENTTEAMS_VERSION}" != "${PINNED_VERSION}" ]]; then
  die "only ${PINNED_VERSION} is allowed for this M0 runtime"
fi

IMAGE_OVERRIDE_NAMES=(
  AGENTTEAMS_INSTALL_CONTROLLER_IMAGE
  AGENTTEAMS_INSTALL_DOCKER_PROXY_IMAGE
  AGENTTEAMS_INSTALL_EMBEDDED_IMAGE
  AGENTTEAMS_INSTALL_MANAGER_IMAGE
  AGENTTEAMS_INSTALL_MANAGER_COPAW_IMAGE
  AGENTTEAMS_INSTALL_WORKER_IMAGE
  AGENTTEAMS_INSTALL_COPAW_WORKER_IMAGE
  AGENTTEAMS_INSTALL_HERMES_WORKER_IMAGE
  AGENTTEAMS_INSTALL_OPENHUMAN_WORKER_IMAGE
)
for variable_name in "${IMAGE_OVERRIDE_NAMES[@]}"; do
  if [[ -n "${!variable_name:-}" ]]; then
    die 'image overrides are forbidden; use official prebuilt images'
  fi
done

require_private_value() {
  local variable_name="$1"
  local value="${!variable_name:-}"
  [[ -n "${value}" ]] || die "${variable_name} is required"
  case "${value}" in
    *'<'*'>'*|your-*|YOUR-*|replace-*|REPLACE-*)
      die "${variable_name} still contains a placeholder"
      ;;
  esac
}

require_private_value AGENTTEAMS_LLM_API_KEY
require_private_value AGENTTEAMS_OPENAI_BASE_URL
require_private_value AGENTTEAMS_DEFAULT_MODEL
[[ "${AGENTTEAMS_OPENAI_BASE_URL}" =~ ^https?:// ]] || die 'AGENTTEAMS_OPENAI_BASE_URL must use http or https'

INSTALLER="${AGENTTEAMS_REPO}/install/agentteams-install.sh"
test -f "${INSTALLER}" || die "reviewed AgentTeams installer is missing: ${INSTALLER}"

export AGENTTEAMS_NON_INTERACTIVE=1
export AGENTTEAMS_VERSION="${PINNED_VERSION}"
export AGENTTEAMS_LLM_PROVIDER="openai-compat"
export AGENTTEAMS_LOCAL_ONLY=1
export AGENTTEAMS_ROOT_DIR="${AGENTFIT_ROOT}/.local-demo/agentteams/platform"
export AGENTTEAMS_DATA_DIR="agentfit-agentteams-data"
export AGENTTEAMS_DASHBOARD=0
export AGENTTEAMS_UPGRADE_KEEP_ALL=1

if ((CHECK_ONLY)); then
  printf '%s\n' \
    'AgentTeams prebuilt install check' \
    "version=${AGENTTEAMS_VERSION}" \
    'mode=local-only' \
    "root_dir=${AGENTTEAMS_ROOT_DIR}" \
    "data_volume=${AGENTTEAMS_DATA_DIR}" \
    'dashboard=disabled' \
    'upgrade_mode=keep-all' \
    'image_source=official-prebuilt' \
    'api_key=configured' \
    'base_url=configured' \
    'default_model=configured'
  exit 0
fi

mkdir -p -- "${AGENTTEAMS_ROOT_DIR}"
cd -- "${AGENTTEAMS_REPO}/install"
umask 077
mkdir -p -- "$(dirname -- "${INSTALL_LOG}")"
: >"${INSTALL_LOG}"
chmod -- 600 "${INSTALL_LOG}"

if bash "${INSTALLER}" >"${INSTALL_LOG}" 2>&1; then
  printf 'AgentTeams prebuilt install completed; private install log: %s\n' "${INSTALL_LOG}"
else
  install_status=$?
  printf 'ERROR: AgentTeams prebuilt install failed; inspect private install log: %s\n' "${INSTALL_LOG}" >&2
  exit "${install_status}"
fi
