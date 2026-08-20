#!/usr/bin/env python3
from pathlib import Path

impl = Path(__file__).with_name("five_effects_impl.py")
code = impl.read_text(encoding="utf-8")
needle = '    source = source.replace("HasilNasibTerkunci", "TickBurnNasib")\n'
if code.count(needle) != 1:
    raise RuntimeError("migration anchor HasilNasibTerkunci non trovato")
code = code.replace(needle, needle + '    validator = validator.replace("HasilNasibTerkunci", "TickBurnNasib")\n', 1)
exec(compile(code, str(impl), "exec"), {"__file__": str(impl), "__name__": "__main__"})
if impl.exists():
    impl.unlink()
