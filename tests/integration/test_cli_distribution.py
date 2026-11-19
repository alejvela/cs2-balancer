import os
import subprocess
import sys
import tomllib
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_information_commands_are_lightweight(tmp_path):
    probe = """
import sys
sys.path.insert(0, sys.argv[1])
def audit(event, args):
    if event == "import" and args[0].split(".")[0] in {
        "application", "configuration", "importers", "scrapers", "optimizer",
        "scoring", "exporters", "models", "main", "webbrowser", "requests",
    }:
        raise AssertionError(args[0])
    if event in {"socket.connect", "webbrowser.open", "subprocess.Popen"}:
        raise AssertionError(event)
sys.addaudithook(audit)
import cs2_balancer_cli
for command in (["--help"], ["--version"], ["balance", "--help"], ["tournament-report", "--help"]):
    assert cs2_balancer_cli.main(command) == 0
"""
    subprocess.run(
        [sys.executable, "-IB", "-c", probe, str(ROOT)], cwd=tmp_path, check=True
    )
    assert not list(tmp_path.iterdir())


def test_installed_wheel_console_script(tmp_path):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"
    wheels = tmp_path / "wheels"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "-w",
            str(wheels),
            str(ROOT),
        ],
        cwd=tmp_path,
        env=env,
        check=True,
    )
    (wheel,) = wheels.glob("*.whl")
    prefix = tmp_path / "installed"
    venv.EnvBuilder(with_pip=True).create(prefix)
    scripts = prefix / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    command = scripts / ("cs2-balancer.exe" if os.name == "nt" else "cs2-balancer")
    subprocess.run(
        [python, "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
        cwd=tmp_path,
        env=env,
        check=True,
    )
    work = tmp_path / "operator"
    work.mkdir()
    assert not work.is_relative_to(ROOT)
    with (ROOT / "pyproject.toml").open("rb") as project:
        version = tomllib.load(project)["project"]["version"]
    for argv, code, text in (
        (["--version"], 0, f"cs2-balancer {version}"),
        (["--help"], 0, "tournament-report"),
        (["balance", "--help"], 0, "Balance a roster"),
        (["tournament-report", "--help"], 0, "Generate a tournament report"),
        ([], 2, "usage:"),
        (["balance"], 2, "not available yet"),
        (["tournament-report"], 2, "not available yet"),
        (["other"], 2, "invalid choice"),
        (["--ver"], 2, "unrecognized arguments"),
    ):
        result = subprocess.run(
            [command, *argv], cwd=work, env=env, text=True, capture_output=True
        )
        assert result.returncode == code, result.stderr
        assert text in (result.stderr if code else result.stdout)
    assert not list(work.iterdir())
