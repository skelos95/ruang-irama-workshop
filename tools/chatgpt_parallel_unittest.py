from __future__ import annotations

import concurrent.futures
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item.id()


sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))
loader = unittest.TestLoader()
suite = loader.discover(str(TESTS), pattern="test_*.py")
ids = list(flatten(suite))
if not ids:
    raise SystemExit("No tests discovered")
workers = min(4, len(ids))
chunks = [ids[i::workers] for i in range(workers)]

env = os.environ.copy()
existing = env.get("PYTHONPATH", "")
env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(TESTS), existing]) if existing else os.pathsep.join([str(ROOT), str(TESTS)])


def run_chunk(chunk):
    cmd = [sys.executable, "-m", "unittest", *chunk]
    result = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
    return result.returncode, result.stdout, result.stderr, len(chunk)

failed = False
with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
    futures = [pool.submit(run_chunk, chunk) for chunk in chunks if chunk]
    for future in concurrent.futures.as_completed(futures):
        code, out, err, count = future.result()
        print(f"--- chunk {count} tests: {'OK' if code == 0 else 'FAILED'} ---")
        if out:
            print(out)
        if err:
            print(err, file=sys.stderr)
        failed |= code != 0

print(f"Parallel suite executed {len(ids)} tests across {workers} workers")
raise SystemExit(1 if failed else 0)
