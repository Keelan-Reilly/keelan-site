---
title: "Measured Tradeoffs in FPGA MAC-Array Architectures"
date: 2026-03-17
summary: "An empirical exploration of how compute sharing and replication shape the real-world behaviour of FPGA MAC-array accelerators, grounded in automated, reproducible hardware experiments."
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

## Introduction

Most discussions of accelerator design reduce to a simple idea: more parallelism leads to more performance. Wider arrays, more compute units, higher throughput. In practice, this view is incomplete. Once designs are mapped onto real hardware—especially FPGAs—physical constraints such as routing congestion, area limits, and timing closure begin to dominate.

This project explores that gap between architectural intuition and physical reality.

The focus is a simple but important question:

> how do different structural approaches to compute—baseline, shared, and replicated—actually behave when implemented on real hardware?

Rather than proposing a new architecture, the work takes an empirical approach. A small, controlled design space is explored and every point is measured using a consistent toolflow. The goal is not to optimise a single design, but to understand how different architectural choices scale—and where they stop working.

To make this possible, the entire workflow was automated. A Python-based controller drives candidate generation, verification, synthesis, implementation, and simulation, producing a deterministic set of results for each configuration. This ensures that every data point is directly comparable, and that failed implementations are preserved as part of the evidence rather than discarded.

This matters because many architectural ideas look equivalent at a high level, but diverge significantly under physical constraints. In FPGA-based systems in particular, where resources are fixed and routing is expensive, understanding these tradeoffs is critical.

---

## A Small but Revealing Design Space

The study is built around a parameterised MAC-array accelerator, representative of GEMM-style compute structures used in machine learning and signal processing.

Three architectural strategies are considered:

- **Baseline** — direct spatial mapping of compute  
- **Shared** — time-multiplexed compute to reduce resource usage  
- **Replicated** — duplicated compute to preserve throughput  

Rather than exploring a large search space, the study focuses on a bounded grid:

- `4×4`, `8×4`, `8×8`

This produces nine canonical configurations. The constraint is intentional: keeping the space small makes it possible to measure each point carefully and interpret the results clearly.

---

## What Happens When You Scale

The baseline architecture behaves as expected:

| Candidate | Latency | LUT | DSP | WNS |
| --- | ---: | ---: | ---: | ---: |
| baseline 4×4 | 22 cycles | 689 | 16 | 3.028 ns |
| baseline 8×4 | 38 cycles | 1408 | 32 | 2.851 ns |
| baseline 8×8 | 70 cycles | 2730 | 64 | 1.490 ns |

Increasing array size increases both performance and cost. Latency grows with the computation, and area grows with the number of compute units. Timing slack decreases as routing becomes more complex.

This provides a clean reference point: straightforward parallelism scales predictably, but not cheaply.

---

## Two Different Ways to Trade Resources

The more interesting behaviour emerges when comparing shared and replicated structures.

![Canonical LUT vs latency](/figures/canonical_lut_vs_latency.png)

*Figure 1. LUT versus latency across all implemented designs.*

This plot captures the core distinction between the two strategies:

- **Sharing moves horizontally** — slightly higher latency for similar area  
- **Replication moves vertically** — much higher area for similar latency  

In other words:

- sharing trades **time for hardware**  
- replication trades **hardware for time**  

These are fundamentally different ways of using resources, and they scale very differently.

---

## Sharing: Doing More with Less Hardware

| Candidate | Latency | LUT | DSP | WNS |
| --- | ---: | ---: | ---: | ---: |
| shared 4×4 | 26 cycles | 695 | 8 | 2.024 ns |
| shared 8×4 | 42 cycles | 1415 | 16 | 1.477 ns |
| shared 8×8 | 74 cycles | 2749 | 32 | 1.571 ns |

![Canonical DSP vs latency](/figures/canonical_dsp_vs_latency.png)

*Figure 2. DSP usage versus latency.*

The effect of sharing is consistent across all sizes:

- DSP usage is reduced by roughly 50%  
- latency increases only slightly  
- overall structure remains similar to baseline  

At `8×8`, this becomes especially clear:

- latency increases from 70 → 74 cycles  
- LUT cost is almost unchanged  
- DSP drops from 64 → 32  

This suggests that sharing does not fundamentally change the computation—it simply redistributes it over time. As a result, it achieves significant resource savings without disrupting the overall behaviour of the design.

---

## Replication: Fast, Until It Isn't

| Candidate | Latency | LUT | DSP | WNS |
| --- | ---: | ---: | ---: | ---: |
| replicated 4×4 | 22 cycles | 1212 | 32 | 4.034 ns |
| replicated 8×4 | 38 cycles | 2453 | 64 | 2.435 ns |

![Family LUT scaling](/figures/family_scaling_lut.png)

*Figure 3. LUT scaling across architecture families.*

Replication preserves baseline latency, but at a rapidly increasing cost in area. This is manageable at smaller sizes, but the trend is not sustainable.

At `8×8`, the design no longer implements:

- synthesis produces a valid design (~41892 LUT)  
- timing is still positive at synthesis  
- placement and routing fail on the target FPGA  

This is not a missing result—it is the most important one.

---

## A Hard Limit Appears

| Candidate | Outcome | Latency | LUT | DSP | WNS |
| --- | --- | ---: | ---: | ---: | ---: |
| baseline 8×8 | full pass | 70 | 2730 | 64 | 1.490 ns |
| shared 8×8 | full pass | 74 | 2749 | 32 | 1.571 ns |
| replicated 8×8 | synth-only | — | 41892 | — | 2.935 ns* |

\* synthesis-stage only

![8×8 architecture comparison](/figures/eight_by_eight_comparison.png)

*Figure 4. Direct comparison at 8×8.*

Up to `8×4`, replication appears viable. At `8×8`, it crosses a boundary and becomes physically unrealizable.

This reveals something important:

> architectural scaling is not continuous—there are hard feasibility thresholds imposed by the hardware.

The replicated design does not degrade gracefully. It simply stops working.

---

## What This Tells Us

Taken together, the results show three distinct behaviours:

- **Baseline** — predictable but increasingly expensive  
- **Shared** — efficient, with small and controlled performance cost  
- **Replicated** — optimal locally, but fundamentally limited  

The most important insight is not which design is “best”, but how differently they scale.

In particular:

- sharing provides a robust way to stay within resource limits  
- replication exposes a sharp boundary where physical constraints dominate  
- implementation failure is a meaningful and informative result  

---

## Limitations

This study is intentionally narrow. It focuses on a small set of array sizes, a single FPGA target, and does not consider power or energy.

However, this constraint is also a strength: it allows the behaviour of each architectural strategy to be observed clearly, without confounding variables.

---

## Closing Remarks

The main takeaway is simple:

> architectural ideas cannot be evaluated in isolation from the hardware they run on.

Even small structural changes—such as sharing or replication—can produce fundamentally different scaling behaviour when mapped onto a real device.

By keeping the design space small and the measurements rigorous, this project shows that meaningful architectural insight does not require large-scale exploration, but careful, grounded experimentation.