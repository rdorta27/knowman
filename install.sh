#!/usr/bin/env bash
# End-to-end install for a clean machine, in one of two modes:
#   --mode docker (default)  builds and starts the Compose stack
#   --mode native            runs on Postgres, pgvector, and Ollama installed on
#                            the host (Arch only)
# Either way it verifies prerequisites and prints how to fix anything missing —
# it never installs anything with elevated privileges on its own — then seeds the
# dummy corpus and confirms `knowman search` returns a real citation.
set -euo pipefail

readonly DEFAULT_MODEL="qwen3-embedding:0.6b"
readonly VERIFY_QUERY="por qué Postgres"
readonly NO_EVIDENCE="No evidence found for that query."

_fail() {
	echo "install: $1" >&2
	exit 1
}

_usage() {
	echo "usage: ./install.sh [--mode docker|native]" >&2
	exit 1
}

_check_command() {
	local cmd="$1" package_hint="$2"
	if command -v "$cmd" >/dev/null 2>&1; then
		return 0
	fi
	echo "install: '${cmd}' not found." >&2
	if command -v apt-get >/dev/null 2>&1; then
		echo "  Try: sudo apt-get install -y ${package_hint%%|*}" >&2
	elif command -v dnf >/dev/null 2>&1; then
		echo "  Try: sudo dnf install -y ${package_hint#*|}" >&2
	elif command -v pacman >/dev/null 2>&1; then
		echo "  Try: sudo pacman -S ${package_hint#*|}" >&2
	else
		echo "  Install it with your system's package manager." >&2
	fi
	return 1
}

# A value from the environment first, then .env, then the given default — the
# same precedence Docker Compose applies, so both modes agree on every setting.
_setting() {
	local name="$1" default="$2" from_env=""
	if [[ -n "${!name:-}" ]]; then
		printf '%s' "${!name}"
		return 0
	fi
	if [[ -f .env ]]; then
		from_env="$(sed -nE "s/^${name}=(.*)$/\\1/p" .env | tail -1)"
	fi
	printf '%s' "${from_env:-${default}}"
}

_resolve_settings() {
	DB_PORT="$(_setting DB_PORT 5432)"
	OLLAMA_PORT="$(_setting OLLAMA_PORT 11434)"
	API_PORT="$(_setting API_PORT 8000)"
	EMBEDDINGS_MODEL="$(_setting EMBEDDINGS_MODEL "${DEFAULT_MODEL}")"
}

# ---------------------------------------------------------------------------
# docker mode
# ---------------------------------------------------------------------------

# `docker compose version` answers from the CLI alone, so it passes with no
# daemon running and with no permission to reach it — the two states a freshly
# installed Docker is normally in. Only a real API call tells them apart.
_check_docker_usable() {
	local output
	if output="$(docker info 2>&1)"; then
		return 0
	fi
	if grep -qi 'permission denied' <<< "${output}"; then
		echo "install: docker is installed but this user can't reach it." >&2
		echo "  Try: sudo usermod -aG docker \"${USER:-$(id -un)}\", then log out and back in." >&2
		echo "  A new group never reaches a session that is already open — reopening a terminal is not enough." >&2
	else
		echo "install: docker is installed but its daemon isn't reachable." >&2
		echo "  Try: sudo systemctl enable --now docker" >&2
	fi
	return 1
}

# GPU is the default wherever the hardware allows it: a `devices:` entry for a
# missing /dev/dri fails at container start, before Ollama could fall back, so
# the override is selected here instead of living in docker-compose.yml.
# Ollama runs on CPU by itself when it sees no device — CPU needs no config.
# KNOWMAN_DRI_PATH is the device the GPU decision looks for; it exists so the
# decision can be exercised on a host whose hardware doesn't match the case
# under test, and defaults to the real path.
_select_compute_mode() {
	readonly GPU_COMPOSE_FILE="docker-compose.yml:docker-compose.gpu.yml"
	local dri_path="${KNOWMAN_DRI_PATH:-/dev/dri}"
	if [[ ! -e "${dri_path}" ]]; then
		COMPUTE_MODE="CPU"
		echo "install: no ${dri_path} on this host — running on CPU"
		return 0
	fi

	[[ -f .env ]] || cp .env.example .env
	if grep -q '^COMPOSE_FILE=' .env; then
		sed -i "s|^COMPOSE_FILE=.*|COMPOSE_FILE=${GPU_COMPOSE_FILE}|" .env
	elif grep -q '^# *COMPOSE_FILE=' .env; then
		sed -i "s|^# *COMPOSE_FILE=.*|COMPOSE_FILE=${GPU_COMPOSE_FILE}|" .env
	else
		printf '\nCOMPOSE_FILE=%s\n' "${GPU_COMPOSE_FILE}" >> .env
	fi
	COMPUTE_MODE="GPU"
	echo "install: ${dri_path} found — enabling the GPU override in .env"
}

_install_docker() {
	local missing=0
	_check_command git "git|git" || missing=1
	_check_command docker "docker.io|docker" || missing=1
	docker compose version >/dev/null 2>&1 || {
		echo "install: the 'docker compose' plugin is missing." >&2
		if command -v apt-get >/dev/null 2>&1; then
			echo "  Try: sudo apt-get install -y docker-compose-v2" >&2
		elif command -v dnf >/dev/null 2>&1; then
			echo "  Try: sudo dnf install -y docker-compose-plugin" >&2
		elif command -v pacman >/dev/null 2>&1; then
			echo "  Try: sudo pacman -S docker-compose" >&2
		else
			echo "  See https://docs.docker.com/compose/install/" >&2
		fi
		missing=1
	}
	[[ "${missing}" -eq 0 ]] || _fail "install prerequisites above, then re-run this script"
	_check_docker_usable || _fail "fix the Docker access above, then re-run this script"

	_select_compute_mode

	echo "install: building and starting the stack"
	docker compose up --build -d

	echo "install: waiting for db and ollama to be healthy"
	local waited=0
	while true; do
		# api has no healthcheck of its own; db and ollama do.
		local db_ok ollama_ok
		db_ok="$(docker compose ps db --format '{{.Health}}')"
		ollama_ok="$(docker compose ps ollama --format '{{.Health}}')"
		[[ "${db_ok}" == "healthy" && "${ollama_ok}" == "healthy" ]] && break
		waited=$((waited + 2))
		[[ "${waited}" -lt 120 ]] || _fail "db/ollama did not become healthy within 120s"
		sleep 2
	done

	echo "install: pulling the embeddings model (${EMBEDDINGS_MODEL})"
	docker compose exec -T ollama ollama pull "${EMBEDDINGS_MODEL}"

	echo "install: applying the database schema"
	docker compose exec -T api knowman db-init

	echo "install: seeding the dummy corpus"
	docker compose exec -T api knowman ingest

	echo "install: verifying search"
	local result
	result="$(docker compose exec -T api knowman search "${VERIFY_QUERY}")"
	echo "${result}"
	[[ "${result}" != "${NO_EVIDENCE}" ]] || _fail "search returned no evidence — install did not complete correctly"

	echo "install: OK — knowman is running at http://localhost:${API_PORT} (compute: ${COMPUTE_MODE})"
	if [[ "${COMPUTE_MODE}" == "GPU" ]]; then
		echo "install: to force CPU, comment the COMPOSE_FILE line in .env and re-run 'docker compose up -d'"
	fi
}

# ---------------------------------------------------------------------------
# native mode (Arch)
# ---------------------------------------------------------------------------

# Every check prints the exact fix and reports unmet instead of stopping, so one
# run lists everything that's missing; nothing here runs with elevated privileges.
# KNOWMAN_PG_EXTENSION_DIR stands in for the Postgres extension directory, for the
# same reason KNOWMAN_DRI_PATH stands in for the device.
_check_native_postgres() {
	local ext_dir="${KNOWMAN_PG_EXTENSION_DIR:-/usr/share/postgresql/extension}"

	if ! command -v postgres >/dev/null 2>&1; then
		echo "install: Postgres isn't installed." >&2
		echo "  Try: sudo pacman -S postgresql pgvector" >&2
		return 1
	fi
	if [[ ! -f "${ext_dir}/vector.control" ]]; then
		echo "install: the pgvector extension isn't installed." >&2
		echo "  Try: sudo pacman -S pgvector" >&2
		return 1
	fi
	if ! pg_isready -h 127.0.0.1 -p "${DB_PORT}" -q; then
		echo "install: Postgres isn't answering on port ${DB_PORT}." >&2
		echo "  If it has never been initialized:" >&2
		echo "    sudo -u postgres initdb -D /var/lib/postgres/data" >&2
		if [[ "${DB_PORT}" != "5432" ]]; then
			echo "  Set 'port = ${DB_PORT}' in /var/lib/postgres/data/postgresql.conf, then:" >&2
		fi
		echo "  Try: sudo systemctl enable --now postgresql" >&2
		return 1
	fi

	local has_vector
	if ! has_vector="$(psql "${DATABASE_URL}" -tAc "SELECT 1 FROM pg_extension WHERE extname = 'vector'" 2>/dev/null)"; then
		echo "install: can't connect as knowman to the knowman database on port ${DB_PORT}." >&2
		echo "  Try:" >&2
		echo "    sudo -u postgres psql -p ${DB_PORT} -c \"CREATE ROLE knowman LOGIN PASSWORD 'knowman'\"" >&2
		echo "    sudo -u postgres createdb -p ${DB_PORT} -O knowman knowman" >&2
		echo "    sudo -u postgres psql -p ${DB_PORT} -d knowman -c 'CREATE EXTENSION IF NOT EXISTS vector'" >&2
		return 1
	fi
	if [[ "${has_vector}" != "1" ]]; then
		echo "install: the vector extension isn't enabled in the knowman database." >&2
		echo "  Try: sudo -u postgres psql -p ${DB_PORT} -d knowman -c 'CREATE EXTENSION IF NOT EXISTS vector'" >&2
		return 1
	fi
	echo "install: Postgres with pgvector is ready on port ${DB_PORT}"
}

_check_native_ollama() {
	local dri_path="${KNOWMAN_DRI_PATH:-/dev/dri}"

	if ! command -v ollama >/dev/null 2>&1; then
		echo "install: Ollama isn't installed." >&2
		if [[ -e "${dri_path}" ]]; then
			echo "  Try: sudo pacman -S ollama-vulkan   (${dri_path} found — GPU acceleration)" >&2
		else
			echo "  Try: sudo pacman -S ollama" >&2
		fi
		return 1
	fi
	if ! curl -sf "${OLLAMA_URL}/api/tags" >/dev/null; then
		echo "install: Ollama isn't answering on port ${OLLAMA_PORT}." >&2
		if [[ "${OLLAMA_PORT}" != "11434" ]]; then
			echo "  Run 'sudo systemctl edit ollama' and add:" >&2
			echo "    [Service]" >&2
			echo "    Environment=\"OLLAMA_HOST=127.0.0.1:${OLLAMA_PORT}\"" >&2
		fi
		echo "  Try: sudo systemctl enable --now ollama" >&2
		return 1
	fi
	echo "install: Ollama is ready on port ${OLLAMA_PORT}"
}

# The Compose stack and the native services want the same ports, so only one
# can be active; the stack is checked by asking Compose, not by probing ports,
# since a native service answering on them is exactly what this mode expects.
_refuse_running_stack() {
	command -v docker >/dev/null 2>&1 || return 0
	local running
	running="$(docker compose ps -q 2>/dev/null || true)"
	if [[ -n "${running}" ]]; then
		echo "install: the Docker stack is running and holds the ports native mode needs." >&2
		echo "  Try: docker compose down" >&2
		return 1
	fi
}

_knowman_bin() {
	local bin_dir
	bin_dir="$(uv tool dir --bin 2>/dev/null || true)"
	if [[ -n "${bin_dir}" && -x "${bin_dir}/knowman" ]]; then
		printf '%s' "${bin_dir}/knowman"
	else
		printf 'knowman'
	fi
}

_install_native() {
	command -v pacman >/dev/null 2>&1 || _fail "native mode supports Arch only; use --mode docker elsewhere"
	_refuse_running_stack || _fail "stop the Docker stack, then re-run this script"

	export DATABASE_URL="postgresql://knowman:knowman@127.0.0.1:${DB_PORT}/knowman"
	export OLLAMA_URL="http://127.0.0.1:${OLLAMA_PORT}"
	export CORPUS_PATH
	CORPUS_PATH="$(_setting CORPUS_PATH corpus/dummy)"
	[[ "${CORPUS_PATH}" == /* ]] || CORPUS_PATH="${PWD}/${CORPUS_PATH}"

	local missing=0
	_check_command uv "uv|uv" || missing=1
	_check_native_postgres || missing=1
	_check_native_ollama || missing=1
	[[ "${missing}" -eq 0 ]] || _fail "fix the steps above, then re-run this script"

	echo "install: installing the knowman command"
	uv tool install --force .
	local knowman
	knowman="$(_knowman_bin)"

	echo "install: pulling the embeddings model (${EMBEDDINGS_MODEL})"
	OLLAMA_HOST="127.0.0.1:${OLLAMA_PORT}" ollama pull "${EMBEDDINGS_MODEL}"

	echo "install: applying the database schema"
	"${knowman}" db-init

	echo "install: seeding the dummy corpus"
	"${knowman}" ingest --path "${CORPUS_PATH}"

	echo "install: verifying search"
	local result
	result="$("${knowman}" search "${VERIFY_QUERY}")"
	echo "${result}"
	[[ "${result}" != "${NO_EVIDENCE}" ]] || _fail "search returned no evidence — install did not complete correctly"

	echo "install: OK — knowman is installed natively"
	echo "install: to keep the index in step with the notes, enable the worker and watcher:"
	echo "  mkdir -p ~/.config/knowman ~/.config/systemd/user"
	echo "  cp deploy/systemd/knowman-*.service ~/.config/systemd/user/"
	echo "  printf 'DATABASE_URL=%s\\nOLLAMA_URL=%s\\nCORPUS_PATH=%s\\n' \\"
	echo "    '${DATABASE_URL}' '${OLLAMA_URL}' '${CORPUS_PATH}' > ~/.config/knowman/env"
	echo "  systemctl --user daemon-reload"
	echo "  systemctl --user enable --now knowman-worker knowman-watcher"
}

main() {
	local mode="docker"
	while [[ $# -gt 0 ]]; do
		case "$1" in
			--mode)
				[[ $# -ge 2 ]] || _usage
				mode="$2"
				shift 2
				;;
			--mode=*)
				mode="${1#--mode=}"
				shift
				;;
			*) _usage ;;
		esac
	done

	_resolve_settings
	case "${mode}" in
		docker) _install_docker ;;
		native) _install_native ;;
		*) echo "install: unknown mode '${mode}'" >&2; _usage ;;
	esac
}

main "$@"
