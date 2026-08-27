# Stage 05 report: canonical robotics workloads

## Outcome

The benchmark contract now contains canonical two-joint forward-kinematics and
base-frame spatial geometric-Jacobian workloads. C++ supports both after full
coefficient-level oracle checks. Rust supports forward kinematics after the same
eight-coefficient motor oracle; its Jacobian is explicitly unsupported because
the selected API does not satisfy the shared fixed-frame convention. Idris 2
emits non-empty unsupported records for both workloads.

## Canonical chain and oracles

The chain has two revolute joints, ordered from base to tool. Both axes are
positive Z, both joint fixed frames are identity rotations translated by
`(0, 1, 0)`, and base and tool frames are identity. Each joint motor is
`fixed_frame * rotor_z(q)`, and the complete FK product is evaluated left to
right from base to tool. The input sequence alternates `[0, tau/4]` and
`[1/1024, tau/4 - 1/1024]`; chain construction and sequence creation occur
outside timing.

At the first vector, the motor coefficient order
`[scalar,e12,e13,e23,e1i,e2i,e3i,e123i]` has reference
`[sqrt(1/2),-sqrt(1/2),0,0,-sqrt(1/2),-sqrt(1/2),0,0]`. Positive Z rotation
therefore has a negative `e12` rotor coefficient. The reported sum is
`-sqrt(2)`.

The Jacobian is the base-frame spatial geometric Jacobian, stored as one twist
per column in coefficient order `[e12,e13,e23,e1i,e2i,e3i]`. Its 6x2 columns
are `[1,0,0,1,0,0]` and `[1,0,0,2,0,0]`; the reported column-major checksum is
`5`. C++ validates every motor and Jacobian coefficient before timing.

## Capability evidence

| Adapter | Forward kinematics | Geometric Jacobian |
| --- | --- | --- |
| C++ `cb9969a` (dirty checkout) | Supported | Supported |
| Rust `dfa8e66` (clean checkout) | Supported | Unsupported |
| Idris 2 `1bf4750` (clean checkout) | Unsupported | Unsupported |

Rust's `forward_kinematics` follows the canonical `origin_transform * rotor`
composition and passes the full motor oracle. Its `geometric_jacobian` places a
joint axis using only the prefix motor before that joint, omitting that joint's
own `origin_transform`; the canonical columns therefore cannot be reconciled.
No nearby Rust Jacobian is substituted. Idris 2 has no benchmark adapter proven
against this chain and oracle, and the stage constraint forbids adding a
benchmark-only robotics implementation.

The C++ checkout was already dirty with CUDA Stage 06 work. The benchmark only
read it and records `dirty: true`; none of those user changes were modified.
No allocation results are reported because the adapters do not share a reliable
documented allocation-measurement method.

## Gates and evidence

The following passed on 2026-08-26:

```text
make check
make test
make benchmark-smoke
make benchmark IMPLEMENTATIONS=cpp,idris2,rust
```

The full bundles contain 15 positive samples for every supported workload and
10,000 operations per robotics sample. On this Apple Silicon host, the raw
median robotics timings were 82.5 ns/operation for C++ FK, 134.1583
ns/operation for C++ Jacobian, and 38.5791 ns/operation for Rust FK. These local
measurements are evidence for the run, not a general language ranking.

## Deviations and open questions

- The prompt baseline described Idris 2 as having no robotics layer. The
  selected revision has evolving robotics code, but this stage does not yet have
  a validated canonical adapter, so unsupported remains the honest result.
- Rust Jacobian support can be enabled only after its origin-frame semantics are
  corrected or an existing API is demonstrated to produce the exact base-frame
  oracle.
- The older third-party and nominal 6-DOF benchmark sources remain untouched as
  a separate legacy suite.
