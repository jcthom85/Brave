"""Run Brave's fast non-Django validation lane."""

from __future__ import annotations

import compileall
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
COMPILE_TARGETS = ("world", "commands", "typeclasses", "web")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _run_compileall():
    ok = True
    for target in COMPILE_TARGETS:
        ok = compileall.compile_dir(
            str(ROOT / target),
            quiet=1,
            force=False,
        ) and ok
    return 0 if ok else 1


def _run_content_build():
    from world.content.build import main

    return int(main() or 0)


def _run_fast_tests():
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "regression_tests/fast"),
        ],
        cwd=str(ROOT),
    )


def main():
    checks = (
        ("compileall", _run_compileall),
        ("content build", _run_content_build),
        ("fast tests", _run_fast_tests),
    )
    for label, check in checks:
        print(f"\n== {label} ==", flush=True)
        result = check()
        if result:
            return result
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
