#!/usr/bin/env python3
"""Read-only dependency discovery, pinned download for review, and no-overwrite install.

Python 3.10+, standard library only. No shell execution or credential access.
Discovery says files are readable, never that a host has loaded a Skill.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import urllib.request
import zipfile

PACKAGE = Path(__file__).resolve().parents[1]
MAX_BYTES = 32 * 1024 * 1024
MAX_FILES = 500


def locked():
    return json.loads((PACKAGE / "dependencies.lock.json").read_text(encoding="utf-8"))["dependencies"]


def safe_name(value):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        raise ValueError("Invalid dependency name")
    return value


def safe_relative(value):
    p = PurePosixPath(value)
    if (not value or p.is_absolute() or "\\" in value or ":" in value
            or any(x in (".", "..", "") for x in value.split("/"))):
        raise ValueError(f"Unsafe archive path: {value}")
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{x}{i}" for x in ("COM", "LPT") for i in range(1, 10)}
    if any(x.endswith((".", " ")) or x.split(".")[0].upper() in reserved for x in p.parts):
        raise ValueError(f"Nonportable archive path: {value}")
    return p


def selected_files(data, spec):
    """Verify pinned bytes then return exactly one skill plus its repository license."""
    if len(data) > MAX_BYTES or hashlib.sha256(data).hexdigest() != spec["archive_sha256"]:
        raise ValueError("Archive digest mismatch or size limit exceeded; do not install")
    root = spec["archive_root"] + "/"
    subtree = root + (spec["skill_path"].strip("/") + "/" if spec["skill_path"] else "")
    license_source = root + spec["license_path"]
    result, seen, total = {}, set(), 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            if entry.filename == license_source:
                relative = "LICENSE"
            elif entry.filename.startswith(subtree):
                relative = entry.filename[len(subtree):]
            else:
                continue
            safe_relative(relative)
            mode = entry.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if kind not in (0, stat.S_IFREG):
                raise ValueError("Archive contains a link or non-regular file")
            key = relative.casefold()
            if key in seen:
                raise ValueError("Duplicate or case-colliding archive file")
            seen.add(key)
            total += entry.file_size
            if total > MAX_BYTES or len(seen) > MAX_FILES:
                raise ValueError("Expanded dependency exceeds limits")
            result[relative] = archive.read(entry)
    for required in [*spec["required_files"], "LICENSE"]:
        if required not in result:
            raise ValueError(f"Missing required upstream file: {required}")
    return result


def write_new_directory(destination, files):
    """Reserve the destination without overwrite; leave evidence if a write fails."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(exist_ok=False)
    try:
        # Write the entrypoint last: a partial copy is less likely to be discovered.
        for name in sorted(files, key=lambda x: (x == "SKILL.md", x)):
            relative = safe_relative(name)
            output = destination.joinpath(*relative.parts)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                stream.write(files[name])
    except Exception:
        # Do not remove user-accessible evidence or silently retry over this folder.
        raise RuntimeError(f"Incomplete copy preserved at {destination}; inspect before repair") from None


def check(roots, specs):
    results = []
    for name, spec in specs.items():
        matches = []
        for root in roots:
            candidate = root / name
            if not candidate.exists() and not candidate.is_symlink():
                continue
            missing = []
            for file in spec["required_files"]:
                try:
                    (candidate / file).read_text(encoding="utf-8-sig")
                except (OSError, UnicodeError):
                    missing.append(file)
            matches.append({"path": str(candidate), "files_readable": not missing, "missing_or_unreadable": missing})
        results.append({"name": name, "state": "present" if any(m["files_readable"] for m in matches)
                        else "incomplete" if matches else "missing", "matches": matches,
                        "host_loaded": "not_checked", "version": "not_inferred"})
    return results


def fetch(name, spec, directory):
    url = f"https://codeload.github.com/{spec['repository']}/zip/{spec['commit']}"
    request = urllib.request.Request(url, headers={"User-Agent": "prompt-ready/0.1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(MAX_BYTES + 1)
    files = selected_files(data, spec)
    directory = Path(directory).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    archive_path = directory / f"{name}-{spec['commit']}.zip"
    review = directory / f"{name}-review"
    if archive_path.exists() or review.exists() or review.is_symlink():
        raise FileExistsError("Download/review output exists; choose another directory or inspect existing output")
    with archive_path.open("xb") as stream:
        stream.write(data)
    write_new_directory(review, files)
    return {"state": "downloaded_for_review", "archive": str(archive_path), "review_directory": str(review),
            "files": sorted(files), "source": url, "installed": False}


def install(name, spec, archive, root):
    root = Path(root).expanduser().resolve()
    destination = root / safe_name(name)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Existing installation preserved: {destination}")
    with Path(archive).open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    files = selected_files(data, spec)
    write_new_directory(destination, files)
    return {"state": "installed_files", "path": str(destination), "host_loaded": "not_checked", "files": len(files)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect_parser = sub.add_parser("check", help="Read only. Pass host-visible roots, not credential/config folders.")
    inspect_parser.add_argument("--search-root", action="append", required=True)
    fetch_parser = sub.add_parser("fetch", help="Fetch pinned bytes and extract a review copy, not an installation.")
    fetch_parser.add_argument("--dependency", choices=list(locked()), required=True)
    fetch_parser.add_argument("--directory", required=True)
    install_parser = sub.add_parser("install", help="Install audited pinned bytes into an explicitly selected skill root.")
    install_parser.add_argument("--dependency", choices=list(locked()), required=True)
    install_parser.add_argument("--archive", required=True)
    install_parser.add_argument("--skill-root", required=True)
    install_parser.add_argument("--reviewed", action="store_true", required=True,
                                help="Agent attests it reviewed the fetched package; not a user-permission bypass.")
    args = parser.parse_args()
    specs = locked()
    if args.command == "check":
        roots = list(dict.fromkeys(Path(r).expanduser().resolve() for r in args.search_root))
        result = {"dependencies": check(roots, specs)}
    elif args.command == "fetch":
        result = fetch(args.dependency, specs[args.dependency], args.directory)
    else:
        result = install(args.dependency, specs[args.dependency], args.archive, args.skill_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
        print(json.dumps({"state": "error", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
