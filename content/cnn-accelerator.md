---
title: "Quantised CNN Inference Accelerator"
date: 2025-12-20
summary: "A fixed-function FPGA CNN inference accelerator implemented in SystemVerilog. The project explores how architectural decisions around data layout, precision, and scheduling affect performance and flexibility."
math: true
repo: "https://github.com/Keelan-Reilly/CNN_FPGA"
kpis:
  - label: "Compute latency (frame loaded → TX start)"
    value: "~466k cycles"
    note: "≈ 4.7 ms @ 100 MHz"
  - label: "End-to-end latency (UART RX + compute + UART TX)"
    value: "~7.28M cycles"
    note: "≈ 73 ms @ 115,200 baud"
  - label: "MNIST accuracy"
    value: "~92.2%"
    note: "Float baseline: ~94.3% (1 epoch)"
---

# Quantised CNN Inference Accelerator

This project implements a complete convolutional neural network inference pipeline in SystemVerilog on an FPGA.

The goal was to study what changes when neural network inference is implemented as fixed-function hardware rather than software on a CPU.

The accelerator receives an MNIST image over UART, processes it through a fully hardware pipeline, and transmits the predicted digit. No CPU, runtime, or instruction execution is involved. All scheduling, memory access, and arithmetic behaviour are defined directly in hardware.

The project explores two questions:

- What engineering challenges appear when implementing an inference pipeline directly in RTL?
- How do architectural choices affect performance, area, and timing once the design is synthesised?

# System Overview

The system receives a **28×28 grayscale image** over UART and processes it through a fixed pipeline:

**convolution → ReLU → max-pool → dense → argmax → UART transmit**

Once a frame is loaded, the accelerator runs autonomously until the classification result is produced.

There is no control processor or software runtime. Instead, each stage is implemented as a hardware module with explicit control signals and deterministic memory access patterns.

# Pipeline Control

The pipeline is organised as a sequence of stages controlled by a top-level FSM.

Each stage exposes a simple protocol:

- `start` pulse initiates execution
- `busy` remains asserted while the stage runs
- `done` pulses when the stage completes

While active, a stage has exclusive ownership of its input and output memories. This design avoids ambiguity when memory latency exceeds a single cycle and makes stage boundaries explicit during verification.

The resulting architecture is **sequential rather than pipelined**: stages execute one after another rather than overlapping.

# Memory Organisation

Feature maps are stored in BRAM-backed memories using a simple **channel-height-width (CHW) linear layout**.

Address generation is entirely deterministic and driven by counters.

Every output location is written exactly once.

This layout prioritises **observability and verifiability** over maximum efficiency. Early bugs occurred when writes were issued one cycle too early or late, producing outputs that looked numerically plausible but were incorrect. The final design enforces:

- write-once semantics
- strict address sequencing
- completion invariants verified in simulation

# Fixed-Point Arithmetic

All arithmetic uses signed fixed-point representation.

Inputs are quantised using lookup tables, while weights and biases are stored as signed constants. Multiply-accumulate operations use widened accumulators to absorb dynamic range growth before scaling and saturation back to the output width.

The hardware behaviour is mirrored bit-for-bit in a reference model used during verification. Approximate agreement is insufficient — the RTL must exactly match the fixed-point semantics.

The resulting design achieves **92.2% MNIST accuracy**, compared to **94.3%** for a simple floating-point PyTorch model trained for one epoch.

# Stage Implementation Details

### Convolution

The convolution stage implements SAME padding and iterates explicitly over channels and kernel taps. Data is fetched from BRAM through an interface with configurable latency.

A subtle control bug only appeared once memory latency exceeded a single cycle: advancing the address counter and accumulation logic together caused values from different kernel positions to mix. This error was invisible under single-cycle memory but surfaced immediately once latency was parameterised in the testbench.

### ReLU

ReLU is implemented as an in-place read-modify-write operation using dual-port memory. Each read must correspond to a write a fixed number of cycles later.

Early versions failed silently when reads and writes overlapped incorrectly. The final testbench tracks read addresses through the pipeline delay and asserts alignment cycle-by-cycle.

### Max-Pooling

Max-pool reads four values per output element and performs signed comparisons. While functionally simple, addressing errors are easy to introduce. The testbench therefore asserts the exact read sequence for every pooling window.

### Dense and Argmax

The dense stage performs multiply-accumulate operations over the flattened feature map, followed by scaling and saturation. Argmax selects the highest output value with deterministic tie-breaking behaviour.

# Verification

Verification is **protocol-driven rather than output-driven**.

Each module has its own testbench consisting of:

- a BRAM-like memory model with configurable latency
- a bit-exact golden reference model
- assertions enforcing interface contracts

Failures such as:

- writes after `done`
- duplicate writes
- out-of-range accesses
- multi-cycle `done` pulses

are treated as fatal errors even if the final numerical output appears correct.

Full-system verification uses **Verilator** for cycle-accurate simulation.

# Performance

The compute pipeline requires roughly:

$$
465{,}732 \text{ cycles at } 100\ \text{MHz} \approx 4.7\ \text{ms}
$$

Stage-level cycle counters show where time is spent:

| Stage | Cycles | Share |
|------|------|------|
| Convolution | 344,962 | 74% |
| ReLU | 25,090 | 5% |
| Max-pool | 32,930 | 7% |
| Dense | 62,732 | 14% |
| Argmax | 11 | ~0% |

This baseline stage breakdown motivated the later architecture study, since it immediately suggested that convolution rather than dense was the dominant bottleneck.

End-to-end latency including UART I/O is approximately **73 ms**, meaning communication dominates total runtime.

# Architecture Experiments

After validating the accelerator, a series of experiments were run to study architectural trade-offs.

Experiments are automated using a batch flow that collects:

- post-route area and timing from Vivado
- cycle-accurate performance from Verilator
- per-stage cycle counters

Results are stored in `results/fpga/aggregates`.

# Dense Parallelism Scaling

The main experiment varies the dense layer parallelism parameter:

$$
P \in \{1,2,5,10\}
$$

where \(P\) denotes the dense-output parallelism parameter in the RTL.

![Stage cycle breakdown vs dense parallelism](/figures/stage_cycles_breakdown_vs_DENSE_OUT_PAR.png)

*Stage cycle breakdown showing that convolution remains constant while dense latency decreases with parallelism.*

Dense stage latency scales almost ideally:

| Parallelism | Dense cycles |
|-------------|-------------|
| 1 | 62,732 |
| 2 | 31,367 |
| 5 | 12,548 |
| 10 | 6,275 |

However, total accelerator latency improves only modestly:

| Parallelism | Total latency |
|-------------|---------------|
| 1 | 465,732 cycles |
| 10 | 409,275 cycles |

This corresponds to only **~1.14× end-to-end speedup**.

![Latency vs dense parallelism](/figures/latency_cycles_vs_DENSE_OUT_PAR.png)

*Total latency decreases only modestly because the convolution stage dominates runtime.*

The reason is visible in the stage breakdown: convolution remains constant at ~345k cycles and dominates the total runtime.

Increasing dense parallelism therefore accelerates the dense block but quickly leaves the system **convolution-bound**.

Area cost also grows significantly:

| Parallelism | LUT | DSP |
|-------------|-----|-----|
| 1 | 2,720 | 5 |
| 10 | 19,061 | 23 |

The result demonstrates a common accelerator design lesson: **local block speedups do not necessarily translate into global system speedups**.

# Precision vs Resource Study

A second experiment varies arithmetic precision while keeping the architecture fixed.

Formats tested were **Q12.5**, **Q14.6**, and **Q16.7**.

Latency remains constant across all formats because the controller schedule does not change. The primary effect is implementation cost:

| Format | LUT | FF | BRAM |
|------|------|------|------|
| Q12.5 | 2649 | 900 | 5 |
| Q16.7 | 2720 | 1004 | 6 |

This confirms that precision changes primarily affect **area and timing**, not the accelerator's cycle schedule.

# Analytical Latency Model

A simple analytical model was implemented to predict latency.

Because the architecture is sequential, total latency can be decomposed as

$$
L_{\text{total}} = L_{\text{fixed}} + L_{\text{dense}}.
$$

The fixed component is approximately

$$
L_{\text{fixed}} \approx 403\,\text{k cycles},
$$

which includes convolution, ReLU, pooling, argmax, and control overhead.

For the dense stage,

$$
L_{\text{dense}} = \lceil C/P \rceil\, W
$$

where \(C\) is the number of classes, \(P\) is the dense-output parallelism, and \(W\) is the work per output.

For the dense-parallelism sweep, this model matches measured latency exactly, demonstrating that the accelerator's behaviour is well explained by a simple stage-level decomposition.

![Measured vs predicted latency](/figures/measured_vs_predicted_latency_vs_DENSE_OUT_PAR.png)

*Measured latency matches the analytical latency model across the dense parallelism sweep.*

# Key Takeaways

This project illustrates the trade-offs inherent in fixed-function hardware acceleration.

Hard-wiring decisions about:

- memory layout
- arithmetic precision
- execution order
- control timing

removes software overhead and yields deterministic performance. However, it also commits the design to a specific workload and exposes architectural bottlenecks directly.

In this accelerator, the convolution stage dominates total runtime. Improving dense parallelism therefore provides only limited end-to-end gains. The next architectural step would be exploring **convolution parallelism or dataflow changes** rather than further scaling the dense layer.

The design therefore serves as both a working accelerator and a concrete baseline for understanding how microarchitectural choices translate into real hardware performance.
