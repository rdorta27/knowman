"""install.sh only exists as a process, so it gets driven as one: a fake
`docker` on PATH reaches every branch without a daemon, and KNOWMAN_DRI_PATH
stands in for the device this host may or may not have."""

import shutil
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_INSTALL = _REPO_ROOT / "install.sh"

_WORKING_DOCKER = """#!/usr/bin/env bash
case "$1" in
	info) exit 0 ;;
	compose)
		case "$2" in
			version|up) exit 0 ;;
			ps) echo "healthy" ;;
			exec) echo "decision-log.md:L5-L5" ;;
		esac
		;;
esac
exit 0
"""

_UNREACHABLE_DOCKER = """#!/usr/bin/env bash
case "$1" in
	info)
		echo "Cannot connect to the Docker daemon at unix:///var/run/docker.sock." >&2
		exit 1
		;;
	compose) exit 0 ;;
esac
exit 0
"""

_FORBIDDEN_DOCKER = """#!/usr/bin/env bash
case "$1" in
	info)
		echo "permission denied while trying to connect to the Docker API" >&2
		exit 1
		;;
	compose) exit 0 ;;
esac
exit 0
"""


def _workspace(tmp_path: Path, docker_script: str | None) -> tuple[Path, dict]:
    work = tmp_path / "work"
    work.mkdir()
    shutil.copy(_INSTALL, work / "install.sh")
    shutil.copy(_REPO_ROOT / ".env.example", work / ".env.example")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("git", "sed", "grep", "cp", "bash", "cat", "tail", "sleep"):
        found = shutil.which(tool)
        if found:
            (bin_dir / tool).symlink_to(found)
    if docker_script is not None:
        docker = bin_dir / "docker"
        docker.write_text(docker_script)
        docker.chmod(0o755)

    return work, {"PATH": str(bin_dir)}


def _run(work: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "./install.sh"],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_missing_docker_prints_a_package_hint_and_stops(tmp_path: Path):
    work, env = _workspace(tmp_path, docker_script=None)

    result = _run(work, env)

    assert result.returncode != 0
    assert "'docker' not found" in result.stderr
    assert "install prerequisites above" in result.stderr


def test_an_unreachable_daemon_points_at_starting_it(tmp_path: Path):
    work, env = _workspace(tmp_path, _UNREACHABLE_DOCKER)

    result = _run(work, env)

    assert result.returncode != 0
    assert "daemon isn't reachable" in result.stderr
    assert "systemctl enable --now docker" in result.stderr


def test_a_permission_error_points_at_the_group_and_a_new_session(tmp_path: Path):
    work, env = _workspace(tmp_path, _FORBIDDEN_DOCKER)

    result = _run(work, env)

    assert result.returncode != 0
    assert "can't reach it" in result.stderr
    assert "usermod -aG docker" in result.stderr
    assert "already open" in result.stderr


def test_a_host_with_the_device_installs_in_gpu_mode(tmp_path: Path):
    work, env = _workspace(tmp_path, _WORKING_DOCKER)
    device = tmp_path / "dri"
    device.mkdir()
    env["KNOWMAN_DRI_PATH"] = str(device)

    result = _run(work, env)

    assert result.returncode == 0, result.stderr
    assert "compute: GPU" in result.stdout
    env_file = (work / ".env").read_text()
    assert "COMPOSE_FILE=docker-compose.yml:docker-compose.gpu.yml" in env_file
    assert "# COMPOSE_FILE=" not in env_file


def test_a_host_without_the_device_installs_in_cpu_mode(tmp_path: Path):
    work, env = _workspace(tmp_path, _WORKING_DOCKER)
    env["KNOWMAN_DRI_PATH"] = str(tmp_path / "absent")

    result = _run(work, env)

    assert result.returncode == 0, result.stderr
    assert "running on CPU" in result.stdout
    assert "compute: CPU" in result.stdout
    assert not (work / ".env").exists()


def test_the_install_fails_when_search_finds_no_evidence(tmp_path: Path):
    negative = _WORKING_DOCKER.replace(
        'exec) echo "decision-log.md:L5-L5" ;;',
        'exec) echo "No evidence found for that query." ;;',
    )
    work, env = _workspace(tmp_path, negative)
    env["KNOWMAN_DRI_PATH"] = str(tmp_path / "absent")

    result = _run(work, env)

    assert result.returncode != 0
    assert "search returned no evidence" in result.stderr


def test_the_install_pulls_the_configured_embeddings_model(tmp_path: Path):
    work, env = _workspace(tmp_path, _WORKING_DOCKER)
    env["KNOWMAN_DRI_PATH"] = str(tmp_path / "absent")
    env["EMBEDDINGS_MODEL"] = "some-other-model"

    result = _run(work, env)

    assert result.returncode == 0, result.stderr
    assert "some-other-model" in result.stdout


def test_the_install_never_runs_a_privileged_command():
    """It detects package managers to print hints; it never invokes one,
    and never elevates — the install says what to do, the human does it."""
    for line in _INSTALL.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "echo" in stripped:
            continue
        assert "sudo" not in stripped
        assert "install -y" not in stripped


def test_an_unknown_mode_is_rejected(tmp_path: Path):
    work, env = _workspace(tmp_path, _WORKING_DOCKER)

    result = subprocess.run(
        ["bash", "./install.sh", "--mode", "hybrid"],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode != 0
    assert "unknown mode 'hybrid'" in result.stderr
    assert "usage" in result.stderr


# --- native mode --------------------------------------------------------------

_READY = {
    "pacman": "exit 0",
    "postgres": "exit 0",
    "pg_isready": "exit 0",
    "psql": "echo 1",
    "ollama": "exit 0",
    "curl": "exit 0",
    "uv": 'if [ "$1 $2" = "tool dir" ]; then echo "$FAKE_BIN"; fi; exit 0',
    "knowman": 'if [ "$1" = "search" ]; then echo "decision-log.md:L5-L5"; fi; exit 0',
}


def _native(tmp_path: Path, **overrides: str | None) -> subprocess.CompletedProcess:
    """Run --mode native with every native prerequisite faked as ready, except
    the ones overridden: a string replaces a command's body, None removes it."""
    work, env = _workspace(tmp_path, docker_script=None)
    bin_dir = Path(env["PATH"])
    extension_dir = tmp_path / "extension"
    extension_dir.mkdir()
    (extension_dir / "vector.control").write_text("")

    commands = {**_READY, **overrides}
    for name, body in commands.items():
        if name.startswith("_") or body is None:
            continue
        fake = bin_dir / name
        fake.write_text(f"#!/usr/bin/env bash\n{body}\n")
        fake.chmod(0o755)

    env.update(
        {
            "FAKE_BIN": str(bin_dir),
            "KNOWMAN_PG_EXTENSION_DIR": str(extension_dir),
            "KNOWMAN_DRI_PATH": str(tmp_path / "absent"),
        }
    )
    if overrides.get("_extension_missing"):
        (extension_dir / "vector.control").unlink()
    if overrides.get("_device_present"):
        device = tmp_path / "dri"
        device.mkdir()
        env["KNOWMAN_DRI_PATH"] = str(device)

    return subprocess.run(
        ["bash", "./install.sh", "--mode", "native"],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_native_mode_is_refused_off_arch(tmp_path: Path):
    result = _native(tmp_path, pacman=None)

    assert result.returncode != 0
    assert "supports Arch only" in result.stderr


def test_native_mode_is_refused_while_the_docker_stack_runs(tmp_path: Path):
    result = _native(tmp_path, docker='echo "a1b2c3"')

    assert result.returncode != 0
    assert "docker compose down" in result.stderr


def test_native_mode_without_postgres_prints_the_packages(tmp_path: Path):
    result = _native(tmp_path, postgres=None)

    assert result.returncode != 0
    assert "sudo pacman -S postgresql pgvector" in result.stderr


def test_native_mode_without_the_extension_prints_pgvector(tmp_path: Path):
    result = _native(tmp_path, _extension_missing="yes")

    assert result.returncode != 0
    assert "sudo pacman -S pgvector" in result.stderr


def test_native_mode_with_postgres_down_prints_how_to_start_it(tmp_path: Path):
    result = _native(tmp_path, pg_isready="exit 2")

    assert result.returncode != 0
    assert "initdb" in result.stderr
    assert "systemctl enable --now postgresql" in result.stderr


def test_native_mode_without_the_role_prints_how_to_create_it(tmp_path: Path):
    result = _native(tmp_path, psql="exit 2")

    assert result.returncode != 0
    assert "CREATE ROLE knowman" in result.stderr
    assert "createdb" in result.stderr


def test_native_mode_without_ollama_prefers_vulkan_when_a_gpu_exists(tmp_path: Path):
    result = _native(tmp_path, ollama=None, _device_present="yes")

    assert result.returncode != 0
    assert "sudo pacman -S ollama-vulkan" in result.stderr


def test_native_mode_without_ollama_or_a_gpu_prints_plain_ollama(tmp_path: Path):
    result = _native(tmp_path, ollama=None)

    assert result.returncode != 0
    assert "sudo pacman -S ollama\n" in result.stderr


def test_native_mode_lists_every_unmet_step_in_one_run(tmp_path: Path):
    result = _native(tmp_path, postgres=None, ollama=None)

    assert result.returncode != 0
    assert "postgresql pgvector" in result.stderr
    assert "sudo pacman -S ollama" in result.stderr


def test_native_mode_with_everything_ready_installs_and_verifies(tmp_path: Path):
    result = _native(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "Postgres with pgvector is ready" in result.stdout
    assert "decision-log.md:L5-L5" in result.stdout
    assert "systemctl --user enable --now knowman-worker knowman-watcher" in result.stdout


def test_every_published_port_is_configurable_and_bound_to_localhost():
    compose = (_REPO_ROOT / "docker-compose.yml").read_text()
    for variable, default, target in [
        ("DB_PORT", "5432", "5432"),
        ("OLLAMA_PORT", "11434", "11434"),
        ("API_PORT", "8000", "8000"),
    ]:
        assert f'"127.0.0.1:${{{variable}:-{default}}}:{target}"' in compose
