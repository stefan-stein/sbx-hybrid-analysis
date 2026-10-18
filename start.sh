#!/usr/bin/env bash
set -euo pipefail

setup_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mode=safe
workspace=
case ${1:-} in
  "") ;;
  --rw)
    mode=rw
    workspace=${2:-"$PWD"}
    if (( $# > 2 )); then
      printf '%s\n' 'Usage: ./start.sh [--rw [workspace-directory]]' >&2
      exit 1
    fi
    ;;
  *)
    printf '%s\n' 'Usage: ./start.sh [--rw [workspace-directory]]' >&2
    exit 1
    ;;
esac

if [[ $mode == safe ]]; then
  sandbox_name=${SANDBOX_NAME:-malware-sandbox-v1-1}
else
  sandbox_name=${SANDBOX_NAME:-malware-sandbox-v1-1-rw}
fi

if ! command -v sbx >/dev/null 2>&1; then
  printf '%s\n' 'Install Docker Sandboxes (sbx) first: https://docs.docker.com/ai/sandboxes/install/' >&2
  exit 1
fi
if [[ $mode == rw && ! -d "$workspace" ]]; then
  printf '%s\n' 'The workspace must be an existing directory.' >&2
  exit 1
fi
if [[ $mode == rw ]]; then
  workspace=$(CDPATH= cd -- "$workspace" && pwd)
fi

if [[ -f "$setup_dir/kit/spec.yaml" ]]; then
  printf '%s\n' 'Legacy kit/spec.yaml found. Remove it before using the v3 workload descriptor.' >&2
  exit 1
fi

# Source builds need an OCI-capable driver. Select Docker's managed kit
# builder by default; its docker-container driver can export OCI images.
# An explicitly empty value preserves host building with BUILDX_BUILDER.
export SBX_KIT_BUILDER="${SBX_KIT_BUILDER-sandbox}"

if [[ $mode == rw ]]; then
  # Direct mode: the selected host directory is writable from the sandbox.
  exec sbx run --name "$sandbox_name" "$setup_dir/kit" "$workspace"
fi

# Safe mode: `sbx run` without a workspace would implicitly mount the current
# directory, so create a mountless sandbox first and then attach by name.
if ! sbx inspect "$sandbox_name" >/dev/null 2>&1; then
  sbx create --name "$sandbox_name" "$setup_dir/kit"
fi
printf '%s\n' \
  "Safe mode: no host directory is mounted." \
  "Transfer files with: sbx cp <source> $sandbox_name:/home/agent/workspace/" \
  "Copy reports out with: sbx cp $sandbox_name:/home/agent/workspace/reports/ <destination>"
exec sbx run --name "$sandbox_name"
