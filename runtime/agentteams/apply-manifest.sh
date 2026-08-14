#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AGENTFIT_ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel)"
MANIFEST=""
APPLY_LOG="${AGENTFIT_ROOT}/.local-demo/agentteams/apply.log"
CONTAINER_COMMAND="${AGENTTEAMS_CONTAINER_COMMAND:-docker}"
REUSE_EXISTING_HUMAN=false

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  printf '%s\n' \
    'Usage: runtime/agentteams/apply-manifest.sh --file PATH [--log-file PATH] [--reuse-existing-human]' \
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
    --reuse-existing-human)
      REUSE_EXISTING_HUMAN=true
      shift
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

apply_manifest="${MANIFEST}"
filtered_manifest=""
human_update=""
command -v python3 >/dev/null || die 'python3 is required to inspect multi-document manifests'
python3 -c 'import yaml' >/dev/null 2>>"${APPLY_LOG}" || die \
  'PyYAML is required to inspect multi-document manifests; inspect the private apply log'
mapfile -t human_names < <(
  python3 -c \
    'import sys, yaml; print("\\n".join(str(d["metadata"]["name"]) for d in yaml.safe_load_all(open(sys.argv[1], encoding="utf-8")) if d and d.get("kind") == "Human"))' \
    "${MANIFEST}"
)
existing_humans=()
for human_name in "${human_names[@]}"; do
  if ${CONTAINER_COMMAND} exec "${controller}" "${cli_name}" get humans "${human_name}" -o json \
    >/dev/null 2>>"${APPLY_LOG}"; then
    existing_humans+=("${human_name}")
  fi
done

if ((${#existing_humans[@]})); then
  [[ "${REUSE_EXISTING_HUMAN}" == true ]] || die \
    'existing Human scope cannot be verified or updated on AgentTeams v1.1.2; inspect the applied manifest and rerun with --reuse-existing-human to acknowledge reuse'
  filtered_manifest="$(mktemp "${TMPDIR:-/tmp}/agentfit-manifest.XXXXXX.yaml")"
  chmod 600 -- "${filtered_manifest}"
  python3 -c \
    'import sys, yaml; source, target, *existing = sys.argv[1:]; docs = [d for d in yaml.safe_load_all(open(source, encoding="utf-8")) if d and not (d.get("kind") == "Human" and str(d.get("metadata", {}).get("name")) in existing)]; yaml.safe_dump_all(docs, open(target, "w", encoding="utf-8"), allow_unicode=True, explicit_start=True, sort_keys=False)' \
    "${MANIFEST}" "${filtered_manifest}" "${existing_humans[@]}"
  apply_manifest="${filtered_manifest}"
  human_update="skipped_existing"
fi

cleanup() {
  if [[ -n "${filtered_manifest}" ]]; then
    rm -f -- "${filtered_manifest}"
  fi
}
trap cleanup EXIT

remote_manifest="/tmp/agentfit-$(basename -- "${MANIFEST}")"
if ! ${CONTAINER_COMMAND} cp "${apply_manifest}" "${controller}:${remote_manifest}" >>"${APPLY_LOG}" 2>&1; then
  printf 'ERROR: manifest copy failed; inspect private apply log: %s\n' "${APPLY_LOG}" >&2
  exit 1
fi

if ${CONTAINER_COMMAND} exec "${controller}" "${cli_name}" apply -f "${remote_manifest}" >>"${APPLY_LOG}" 2>&1; then
  printf 'cli=%s\n' "${cli_name}"
  printf 'apply=accepted\n'
  if [[ -n "${human_update}" ]]; then
    printf 'human_update=%s\n' "${human_update}"
    printf 'human_reuse=explicitly_acknowledged\n'
  fi
  printf 'private_log=%s\n' "${APPLY_LOG}"
else
  apply_status=$?
  printf 'ERROR: apply failed; cli=%s; inspect private apply log: %s\n' "${cli_name}" "${APPLY_LOG}" >&2
  exit "${apply_status}"
fi
