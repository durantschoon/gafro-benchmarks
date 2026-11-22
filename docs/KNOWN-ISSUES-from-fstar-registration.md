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
3. **The sibling gafro-cpp build tree pins a compiler that is gone**:
   gafro-cpp's own `build/CMakeCache.txt` pins
   `/opt/homebrew/opt/gcc/bin/g++-15`, which Homebrew has since replaced
   with `…-16`, so that sibling's own build no longer configures as-is.
   This no longer affects the harness: the C++ member compiles its
   adapter in a fresh temporary tree with its own compiler
   (`/usr/bin/clang++` on Darwin) and reads only the generated
   `src/gafro/gafro_package_config.hpp` from that build directory; a
   2026-11-22 smoke run built and validated the C++ member against it
   unchanged. Fix (in gafro-cpp): regenerate its build dir.
4. **`benchmark_harness/core.py:15` hard-codes
   `IMPLEMENTATIONS = ("cpp","idris2","rust","julia")`** and rejects
   `"fstar"`; the one-token addition is proposed in the fstar
   registration commit message and `fstar/README.md`, measured as the
   only remaining gap to full `validate_complete_run` acceptance.
