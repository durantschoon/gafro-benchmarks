#!/usr/bin/env python3
# SPDX-FileCopyrightText: Durant Schoon <durant.schoon@gmail.com>
#
# SPDX-License-Identifier: MPL-2.0

"""The gafro-fstar member of the shootout.

gafro-fstar is the F*/Low* member: its kernels are verified in F*,
extracted to C by KaRaMeL, and committed.  Unlike every other member,
it does NOT build on the runner host.  Its toolchain is a lock
(channels.scm + manifest.scm + opam/pins.env) that is only ever
instantiated inside an OrbStack machine running Guix, and its own
Makefile refuses to assume a compiler on the Mac.  So this wrapper does
not compile anything: it asks that repository for `make bench', which
builds and runs the benchmark inside the machine and writes a
`gafro-benchmark-bundle/v1' document to stdout.

THREE OUTCOMES, AND ONLY ONE OF THEM IS A NUMBER.

  available    the checkout is there, orbctl is there, the machine is
               running, `make bench' succeeded -> its rows, verbatim.
  unavailable  a host prerequisite is missing (no checkout, no orbctl,
               machine not running).  Every contract id is emitted as
               `unavailable' with the reason.  A member that cannot run
               here says so; it does not fail the shootout.
  failed       the prerequisites were all present and `make bench'
               still failed -- a real defect, reported as `failed' with
               the captured stderr.  This is NOT downgraded to
               `unavailable': hiding a broken member behind a missing
               toolchain is the one thing this wrapper must not do.

WHERE THE NUMBERS COME FROM.  Inside the machine.  Every other member
of this shootout is built and timed natively on the host.  A ratio
between an fstar row and a native row therefore crosses a
virtualisation boundary -- and on an Apple Silicon host it crosses an
ARCHITECTURE boundary as well, because the guest reports aarch64 while
the host's Rosetta toolchains report x86_64.  That is not left to a
footnote: the rows gafro-fstar emits carry the guest's own uname, and
benchmark_harness/core.py's `_compatible_environments' refuses to
ratio two rows whose declared host keys disagree.  Telling the truth in
the row is what makes the tool decline the comparison.

  usage: fstar/run_fstar.py [--fstar-path PATH] [--profile smoke|full]

  GAFRO_FSTAR_PATH   overrides the checkout search, same role as
                     benchmark_harness.cli's --cpp-path / --rust-path.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CONTRACT = ROOT_DIR / "contracts" / "workloads-v1.json"

# The file that marks a gafro-fstar checkout able to bench: not the
# Makefile (every repository has one) but the harness itself.
MARKER = Path("bench") / "bench_cga.c"

FAMILY = "fstar"
BUNDLE_VERSION = "gafro-benchmark-bundle/v1"
RESULT_VERSION = "gafro-benchmark-result/v1"

# Used only for the placeholder rows, where no build ever happened and
# so no compiler, revision or flag list can honestly be reported.
PLACEHOLDER_IDENTITY = {
    "family": FAMILY,
    "name": "gafro-fstar",
    "repository_revision": "unknown: nothing was built",
    "dirty": False,
    "compiler": "none: no build was attempted on this host",
    "backend": "lowstar-karamel-c",
    "flags": [],
}


def workload_ids() -> list[str]:
    manifest = json.loads(CONTRACT.read_text())
    return [item["id"] for item in manifest["workloads"]]


def placeholder_rows(status: str, reason: str, identity: dict | None = None) -> list[dict]:
    """One row per contract id, so a gap is visible instead of absent."""
    return [
        {
            "schema_version": RESULT_VERSION,
            "implementation": dict(identity or PLACEHOLDER_IDENTITY),
            "host": {},
            "workload_id": workload_id,
            "status": status,
            "reason": reason,
        }
        for workload_id in workload_ids()
    ]


def discover(override: str | None) -> dict[str, str]:
    """Locate a gafro-fstar checkout, mirroring benchmark_harness.cli.discover."""
    override = override or os.environ.get("GAFRO_FSTAR_PATH")
    if override:
        candidates = [Path(override).expanduser()]
    else:
        candidates = []
        for parent in (ROOT_DIR.parent, ROOT_DIR.parent.parent):
            checkout = parent / f"gafro-{FAMILY}"
            candidates.extend((checkout, checkout / f"gafro-{FAMILY}"))
    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / MARKER).is_file():
            return {"status": "available", "path": str(resolved)}
    shown = str(candidates[0].resolve())
    return {
        "status": "unavailable",
        "path": shown,
        "reason": f"no gafro-fstar checkout with {MARKER} at {shown} "
                  f"(set GAFRO_FSTAR_PATH or pass --fstar-path)",
    }


def machine_ready(checkout: Path) -> tuple[bool, str]:
    """Is the OrbStack machine this member needs actually up?

    Deliberately does not try to start it.  Provisioning is
    `make provision' in gafro-fstar and is that repository's business;
    a benchmark runner that silently rebuilt a VM would be doing
    something nobody asked it to do.
    """
    orbctl = shutil.which("orbctl") or "/usr/local/bin/orbctl"
    if not Path(orbctl).is_file():
        return False, ("gafro-fstar runs only inside an OrbStack machine (its toolchain is a "
                       "guix lock, never installed on the host) and orbctl is not on this host")
    name = os.environ.get("GAFRO_VM", "guix")
    try:
        listing = subprocess.run([orbctl, "list"], check=True, text=True,
                                 capture_output=True, timeout=30).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        return False, f"orbctl list failed on this host ({exc})"
    for line in listing.splitlines():
        fields = line.split()
        if fields and fields[0] == name:
            if len(fields) > 1 and fields[1] == "running":
                return True, ""
            state = fields[1] if len(fields) > 1 else "unknown"
            return False, (f"the OrbStack machine {name!r} gafro-fstar needs is {state}, not "
                           f"running; start it, or run `make provision' in {checkout}")
    return False, (f"no OrbStack machine named {name!r} on this host; gafro-fstar's toolchain "
                   f"lives only there (run `make provision' in {checkout})")


def run(checkout: Path, profile: str) -> tuple[int, str, str]:
    command = ["make", "bench"]
    if profile == "smoke":
        command.append("BENCH_ARGS=--profile smoke")
    completed = subprocess.run(command, cwd=str(checkout), text=True, capture_output=True)
    return completed.returncode, completed.stdout, completed.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description="run the gafro-fstar benchmark member")
    parser.add_argument("--fstar-path", default=None)
    parser.add_argument("--profile", default="full", choices=("smoke", "full"))
    args = parser.parse_args()

    found = discover(args.fstar_path)
    if found["status"] != "available":
        rows = placeholder_rows("unavailable", found["reason"])
        print(json.dumps({"schema_version": BUNDLE_VERSION, "results": rows}, indent=2, sort_keys=True))
        print(f"[fstar] unavailable: {found['reason']}", file=sys.stderr)
        return 0

    checkout = Path(found["path"])
    ready, why = machine_ready(checkout)
    if not ready:
        rows = placeholder_rows("unavailable", why)
        print(json.dumps({"schema_version": BUNDLE_VERSION, "results": rows}, indent=2, sort_keys=True))
        print(f"[fstar] unavailable: {why}", file=sys.stderr)
        return 0

    print(f"[fstar] make bench in {checkout} (inside the OrbStack machine)", file=sys.stderr)
    code, stdout, stderr = run(checkout, args.profile)
    if code != 0 or not stdout.strip():
        tail = " | ".join(line for line in stderr.strip().splitlines()[-6:])
        reason = (f"`make bench' in {checkout} exited {code}. This is a real failure of the "
                  f"member, not a missing host prerequisite, and is reported as such: {tail}")
        rows = placeholder_rows("failed", reason)
        print(json.dumps({"schema_version": BUNDLE_VERSION, "results": rows}, indent=2, sort_keys=True))
        print(stderr, file=sys.stderr)
        return 0

    try:
        bundle = json.loads(stdout)
    except json.JSONDecodeError as exc:
        reason = f"`make bench' produced output that is not JSON: {exc.msg}"
        rows = placeholder_rows("failed", reason)
        print(json.dumps({"schema_version": BUNDLE_VERSION, "results": rows}, indent=2, sort_keys=True))
        print(stderr, file=sys.stderr)
        return 0

    print(json.dumps(bundle, indent=2, sort_keys=True))
    print(stderr, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
