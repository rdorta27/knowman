#!/usr/bin/env bash
# End-to-end install check for a clean machine: verifies git/docker/compose
# are present (prints install instructions and exits if not — never installs
# anything with elevated privileges on its own), then builds and starts the
# Compose stack, seeds the dummy corpus, and confirms `knowman search` works.
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
		echo "  Try: sudo apt-get install -y ${package_hint}" >&2
	elif command -v dnf >/dev/null 2>&1; then
		echo "  Try: sudo dnf install -y ${package_hint}" >&2
	elif command -v pacman >/dev/null 2>&1; then
		echo "  Try: sudo pacman -S ${package_hint}" >&2
	else
		echo "  Install it with your system's package manager." >&2
	fi
	return 1
}

main() {
	local missing=0
	_check_command git git || missing=1
	_check_command docker docker || missing=1
	docker compose version >/dev/null 2>&1 || {
		echo "install: 'docker compose' plugin not found (see https://docs.docker.com/compose/install/)." >&2
		missing=1
	}
	[[ "${missing}" -eq 0 ]] || _fail "install prerequisites above, then re-run this script"

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

	echo "install: pulling the embeddings model"
	docker compose exec -T ollama ollama pull qwen3-embedding:0.6b

	echo "install: applying the database schema"
	docker compose exec -T api knowman db-init

	echo "install: seeding the dummy corpus"
	docker compose exec -T api knowman ingest

	echo "install: verifying search"
	local result
	result="$(docker compose exec -T api knowman search "por qué Postgres")"
	echo "${result}"
	[[ "${result}" != "No evidence found for that query." ]] || _fail "search returned no evidence — install did not complete correctly"

	echo "install: OK — knowman is running at http://localhost:8000"
}

main "$@"
