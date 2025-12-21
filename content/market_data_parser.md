---
title: "FPGA Market Data Parser (Low-Latency Pipeline)"
date: 2025-12-20
summary: "This project implements a low-latency market data ingestion pipeline in SystemVerilog. I built it to understand how protocol handling, backpressure, and control timing shape end-to-end latency in real hardware pipelines."
repo: "https://github.com/Keelan-Reilly/low_latency_market_parser"
kpis:
  - label: "End-to-end latency (ingress → decision)"
    value: "~38 cycles"
    note: "≈ 152 ns @ 250 MHz (simulation)"
  - label: "Clock target"
    value: "250 MHz"
    note: "Closed with positive slack in Vivado"
  - label: "Verification"
    value: "Cycle-accurate"
    note: "Verilator + Python reference models"
---

## Introduction

Unlike arithmetic-heavy accelerators, protocol-facing hardware is dominated by control flow, state, and timing constraints. Bytes arrive sequentially, fields are interdependent, and downstream stalls must be handled without losing or duplicating data. Latency is shaped less by computation than by how early decisions can be made and how cleanly backpressure propagates.

This project explores those constraints by implementing a complete market-data ingestion pipeline on FPGA: Ethernet framing, CRC verification, ITCH message parsing, and a simple decision stage. The focus is not trading strategy, but the mechanics of building a lossless, latency-aware hardware pipeline.

## System behaviour

The system consumes an Ethernet byte stream, detects valid frames, verifies CRC-32, filters destination MAC addresses, and streams ITCH payload bytes into a parser. For trade (‘P’) messages, selected fields are extracted and dispatched to a small decision block. Decisions are emitted over a UART interface.

The entire pipeline is built around explicit valid/ready handshakes. No data is dropped, duplicated, or reordered under backpressure.

## Pipeline structure

The design is organised as a sequence of narrowly scoped stages:

- Ethernet RX with preamble/SFD detection, MAC filtering, and CRC-32 verification  
- ITCH parser with early dispatch on the final price byte  
- One-deep registered boundaries between stages to isolate timing and propagate stalls  
- A minimal decision block that emits results when conditions are met  

Skid buffers are used where fall-through behaviour is safe; registered slices are used where timing isolation is required.

## Early dispatch and latency

A key optimisation is early dispatch in the parser. Rather than waiting for the full ITCH message to drain, the parser asserts a valid event on the cycle the final price byte arrives. This allows the decision stage to trigger immediately, without bubbles between parsing and logic.

At 250 MHz, the resulting end-to-end latency from message ingress to decision availability is 38 cycles (≈ 152 ns) in simulation.

## Backpressure and correctness

Every interface in the pipeline honours backpressure. If the UART stage stalls, decisions are buffered and upstream stages naturally pause without losing alignment. The design was intentionally stress-tested with periodic sink stalls to ensure correctness under non-ideal conditions.

Several early bugs only appeared once realistic backpressure and multi-cycle delays were introduced, reinforcing the importance of protocol-accurate handshakes even in simple pipelines.

## Verification

Verification is cycle-accurate and protocol-focused. A C++ Verilator harness replays real packet traces, injects controlled stalls, and records timestamps at each pipeline boundary. Python reference models independently parse packets, recompute CRCs, and validate extracted fields.

Correctness is defined structurally as well as functionally: stable outputs during stalls, one-to-one correspondence between input messages and output events, and monotonic timestamps.

## What this establishes

This project demonstrates how low latency in hardware is primarily a control problem. The dominant challenges are not arithmetic throughput, but deciding *when* information becomes actionable, how long it must be retained, and how stalls propagate without corrupting state.