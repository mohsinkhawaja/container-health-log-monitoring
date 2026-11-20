#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

PYTHON="${PYTHON:-python}"
# Own a disposable Compose project so cleanup never touches another lab.
export COMPOSE_PROJECT_NAME="qa-health-lab-${BASHPID}"
export DEMO_PORT="${DEMO_PORT:-18080}"
export DEMO_EMIT_ERROR=0
export MONITOR_PROJECT="$COMPOSE_PROJECT_NAME"
export MONITOR_LIVE=1
mkdir -p artifacts

cleanup() {
    docker compose logs --no-color > artifacts/compose.log 2>&1 || true
    docker compose down --remove-orphans || true
}
trap cleanup EXIT

docker compose up --build --wait --wait-timeout 90
"$PYTHON" -m pytest --junitxml=artifacts/pytest.xml
args=(--project "$COMPOSE_PROJECT_NAME" --url "http://127.0.0.1:$DEMO_PORT/health")
"$PYTHON" -m monitor.cli "${args[@]}" > artifacts/healthy.json

DEMO_EMIT_ERROR=1 docker compose up --wait --wait-timeout 90
set +e
"$PYTHON" -m monitor.cli "${args[@]}" > artifacts/seeded-error.json
result=$?
set -e
if [[ $result -ne 1 ]]; then
    echo "Expected exit 1 for the seeded error. Got $result." >&2
    exit 1
fi
"$PYTHON" -c 'import json; from pathlib import Path; data = json.loads(Path("artifacts/seeded-error.json").read_text()); assert [check["name"] for check in data["checks"] if not check["passed"]] == ["container_logs"]'
