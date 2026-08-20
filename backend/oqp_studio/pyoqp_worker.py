"""Worker process: run one OpenQP job directory through the pyoqp API.

Usage: python -m oqp_studio.pyoqp_worker <job_dir>

Reads <job_dir>/input.inp, runs it with oqp.pyoqp.Runner (log appended by the
parent to job.log via stdout), and writes a JSON summary of runner.results()
to <job_dir>/results.json. Exit code 0 only if the calculation completed and
the summary was written.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _jsonable(value):
    """Best-effort conversion of numpy arrays and other objects to JSON."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return tolist()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def main() -> int:
    job_dir = Path(sys.argv[1]).resolve()
    input_file = next(
        (f for name in ("input.oqp", "input.inp") if (f := job_dir / name).exists()),
        job_dir / "input.oqp",
    )

    from oqp.pyoqp import Runner  # deferred: only the worker needs OpenQP

    runner = Runner(
        project=job_dir.name,
        input_file=str(input_file),
        log=str(job_dir / "oqp.log"),
    )
    runner.run()

    summary = _jsonable(runner.results())
    (job_dir / "results.json").write_text(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
