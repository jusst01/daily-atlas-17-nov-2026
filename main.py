#!/usr/bin/env python3
"""make.fun entry point for the news-image-20261117 entry.

Deploys the bundled, pre-rendered front page (entry.png, sitting next to this
file) into $MAKEFUN_OUTPUT_DIR (default: /output).

Standard library only. The source image is resolved relative to this file, so
the process working directory is irrelevant, and the output is staged through
a temporary file next to the destination and moved into place with an atomic
rename -- a runner that interrupts us never leaves a half-written PNG behind.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

IMAGE_NAME = "entry.png"
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, IMAGE_NAME)
DEFAULT_OUTPUT_DIR = "/output"


def fail(message: str):
    print(f"main.py: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def output_dir() -> str:
    raw = os.environ.get("MAKEFUN_OUTPUT_DIR")
    target = raw if raw else DEFAULT_OUTPUT_DIR
    try:
        os.makedirs(target, exist_ok=True)
    except OSError as exc:
        fail(f"cannot create output directory {target!r}: {exc}")
    return target


def deploy(source: str, dest: str) -> None:
    """Copy `source` to `dest` via a temp file in the same directory, then rename."""
    expected = os.path.getsize(source)
    dest_dir = os.path.dirname(dest) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".entry-", suffix=".png.tmp", dir=dest_dir)
    os.close(fd)
    try:
        shutil.copyfile(source, tmp_path)
        staged = os.path.getsize(tmp_path)
        if staged != expected:
            fail(
                f"copy was truncated: wrote {staged} bytes of {expected} "
                f"from {source!r}"
            )
        os.replace(tmp_path, dest)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    written = os.path.getsize(dest)
    if written != expected:
        fail(
            f"deployed copy is {written} bytes but source is {expected} bytes "
            f"({dest!r})"
        )


def main() -> int:
    if not os.path.isfile(SOURCE):
        fail(f"bundled image not found at {SOURCE}")
    dest = os.path.join(output_dir(), IMAGE_NAME)
    try:
        deploy(SOURCE, dest)
    except OSError as exc:
        fail(f"could not write {dest!r}: {exc}")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
