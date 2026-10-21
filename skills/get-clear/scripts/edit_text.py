#!/usr/bin/env python3
"""Apply one literal text replacement without changing unrelated file bytes."""
from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode(data: bytes) -> tuple[bytes, str, str]:
    if data.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        raise ValueError("UTF-32 is not supported; use a format-aware editor")
    for marker, encoding in ((codecs.BOM_UTF8, "utf-8"),
                             (codecs.BOM_UTF16_LE, "utf-16-le"),
                             (codecs.BOM_UTF16_BE, "utf-16-be")):
        if data.startswith(marker):
            return marker, encoding, data[len(marker):].decode(encoding, errors="strict")
    text = data.decode("utf-8", errors="strict")
    if "\x00" in text:
        raise ValueError("NUL bytes without an encoding marker; inspect the file encoding")
    return b"", "utf-8", text


def replace_file(path: Path, spec: dict) -> dict:
    allowed = {"old", "new", "expected_matches", "expected_sha256"}
    if not isinstance(spec, dict) or set(spec) - allowed:
        raise ValueError("Use only old, new, expected_matches and optional expected_sha256")
    old, new, count = spec.get("old"), spec.get("new"), spec.get("expected_matches")
    if not isinstance(old, str) or not old or not isinstance(new, str):
        raise ValueError("old must be nonempty text and new must be text")
    if type(count) is not int or count < 1:
        raise ValueError("expected_matches must be a positive integer")
    if path.is_symlink() or not path.is_file():
        raise ValueError("Target must be an existing regular file, not a symbolic link")
    before = path.read_bytes()
    before_hash = digest(before)
    expected_hash = spec.get("expected_sha256")
    if expected_hash is not None and expected_hash != before_hash:
        raise ValueError("Target differs from expected_sha256; reread before editing")
    marker, encoding, content = decode(before)
    matches = content.count(old)
    if matches != count:
        raise ValueError(f"Expected {count} matches, found {matches}; target unchanged")
    after = marker + content.replace(old, new).encode(encoding, errors="strict")
    report = {"applied": False, "matches": matches, "encoding": encoding,
              "before_sha256": before_hash, "after_sha256": digest(after)}
    if after == before:
        return report
    mode = stat.S_IMODE(path.stat().st_mode)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".get-clear-", delete=False) as out:
            temporary = Path(out.name)
            out.write(after)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temporary, mode)
        if path.read_bytes() != before:
            raise ValueError("Target changed while preparing the edit; target left untouched")
        os.replace(temporary, path)
        temporary = None
        if path.read_bytes() != after:
            raise OSError("Readback differs from the intended result; inspect before proceeding")
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    report["applied"] = True
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--spec", type=Path, required=True,
                        help="UTF-8 JSON with old, new, expected_matches")
    args = parser.parse_args()
    try:
        if args.target.resolve() == args.spec.resolve():
            raise ValueError("The target and replacement spec must be different files")
        spec = json.loads(args.spec.read_text(encoding="utf-8-sig"))
        result = replace_file(args.target, spec)
    except (OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
