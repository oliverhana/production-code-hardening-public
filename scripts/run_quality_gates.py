#!/usr/bin/env python3
"""Run bounded, shell-free Python release gates and emit JSON evidence."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


MAX_CAPTURE_CHARS = 20_000
COMPILE_EXCLUDE = r"(^|/)(\.git|\.venv|venv|node_modules|build|dist|\.tox|\.nox|__pycache__)(/|$)"


@dataclass(frozen=True)
class Gate:
    name: str
    command: tuple[str, ...]
    required: bool = True


@dataclass
class GateResult:
    name: str
    status: str
    required: bool
    command: list[str]
    returncode: int | None
    duration_seconds: float
    output: str
    reason: str = ""


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run bounded Python quality gates without invoking a shell."
    )
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Collect coverage, honoring project configuration when no target is supplied.",
    )
    parser.add_argument("--coverage-target", action="append", default=[])
    parser.add_argument("--coverage-fail-under", type=float)
    parser.add_argument(
        "--test-runner",
        choices=("auto", "unittest", "pytest"),
        default="auto",
        help="Test framework; auto selects pytest only when project configuration declares it.",
    )
    parser.add_argument(
        "--test-arg",
        action="append",
        default=[],
        help="Additional test-runner argument; repeat and use --test-arg=-x for flags.",
    )
    parser.add_argument("--skip-git-diff-check", action="store_true")
    parser.add_argument("--skip-compile", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-dependency-check", action="store_true")
    parser.add_argument(
        "--extra-gate",
        action="append",
        default=[],
        metavar="NAME=COMMAND",
        help="Add a required shell-free gate parsed with shlex; shell operators are rejected.",
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--max-output-chars",
        type=int,
        default=MAX_CAPTURE_CHARS,
        help="Maximum captured output per gate; use 0 to omit command output.",
    )
    args = parser.parse_args(argv)

    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.max_output_chars < 0:
        parser.error("--max-output-chars cannot be negative")
    if args.coverage_fail_under is not None:
        if not 0 <= args.coverage_fail_under <= 100:
            parser.error("--coverage-fail-under must be between 0 and 100")
    return args


def is_git_repository(project: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "--is-inside-work-tree"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=10,
    )
    return result.returncode == 0


def has_python(project: Path) -> bool:
    markers = ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")
    if any((project / marker).exists() for marker in markers):
        return True
    return any(path.is_file() for path in project.glob("*.py"))


def has_tests(project: Path) -> bool:
    if (project / "tests").is_dir():
        return True
    return any(project.glob("test_*.py")) or any(project.glob("*_test.py"))


def detect_test_runner(project: Path) -> str:
    configuration_files = (
        "pyproject.toml",
        "pytest.ini",
        "setup.cfg",
        "tox.ini",
        "requirements.txt",
        "requirements-dev.txt",
    )
    for filename in configuration_files:
        path = project / filename
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            continue
        if "pytest" in content:
            return "pytest"
    return "unittest"


def parse_extra_gate(value: str) -> Gate:
    name, separator, raw_command = value.partition("=")
    if not separator or not name.strip() or not raw_command.strip():
        raise ValueError("extra gate must use NAME=COMMAND")
    command = tuple(shlex.split(raw_command))
    if not command:
        raise ValueError(f"extra gate {name!r} has an empty command")
    forbidden = {"|", "||", "&&", ";", ">", ">>", "<", "<<", "&"}
    if any(part in forbidden for part in command):
        raise ValueError(
            f"extra gate {name!r} contains a shell operator; invoke one executable directly"
        )
    return Gate(name=name.strip(), command=command)


def build_gates(args: argparse.Namespace, project: Path) -> tuple[list[Gate], list[GateResult]]:
    gates: list[Gate] = []
    skipped: list[GateResult] = []

    if args.skip_git_diff_check:
        skipped.append(skipped_result("git-diff-check", "disabled by option"))
    elif is_git_repository(project):
        gates.append(Gate("git-diff-check", ("git", "-C", str(project), "diff", "--check")))
    else:
        skipped.append(skipped_result("git-diff-check", "project is not a Git work tree"))

    python_project = has_python(project)
    if args.skip_compile:
        skipped.append(skipped_result("python-compile", "disabled by option"))
    elif python_project:
        gates.append(
            Gate(
                "python-compile",
                (
                    args.python,
                    "-m",
                    "compileall",
                    "-q",
                    "-x",
                    COMPILE_EXCLUDE,
                    str(project),
                ),
            )
        )
    else:
        skipped.append(skipped_result("python-compile", "no Python project marker found"))

    if args.skip_tests:
        skipped.append(skipped_result("python-tests", "disabled by option"))
    elif python_project and has_tests(project):
        coverage_enabled = bool(
            args.coverage
            or args.coverage_target
            or args.coverage_fail_under is not None
        )
        runner = (
            detect_test_runner(project)
            if args.test_runner == "auto"
            else args.test_runner
        )
        if runner == "pytest":
            test_command = ["pytest", "-q", *args.test_arg]
        else:
            test_command = [
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test*.py",
                *args.test_arg,
            ]
        if coverage_enabled:
            command = [
                args.python,
                "-m",
                "coverage",
                "run",
            ]
            if args.coverage_target:
                command.append(f"--source={','.join(args.coverage_target)}")
            command.extend(("-m", *test_command))
        else:
            command = [args.python, "-m", *test_command]
        gates.append(Gate("python-tests", tuple(command)))
        if coverage_enabled:
            coverage_command = [
                args.python,
                "-m",
                "coverage",
                "report",
                "--show-missing",
            ]
            if args.coverage_fail_under is not None:
                coverage_command.append(
                    f"--fail-under={args.coverage_fail_under:g}"
                )
            gates.append(Gate("python-coverage", tuple(coverage_command)))
    elif python_project:
        skipped.append(skipped_result("python-tests", "no tests directory or test modules found"))
    else:
        skipped.append(skipped_result("python-tests", "not a detected Python project"))

    if args.skip_dependency_check:
        skipped.append(skipped_result("python-dependencies", "disabled by option"))
    elif python_project:
        gates.append(Gate("python-dependencies", (args.python, "-m", "pip", "check")))
    else:
        skipped.append(skipped_result("python-dependencies", "not a detected Python project"))

    for raw_gate in args.extra_gate:
        gates.append(parse_extra_gate(raw_gate))
    return gates, skipped


def skipped_result(name: str, reason: str) -> GateResult:
    return GateResult(
        name=name,
        status="skipped",
        required=False,
        command=[],
        returncode=None,
        duration_seconds=0.0,
        output="",
        reason=reason,
    )


def truncate_output(output: str, limit: int) -> str:
    if limit == 0:
        return ""
    if len(output) <= limit:
        return output
    omitted = len(output) - limit
    return f"{output[:limit]}\n...[truncated {omitted} characters]"


def run_gate(
    gate: Gate,
    project: Path,
    timeout: float,
    output_limit: int,
    environment_overrides: dict[str, str],
) -> GateResult:
    started = time.monotonic()
    environment = os.environ.copy()
    environment.update(environment_overrides)
    environment.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    try:
        completed = subprocess.run(
            list(gate.command),
            cwd=project,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            timeout=timeout,
            env=environment,
        )
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        return GateResult(
            name=gate.name,
            status="passed" if completed.returncode == 0 else "failed",
            required=gate.required,
            command=list(gate.command),
            returncode=completed.returncode,
            duration_seconds=round(time.monotonic() - started, 3),
            output=truncate_output(output.rstrip(), output_limit),
        )
    except subprocess.TimeoutExpired as exc:
        captured = "\n".join(
            part.decode(errors="replace") if isinstance(part, bytes) else (part or "")
            for part in (exc.stdout, exc.stderr)
            if part
        )
        return GateResult(
            name=gate.name,
            status="timed_out",
            required=gate.required,
            command=list(gate.command),
            returncode=None,
            duration_seconds=round(time.monotonic() - started, 3),
            output=truncate_output(captured.rstrip(), output_limit),
            reason=f"exceeded {timeout:g} seconds",
        )
    except OSError as exc:
        return GateResult(
            name=gate.name,
            status="error",
            required=gate.required,
            command=list(gate.command),
            returncode=None,
            duration_seconds=round(time.monotonic() - started, 3),
            output="",
            reason=str(exc),
        )


def serialize_report(project: Path, results: list[GateResult]) -> dict[str, object]:
    required_failures = [
        result.name
        for result in results
        if result.required and result.status not in {"passed", "skipped"}
    ]
    return {
        "schema_version": 1,
        "project": str(project),
        "generated_at_epoch": int(time.time()),
        "passed": not required_failures,
        "required_failures": required_failures,
        "summary": {
            status: sum(result.status == status for result in results)
            for status in ("passed", "failed", "timed_out", "error", "skipped")
        },
        "gates": [asdict(result) for result in results],
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    project = args.project.expanduser().resolve()
    if not project.is_dir():
        print(f"error: project directory does not exist: {project}", file=sys.stderr)
        return 2

    try:
        gates, skipped = build_gates(args, project)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="production-code-hardening-") as work_dir:
        environment_overrides = {
            "COVERAGE_FILE": str(Path(work_dir) / ".coverage"),
            "PYTHONPYCACHEPREFIX": str(Path(work_dir) / "pycache"),
        }
        results = [
            run_gate(
                gate,
                project,
                args.timeout,
                args.max_output_chars,
                environment_overrides,
            )
            for gate in gates
        ]
    results.extend(skipped)
    report = serialize_report(project, results)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)

    if args.report:
        report_path = args.report.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(rendered + "\n", encoding="utf-8")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
