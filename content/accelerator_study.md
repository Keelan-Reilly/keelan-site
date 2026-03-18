---
title: "Measured Tradeoffs in FPGA MAC-Array Architectures"
date: 2026-03-17
summary: "A deterministic experimentation framework for bounded FPGA architecture studies over parameterised SystemVerilog MAC-array accelerators, with canonical run provenance, automated verification/synthesis/performance collection, and measured tradeoff analysis across baseline, shared, and replicated compute structures."
math: true
kpis:
  - label: "8×8 DSP reduction"
    value: "64 → 32 DSP"
    note: "shared vs baseline with +4 cycle latency"

  - label: "Replication limit"
    value: "8×8 fails implementation"
    note: "41892 LUT at synth, does not place on Artix-7"

  - label: "Bounded architecture study"
    value: "canonical 3×3 grid"
    note: "baseline / shared / replicated across 4×4, 8×4, 8×8"
---

This project is a deterministic control plane for bounded FPGA architecture studies over a parameterised SystemVerilog MAC-array accelerator.

The repository owns the full experimental workflow around the hardware implementation: candidate manifests, canonical run directories, fast verification, Vivado implementation, Verilator performance collection, SQLite-backed provenance, score computation, and result generation. The RTL implementation itself lives in an external accelerator repository; this project owns the measurement and evidence model around it.

The study focuses on a simple question:

- how baseline, shared, and replicated MAC-array structures trade off **latency, area, and timing**
- where sharing remains efficient
- where replication becomes physically too expensive on the target FPGA

## Project Overview

The active accelerator family is a bounded MAC-array / GEMM-style architecture with real synthesizable parameters for:

- architecture family
- array dimensions
- cluster size
- sharing factor
- arithmetic width
- accumulator width
- bounded pipeline depth
- memory sizing

Each candidate is evaluated through a fixed controller-owned flow:

**manifest registration → fast verification → Vivado implementation → Verilator performance collection → scoring/ranking**

Every controller run produces:

- a canonical `runs/<candidate_id>/attempt_<n>/` directory
- stable stage outputs
- tracked state transitions in SQLite
- explicit provenance about whether ranking uses full implementation data or provisional synth-only evidence

This keeps the study reproducible and prevents results from drifting across scratch directories, stale reports, or overwritten runs.

## System Structure

The repository is organised into three main layers.

### Controller layer

The Python controller handles:

- candidate registration
- stage execution
- state transitions
- artifact resolution
- scoring and ranking
- best-candidate tracking

The execution model is intentionally local and deterministic: stage order is fixed, every run receives a unique owned directory, and canonical artifacts are never overwritten in place.

### Wrapper layer

Stable wrapper scripts handle the real tool boundaries:

- fast verification / lint
- Vivado batch execution
- Verilator performance collection

Each wrapper emits machine-readable stage results and makes partial or failed outcomes explicit.

### Evidence layer

`runs/` is the primary evidence surface for measured results.

That evidence includes:

- canonical run directories
- stage result JSON files
- parsed Vivado and Verilator metrics
- ranking reports
- generated study summaries

## Candidate Model

Each candidate is represented by a manifest containing:

- candidate ID
- parameter choices
- rationale / hypothesis
- lightweight tags

The active bounded study covers three architecture families:

- **baseline**: direct compute structure
- **shared**: reduced DSP demand through phased sharing
- **replicated**: preserved shadow compute to expose the physical cost of replication

Canonical points were measured at:

- `4×4`
- `8×4`
- `8×8`

This produces a compact architecture lattice that is small enough to run carefully and large enough to expose real scaling behaviour.

## Verification and Toolflow

Every candidate passes through the same deterministic execution path.

### Fast verification

The controller checks that:

- the manifest matches the active schema
- every searched parameter exists in the real top-level RTL
- required toolflow entry points exist
- Verilator lint passes

This blocks invalid candidates before expensive implementation work begins.

### Vivado implementation

The controller forwards the real parameter values into the external Vivado batch flow and parses post-run implementation metrics such as:

- LUT
- FF
- DSP
- BRAM
- WNS
- estimated Fmax

### Verilator performance collection

For implementation-clean candidates, the controller also collects cycle-accurate performance metrics through the external Verilator flow, including:

- latency in cycles
- time at the target clock
- performance counters for the same parameter point

## Partial Results and Synth-Only Evidence

The study preserves **synth-only** Vivado evidence when implementation fails after synthesis.

That behaviour is important for architecture work, because failed implementation runs are often the strongest signals in the search space. A point that synthesises but does not implement still says something real about physical cost.

The controller therefore distinguishes between:

- **full implementation evidence**
- **provisional synth-only evidence**

Synth-only outcomes remain visible, are explicitly marked as provisional, and carry a ranking penalty. They are not treated as full passes.

This becomes critical at `replicated 8×8`, where synthesis metrics are preserved but implementation fails on the target device.

## Measured Architecture Study

The canonical measured study currently covers nine MAC-array candidates across baseline, shared, and replicated families.

### Baseline scaling

The baseline family scales monotonically in both latency and implementation cost:

| Candidate | Latency | LUT | DSP | WNS |
| --- | ---: | ---: | ---: | ---: |
| baseline 4×4 | 22 cycles | 689 | 16 | 3.028 ns |
| baseline 8×4 | 38 cycles | 1408 | 32 | 2.851 ns |
| baseline 8×8 | 70 cycles | 2730 | 64 | 1.490 ns |

Wider active arrays increase useful work, but also increase area and reduce timing slack.

![Canonical LUT vs latency](/figures/canonical_lut_vs_latency.png)

*Figure 1. Canonical LUT vs latency for full-pass measured candidates. Baseline scaling is monotonic, shared points stay close to baseline in LUT, and replicated points move sharply rightward in area.*

### Shared structures

The shared family consistently reduces DSP count relative to baseline while paying a modest schedule penalty:

| Candidate | Latency | LUT | DSP | WNS |
| --- | ---: | ---: | ---: | ---: |
| shared 4×4 | 26 cycles | 695 | 8 | 2.024 ns |
| shared 8×4 | 42 cycles | 1415 | 16 | 1.477 ns |
| shared 8×8 | 74 cycles | 2749 | 32 | 1.571 ns |

At `8×8`, the shared point is especially strong:

- latency rises only from `70` to `74` cycles
- LUT remains almost unchanged relative to baseline
- DSP drops from `64` to `32`

That is the cleanest measured example of sharing reducing physical cost without materially changing the shape of the design.

![Canonical DSP vs latency](/figures/canonical_dsp_vs_latency.png)

*Figure 2. Canonical DSP vs latency. Shared structures cut DSP materially at every measured size, while replicated structures preserve latency only by paying much higher compute cost.*

### Replicated structures

Replication preserves baseline-like latency where implementation still succeeds:

| Candidate | Latency | LUT | DSP | WNS |
| --- | ---: | ---: | ---: | ---: |
| replicated 4×4 | 22 cycles | 1212 | 32 | 4.034 ns |
| replicated 8×4 | 38 cycles | 2453 | 64 | 2.435 ns |

Those points preserve baseline schedule length, but at a clear area cost.

At `8×8`, replication no longer closes:

- `41892` LUT preserved from synthesis
- positive synth-stage timing still visible
- implementation fails before placement on the target Artix-7 device

The result is not a missing datapoint. It is a real limit point in the study.

![Family LUT scaling](/figures/family_scaling_lut.png)

*Figure 3. LUT scaling by architecture family. Shared remains close to baseline through 8×8, while replicated cost rises much faster and the replicated 8×8 point is only available as synth-only evidence.*

![Family latency scaling](/figures/family_scaling_latency.png)

*Figure 4. Latency scaling by architecture family. Shared introduces a near-fixed schedule penalty, while replicated matches baseline latency at measured full-pass points.*

## 8×8 Comparison

The `8×8` family comparison is the clearest single snapshot of the architecture tradeoff:

| Candidate | Outcome | Latency | LUT | DSP | WNS |
| --- | --- | ---: | ---: | ---: | ---: |
| baseline 8×8 | full pass | 70 | 2730 | 64 | 1.490 ns |
| shared 8×8 | full pass | 74 | 2749 | 32 | 1.571 ns |
| replicated 8×8 | synth-only | — | 41892 | — | 2.935 ns* |

\* synth-stage evidence only

This makes the 8×8 result straightforward:

- baseline 8×8 is a clean reference point
- shared 8×8 is also a clean full-pass point
- shared 8×8 is the strongest measured 8×8 tradeoff under the current score policy
- replicated 8×8 exceeds the implementation budget of the target part

![8×8 architecture comparison](/figures/eight_by_eight_comparison.png)

*Figure 5. Direct 8×8 comparison. Shared 8×8 preserves almost the same LUT and timing as baseline while halving DSP count. Replicated 8×8 is shown separately as an implementation-limited synth-only result.*

## Ranking and Score Sensitivity

The controller ranks candidates using an explicit score policy over:

- latency
- area
- timing
- penalties for incomplete or provisional evidence

Under the current official policy, the best measured candidate is:

**`mac_shared_4x4_sf2_dw16`**

The measured ranking currently begins:

1. shared 4×4  
2. baseline 4×4  
3. replicated 4×4  
4. shared 8×4  
5. baseline 8×4  
6. shared 8×8  
7. replicated 8×4  
8. baseline 8×8  

A separate score-sensitivity analysis was also run across alternative weighting schemes. The result is consistent:

- shared 4×4 wins under most tested policies
- replicated 4×4 wins under a timing-priority policy

So the robust findings are the measured architectural ones:

- shared reduces DSP materially
- replicated preserves latency where it still fits
- baseline scaling increases area and latency
- replicated 8×8 crosses a real implementation limit

The exact winner label depends on the score policy. The measured tradeoffs do not.

## Generated Evidence and Presentation Assets

On top of the canonical run model, the repository also generates a compact evidence bundle and presentation asset pack from the measured results.

Generated evidence includes:

- canonical result tables
- ranking reports
- score-policy sensitivity reports
- 8×8 diagnosis summaries
- current execution-state summaries

Generated presentation assets include:

- LUT vs latency
- DSP vs latency
- family scaling plots
- 8×8 comparison figures
- website / README-ready summary snippets

These assets are derived from the canonical evidence layer rather than being hand-assembled.

## Key Takeaways

- The project provides a deterministic control plane for bounded FPGA architecture studies over a parameterised MAC-array accelerator.
- Canonical run ownership, stage provenance, and explicit artifact resolution make the evidence layer reproducible and inspectable.
- Shared structures consistently reduce DSP usage while introducing only modest latency overhead.
- Replicated structures preserve baseline-like latency at smaller points, but their physical cost rises sharply with scale.
- Replicated `8×8` exposes a real target-device implementation limit rather than a tooling defect.
- Shared `8×8` is the strongest measured `8×8` tradeoff in the current evidence set.
- The repository functions both as a bounded architecture study and as a reusable experimentation framework for deterministic hardware evaluation.