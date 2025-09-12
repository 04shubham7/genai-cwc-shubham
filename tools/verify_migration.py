from __future__ import annotations

import argparse
import hashlib
import os
from dataclasses import dataclass
from typing import Iterable, List, Tuple


IGNORE_DIRS = {
    ".git",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".vscode",
    ".idea",
    "node_modules",
    ".ipynb_checkpoints",
}


def file_iter(root: str) -> Iterable[str]:
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        # prune ignored dirs
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            if f == ".DS_Store":
                continue
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, root)
            yield rel


def sha256(path: str, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as rf:
        while True:
            b = rf.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


@dataclass
class Diff:
    missing_in_dest: List[str]
    extra_in_dest: List[str]
    size_mismatch: List[Tuple[str, int, int]]
    hash_mismatch: List[str]


def compare_dirs(src: str, dst: str, do_hash: bool = False) -> Diff:
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)

    src_files = sorted(file_iter(src))
    dst_files = sorted(file_iter(dst))
    src_set = set(src_files)
    dst_set = set(dst_files)

    missing = sorted(src_set - dst_set)
    extra = sorted(dst_set - src_set)

    size_mismatch: List[Tuple[str, int, int]] = []
    hash_mismatch: List[str] = []

    for rel in sorted(src_set & dst_set):
        s = os.path.join(src, rel)
        d = os.path.join(dst, rel)
        ss = os.path.getsize(s)
        ds = os.path.getsize(d)
        if ss != ds:
            size_mismatch.append((rel, ss, ds))
            continue
        if do_hash:
            if sha256(s) != sha256(d):
                hash_mismatch.append(rel)

    return Diff(missing, extra, size_mismatch, hash_mismatch)


def main() -> int:
    p = argparse.ArgumentParser(description="Verify project migration between folders")
    p.add_argument("--source", required=True, help="Source folder (old/current)")
    p.add_argument("--dest", required=True, help="Destination folder (new)")
    p.add_argument("--hash", action="store_true", help="Verify file contents with SHA256 (slower)")
    args = p.parse_args()

    if not os.path.isdir(args.source):
        print(f"ERROR: source not found: {args.source}")
        return 2
    if not os.path.isdir(args.dest):
        print(f"ERROR: dest not found: {args.dest}")
        return 3

    diff = compare_dirs(args.source, args.dest, do_hash=args.hash)

    print("Source:", os.path.abspath(args.source))
    print("Dest  :", os.path.abspath(args.dest))
    print()

    if diff.missing_in_dest:
        print(f"Missing in dest ({len(diff.missing_in_dest)}):")
        for rel in diff.missing_in_dest:
            print("  -", rel)
        print()
    if diff.extra_in_dest:
        print(f"Extra in dest ({len(diff.extra_in_dest)}):")
        for rel in diff.extra_in_dest:
            print("  +", rel)
        print()
    if diff.size_mismatch:
        print(f"Size mismatches ({len(diff.size_mismatch)}):")
        for rel, ss, ds in diff.size_mismatch:
            print(f"  * {rel} (src={ss}B, dest={ds}B)")
        print()
    if diff.hash_mismatch:
        print(f"Hash mismatches ({len(diff.hash_mismatch)}):")
        for rel in diff.hash_mismatch:
            print(f"  # {rel}")
        print()

    if not (diff.missing_in_dest or diff.size_mismatch or diff.hash_mismatch):
        print("OK: All source files found in destination with matching sizes" + (" and hashes" if args.hash else "") + ".")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
