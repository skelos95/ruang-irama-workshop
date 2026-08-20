#!/usr/bin/env python3
from pathlib import Path

impl = Path(__file__).with_name("five_effects_impl.py")
code = impl.read_text(encoding="utf-8")
exec(compile(code, str(impl), "exec"), {"__file__": str(impl), "__name__": "__main__"})
if impl.exists():
    impl.unlink()
