#!/usr/bin/env bash
# End-to-end install check for a clean machine: verifies git/docker/compose
# are present (prints install instructions and exits if not — never installs
# anything with elevated privileges on its own), confirms the daemon is actually
# reachable, enables the GPU override when the host exposes /dev/dri, then builds
# and starts the Compose stack, seeds the dummy corpus, and confirms `knowman
# search` works.
set -euo pipefail

_fail() {
	echo "install: $1" >&2
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

_embeddings_model() {
	local from_env=""
	if [[ -f .env ]]; then
		from_env="$(sed -nE 's/^EMBEDDINGS_MODEL=(.*)$/\1/p' .env | tail -1)"
	fi
	EMBEDDINGS_MODEL="${EMBEDDINGS_MODEL:-${from_env:-qwen3-embedding:0.6b}}"
}

main() {
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
	_embeddings_model

	echo "install: building and starting the stack"
	docker compose up --build -d

	echo "install: waiting for db, ollama, and api to be healthy"
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
	result="$(docker compose exec -T api knowman search "por qué Postgres")"
	echo "${result}"
	[[ "${result}" != "No evidence found for that query." ]] || _fail "search returned no evidence — install did not complete correctly"

	echo "install: OK — knowman is running at http://localhost:8000 (compute: ${COMPUTE_MODE})"
	if [[ "${COMPUTE_MODE}" == "GPU" ]]; then
		echo "install: to force CPU, comment the COMPOSE_FILE line in .env and re-run 'docker compose up -d'"
	fi
}

main "$@"
