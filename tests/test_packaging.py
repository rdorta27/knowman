"""The data files the product reads at runtime used to be found by walking up
from the source tree, so they only existed inside a checkout. An installed
command — `uv tool install`, the native mode's path — shipped without them and
failed on its first `db-init`. Building the wheel is the only way to see what
actually travels."""

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def wheel(tmp_path_factory) -> zipfile.ZipFile:
    if shutil.which("uv") is None:
        pytest.skip("uv is needed to build the wheel")
    out = tmp_path_factory.mktemp("dist")
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out)],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        timeout=300,
    )
    (built,) = out.glob("*.whl")
    return zipfile.ZipFile(built)


@pytest.mark.parametrize(
    "resource",
    [
        "knowman/schema/001_init.sql",
        "knowman/prompts/ask_v1.txt",
        "knowman/evaldata/dataset.json",
        "knowman/static/dashboard.html",
    ],
)
def test_the_wheel_carries_every_runtime_data_file(wheel: zipfile.ZipFile, resource: str):
    assert resource in wheel.namelist()
