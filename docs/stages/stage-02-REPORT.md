# Stage 02 report: C++ reference adapter

## Outcome

The C++ adapter now implements every Stage 01 workload with binary64 inputs,
analytically derived reference outputs, untimed oracle checks, varied inputs,
an assembly memory-clobber optimization boundary, warm-up, and multiple raw
samples. The CLI performs an isolated release build from explicit source and
generated-header paths and writes raw evidence only after pure validation.

## Provenance and build

The successful clean build used `/usr/bin/clang++`, AppleClang
21.0.0.21000101, `-std=c++2c -O3 -march=native -DNDEBUG`, and GAFro revision
`37093d992b98a272e5a1fa264a68bef964a65eb2`. CMake validates both
`GAFRO_CPP_DIR/src/gafro/gafro.hpp` and the generated package-config header in
`GAFRO_CPP_BUILD_DIR`; it never falls back to an installed package.

The host-default Homebrew `g++-15` compiled and linked but its chrono readings
were zero on this macOS host, so those observations were rejected rather than
published. The Darwin default is consequently the system Clang compiler; an
explicit `CPP_COMPILER` override remains available and is recorded.

## Gates and sanity checks

The following passed on 2026-08-26:

```text
make check
make test
make benchmark-smoke
make benchmark IMPLEMENTATIONS=cpp
```

The full profile emitted 15 positive finite samples for each of the three
workloads at 100,000 operations per sample. Tests cover incorrect oracle values,
missing benchmark IDs, non-finite samples, and inconsistent operation counts.
Neither run modified the committed summary files.

## Deviations and open questions

- Current GAFro headers use C++26 pack indexing, so the adapter records C++26
  rather than the Stage 01-era C++20 assumption.
- Later stages should replace the `latest` evidence filename with immutable run
  IDs when reproducible aggregation is introduced.
