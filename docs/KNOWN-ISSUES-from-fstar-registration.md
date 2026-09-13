# Known issues surfaced by the gafro-fstar registration (2026-09-13)

Recorded here per family practice (findings documented in the repo they
belong to); sources: gafro-fstar stage-04 REPORT §deviations/OQ.

1. **`PORTING_AND_STANDARDS.md` §2's row sample is dead.** It shows
   `benchmark`/`time_per_op_ns`/`ops_per_sec`; no emitter in any
   committed run produces those keys. The truth is the committed runs'
   shape (`schema_version/implementation/host/workload_id/status/…`,
   validated by `contracts/result-v1.schema.json`). A new member
   author following the doc emits rejected rows. Fix: update the doc
   sample from a committed run.
2. **`cli.smoke` writes `oracle: {"scalar": 1.0}` but the validator
   reads `oracle.value`** (`core.validate_complete_run`) — a template
   trap for anyone copying the smoke row.
3. **The C++ member no longer builds on this host**:
   `cpp/build/CMakeCache.txt` pins `/opt/homebrew/opt/gcc/bin/g++-15`,
   which Homebrew has since replaced with `…-16`. Pre-existing host
   rot, reproduced with the exact cmake invocation during the fstar
   registration; `build_cpp` itself is unchanged. Fix: regenerate the
   build dir (it arguably should not be committed at all).
4. **`benchmark_harness/core.py:15` hard-codes
   `IMPLEMENTATIONS = ("cpp","idris2","rust","julia")`** and rejects
   `"fstar"`; the one-token addition is proposed in the fstar
   registration commit message and `fstar/README.md`, measured as the
   only remaining gap to full `validate_complete_run` acceptance.
