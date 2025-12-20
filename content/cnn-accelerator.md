---
title: "Quantised CNN Inference Accelerator"
date: 2025-12-20
summary: "This project implements a complete CNN inference pipeline in SystemVerilog. I built it to understand the tradeoffs of fixed-function hardware accelerators: the performance gains they deliver, and the flexibility they give up when data movement, arithmetic precision, and control timing are handled explicitly in hardware."
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

## Introduction

Neural network inference is a natural fit for accelerators because most of the work is structured arithmetic over predictable dataflows. CPUs retain flexibility by deferring decisions to runtime, but pay for that in instruction overhead, data movement, and unpredictable latency. Fixed-function accelerators recover efficiency by hard-wiring those decisions: memory layout, precision, and execution order are chosen once and enforced in hardware. This project explores that trade-off directly by implementing an entire inference pipeline without a CPU or software runtime.

The target application is MNIST digit classification. The model is deliberately small, which makes it possible to reason about the entire system end to end while still exercising the same structural issues as larger accelerators: staged computation, fixed-point numerics, explicit memory interfaces, and latency-aware control.

## System behaviour

The system receives a 28×28 grayscale image over UART, stores it in on-chip memory, processes it through a fixed pipeline (convolution, ReLU, max-pooling, dense, argmax), and transmits the predicted digit as a single ASCII character. Once the frame is loaded, the pipeline runs autonomously in hardware. There is no instruction fetch, scheduler, or control processor involved.

## Pipeline control

The pipeline is organised as a sequence of independent stages. Each stage is triggered by a single-cycle start pulse, asserts busy while active, and emits a single-cycle done pulse on completion. While active, a stage has exclusive ownership of its input and output memories. This structure avoids ambiguity once non-zero memory latency is introduced and makes stage boundaries explicit during integration and verification.

## Memory and addressing

All feature maps are stored in BRAM-backed memories using a simple CHW-linear layout. Address generation is entirely deterministic and counter-driven, and every output address is written exactly once. This layout is not maximally efficient, but it is fully observable and exhaustively verifiable. Several early bugs came from violating this assumption—writes occurring one cycle too early or too late produced numerically plausible but incorrect outputs—so the final design and testbenches enforce write-once and post-completion invariants explicitly.

## Fixed-point numerics

All arithmetic is signed fixed-point. Inputs are quantised through a lookup table. Weights and biases are stored as signed constants. Multiply-accumulate operations use widened accumulators to absorb growth, followed by a right shift and explicit saturation to the output width. Fixed-point behaviour is defined precisely and mirrored bit-for-bit in the reference models; approximate agreement is not sufficient when validating hardware.

## Stage details and timing failure modes

The convolution stage is where most control complexity appears. It implements SAME padding, iterates explicitly over channels and kernel taps, and accumulates into a wide register before scaling and saturation. Reads are issued to a BRAM-like interface with configurable latency, and the control FSM waits for data to return before consuming it. One subtle bug only appeared once memory latency exceeded a single cycle: advancing the address counter and accumulation logic together caused data from different kernel positions to mix. This failure mode was invisible under single-cycle memory and only surfaced once latency was parameterised in the testbench.

ReLU is implemented as an in-place read-modify-write operation using a dual-port memory. Each read must correspond to a write a fixed number of cycles later to the same address. Early versions failed silently when reads and writes overlapped incorrectly, particularly when addresses were reused. The final testbench tracks read addresses through the pipeline delay and asserts alignment cycle-by-cycle. Mixed-sign and adversarial input patterns are used to catch errors that positive-only tests would miss.

Max-pooling reads four values per output element in a fixed spatial order and performs signed comparisons. While functionally simple, addressing errors are easy to introduce. The testbench asserts the exact read sequence for every pooling window and fails immediately on any deviation. Dense and argmax stages follow the same philosophy: accumulator width, bias alignment, saturation, and tie-breaking behaviour are explicit and verified, not inferred from outputs.

## Verification

Verification is stage-driven and protocol-focused. Each module has a dedicated testbench consisting of a BRAM-like memory model with configurable latency, a bit-exact golden model matching RTL semantics, and assertions enforcing interface contracts. Writes after done, duplicate writes, out-of-range accesses, or multi-cycle done pulses are treated as fatal errors, even if numerical results appear correct. Several early designs “worked” only because the testbenches were too permissive; tightening the memory and protocol models exposed control bugs immediately.

Full-system verification uses Verilator for cycle-accurate simulation. The quantised RTL achieves approximately 92.2% accuracy on the MNIST test set, compared to 94.3% for a simple floating-point PyTorch model trained for one epoch. The difference is attributable to quantisation and saturation; the RTL matches the fixed-point reference exactly.

## Performance

The compute pipeline requires roughly 466k cycles at 100 MHz (≈ 4.7 ms). End-to-end latency, including UART receive and transmit at 115,200 baud, is approximately 7.28 million cycles (≈ 73 ms). UART I/O dominates total latency; the design prioritises correctness, determinism, and observability rather than throughput optimisation.

## What this establishes

The main outcome of this project was understanding what fixed-function optimisation commits you to. Memory layout, datapath width, scaling, and control structure are all tuned to a specific workload. Those choices deliver efficiency, but they also define the points where adaptability would require redesign. This accelerator serves as a concrete baseline: it shows what you gain by hard-wiring decisions, and what would need to become tunable in a reconfigurable design.