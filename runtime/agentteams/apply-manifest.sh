#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AGENTFIT_ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel)"
MANIFEST=""
APPLY_LOG="${AGENTFIT_ROOT}/.local-demo/agentteams/apply.log"
CONTAINER_COMMAND="${AGENTTEAMS_CONTAINER_COMMAND:-docker}"

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  printf '%s\n' \
    'Usage: runtime/agentteams/apply-manifest.sh --file PATH [--log-file PATH]' \
    '' \
    'Applies an AgentTeams YAML through the controller-native agt/hiclaw CLI.' \
    'Full apply output is written to an ignored, mode-0600 private log.'
}

while (($#)); do
  case "$1" in
    -f|--file)
      (($# >= 2)) || die '--file requires a path'
      MANIFEST="$2"
      shift 2
      ;;
    --log-file)
      (($# >= 2)) || die '--log-file requires a path'
      APPLY_LOG="$2"
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

[[ -n "${MANIFEST}" ]] || die '--file is required'
if [[ "${APPLY_LOG}" != /* ]]; then
  APPLY_LOG="${AGENTFIT_ROOT}/${APPLY_LOG}"
fi
test -f "${MANIFEST}" || die "manifest does not exist: ${MANIFEST}"
[[ "${APPLY_LOG}" != "${MANIFEST}" ]] || die 'apply log must not overwrite the manifest'
git -C "${AGENTFIT_ROOT}" check-ignore -q -- "${APPLY_LOG}" || die 'apply log must be ignored by Git'
command -v "${CONTAINER_COMMAND}" >/dev/null || die "container command is unavailable: ${CONTAINER_COMMAND}"

umask 077
mkdir -p -- "$(dirname -- "${APPLY_LOG}")"
: >"${APPLY_LOG}"
chmod 600 -- "${APPLY_LOG}"

controller="$(${CONTAINER_COMMAND} ps --format '{{.Names}}' 2>>"${APPLY_LOG}" | awk '/^(agentteams|hiclaw)-controller$/ { print; exit }')"
[[ -n "${controller}" ]] || die 'running AgentTeams controller was not found'

cli_path="$(${CONTAINER_COMMAND} exec "${controller}" sh -c \
  'if command -v agt >/dev/null; then command -v agt; elif command -v hiclaw >/dev/null; then command -v hiclaw; else exit 127; fi' \
  2>>"${APPLY_LOG}")" || die 'neither agt nor hiclaw exists in the AgentTeams controller'
cli_name="$(basename -- "${cli_path}")"
case "${cli_name}" in
  agt|hiclaw) ;;
  *) die "unsupported AgentTeams CLI: ${cli_name}" ;;
esac

remote_manifest="/tmp/agentfit-$(basename -- "${MANIFEST}")"
if ! ${CONTAINER_COMMAND} cp "${MANIFEST}" "${controller}:${remote_manifest}" >>"${APPLY_LOG}" 2>&1; then
  printf 'ERROR: manifest copy failed; inspect private apply log: %s\n' "${APPLY_LOG}" >&2
  exit 1
fi

if ${CONTAINER_COMMAND} exec "${controller}" "${cli_name}" apply -f "${remote_manifest}" >>"${APPLY_LOG}" 2>&1; then
  printf 'cli=%s\n' "${cli_name}"
  printf 'apply=accepted\n'
  printf 'private_log=%s\n' "${APPLY_LOG}"
else
  apply_status=$?
  printf 'ERROR: apply failed; cli=%s; inspect private apply log: %s\n' "${cli_name}" "${APPLY_LOG}" >&2
  exit "${apply_status}"
fi
