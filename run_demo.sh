#!/usr/bin/env bash
# Starts the FastAPI server and the Streamlit demo UI together, and stops
# both cleanly on Ctrl+C.
#
# Usage:
#   ./run_demo.sh
#
# Env vars (all optional):
#   API_PORT             default 8000
#   STREAMLIT_PORT        default 8501
#   FDC_API_KEY           required to start the API server; falls back to
#                         USDA's public DEMO_KEY (rate-limited) if unset

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

API_PORT="${API_PORT:-8000}"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"

# Loads a repo-root .env file, same convention as the Python side's
# load_dotenv() — so FDC_API_KEY/OPENFDA_API_KEY set there are picked up
# here too.
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [ -z "${FDC_API_KEY:-}" ]; then
  echo "No FDC_API_KEY found (env var or .env) — using USDA's public DEMO_KEY (rate-limited)."
  echo "Get your own free key: https://fdc.nal.usda.gov/api-key-signup"
  export FDC_API_KEY="DEMO_KEY"
fi

export SIMULATOR_API_BASE_URL="http://localhost:${API_PORT}"
# Belt-and-suspenders: some shells don't pick up editable installs
# reliably, so make sure the subprocess can import the package regardless.
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

PIDS=()

cleanup() {
  echo
  echo "Stopping..."
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
  wait >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

echo "Starting FastAPI server on http://localhost:${API_PORT} ..."
uvicorn mind_recovery_mvp.main:app --host 127.0.0.1 --port "${API_PORT}" &
PIDS+=("$!")

echo "Waiting for the server to become healthy..."
healthy=0
for _ in $(seq 1 30); do
  if curl -sf "http://localhost:${API_PORT}/health" >/dev/null 2>&1; then
    healthy=1
    break
  fi
  sleep 0.5
done
if [ "$healthy" -ne 1 ]; then
  echo "Server did not become healthy in time — check the output above." >&2
  exit 1
fi
echo "Server is up."

echo "Starting Streamlit app on http://localhost:${STREAMLIT_PORT} ..."
streamlit run streamlit_app.py --server.port "${STREAMLIT_PORT}" &
PIDS+=("$!")

echo
echo "Both running. Press Ctrl+C to stop."
wait
