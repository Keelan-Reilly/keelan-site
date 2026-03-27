---
title: "Compute Sharing in FPGA MAC Arrays Isn't a Smooth Tradeoff"
date: 2026-03-26
---

There's a common way this conversation goes in FPGA design. Someone suggests time-multiplexing a compute unit to save resources, and the response is either "great, that saves LUTs" or "bad, that kills throughput." Both answers are technically true and practically useless, because neither one tells you *when* the tradeoff makes sense.

I wanted a more concrete answer for a small family of MAC-array implementations, so I built all three variants, ran them through a full synthesis and routing flow on the Basys 3, and measured what actually happened.

In this design family, compute sharing isn't a gradual tradeoff — it's a fixed cost you only accept when you run out of the right resource.

## The setup

The family has three members. The **baseline** gives every MAC unit its own dedicated hardware — fully parallel, nothing shared. The **LUT-saving** variant time-multiplexes the compute, keeping DSP usage the same but reducing LUT consumption. The **DSP-eliminating** variant also time-multiplexes, but goes further and removes DSP usage entirely.

I measured all three at three array sizes — 16, 32, and 64 MAC units — with a fixed accumulation depth of 32. Everything that follows is grounded in those configurations only.

## The chip budget

The XC7A35T is a modest chip. Knowing where its ceilings are changes how you read the results.

| Resource | Available | Baseline (64 MAC) | LUT-saving (64 MAC) | DSP-eliminating (64 MAC) |
|---|---|---|---|---|
| LUTs | 20,800 | 4,287 (21%) | 2,694 (13%) | 3,620 (17%) |
| DSPs | 90 | 64 (71%) | 64 (71%) | 0 (0%) |
| FFs | 41,600 | 2,060 (5%) | 1,555 (4%) | 2,324 (6%) |

LUTs and flip-flops are barely touched even at the largest configuration. DSPs are a different story — baseline and the LUT-saving variant both consume 64 of 90 at that scale, leaving almost no room for any other DSP-heavy logic on the chip. The DSP-eliminating variant uses none. Keep that in mind as you read the rest.

## Both shared variants pay the same penalty

The answer is the same for both. It's structural.

Baseline latency is 33 cycles; both shared variants take 65. Throughput drops to about half of baseline at every array size, with no difference between the two shared implementations.

This means the performance question and the resource question are separable. You don't get a better or worse schedule depending on *which* shared variant you pick — you just get a different bottleneck relieved. If the shorter schedule or full throughput is a hard requirement, both shared implementations are off the table regardless of how the resource situation looks.

![Figure 1 — latency vs MAC units](/figures/final_tradeoff_figures/latency_vs_mac_units.png)
*Figure 1. Baseline holds flat at 33 cycles across all array sizes. Both shared variants hold flat at 65. This follows directly from the architecture.*

![Figure 2 — throughput vs MAC units](/figures/final_tradeoff_figures/throughput_vs_mac_units.png)
*Figure 2. Baseline throughput scales linearly with MAC units. Both shared variants track each other at roughly half of baseline — identical to each other, identical across sizes.*

## The resource savings are not the same

The two shared implementations diverge on which resource they actually relieve.

The LUT-saving variant reduces LUT usage by about 37% relative to baseline, with DSP usage unchanged. The DSP-eliminating variant removes all DSP usage — going from 71% utilisation at the largest configuration down to zero — but its LUT savings are weaker and its flip-flop usage is higher.

On a device with a large DSP budget, these tradeoffs are comparable. On the XC7A35T, they aren't. The LUT-saving variant addresses a resource you have plenty of. The DSP-eliminating variant addresses the one that's actually scarce. A 37% LUT reduction sounds meaningful until you remember you're starting at 21% utilisation.

![Figure 3 — LUT vs MAC units](/figures/final_tradeoff_figures/lut_vs_mac_units.png)
*Figure 3. Both shared variants reduce LUT relative to baseline, with the LUT-saving variant giving the larger reduction at every scale. On this chip the absolute numbers are all well within headroom.*

![Figure 4 — DSP vs MAC units](/figures/final_tradeoff_figures/dsp_vs_mac_units.png)
*Figure 4. Baseline and the LUT-saving variant both scale with array size. The DSP-eliminating variant sits at zero across all three sizes — on a 90-DSP chip, this is the axis that matters.*

## When does sharing make sense?

Only when the resource it relieves is the actual bottleneck.

| Situation on XC7A35T | Recommended choice |
|---|---|
| LUT and DSP budgets are comfortable, throughput matters | Baseline |
| You need DSP headroom for other logic alongside the MAC array, and the longer schedule is acceptable | DSP-eliminating variant |
| LUT budget is genuinely tight, DSP budget is fine | LUT-saving variant |

The realistic choice on this device collapses to two options: baseline when you need the performance and DSPs aren't a problem, the DSP-eliminating variant when you need those DSPs for something else. In practice, the LUT-saving variant is rarely the right answer here. You run into DSP pressure first.

![Figure 5 — decision surface](/figures/final_decision_surface_figures/supported_choice_regions.png)
*Figure 5. The three-way decision surface across LUT and DSP budget space. On the XC7A35T, you hit DSP pressure long before you approach any LUT limit.*

## A note on timing

Worst-case slack varies enough across implementations and sizes that I'm not comfortable deriving a smooth switching rule from it. The slower speed grade on this part makes timing harder to generalise. Check it with a fresh implementation run rather than inferring it from the baseline.

## The takeaway

Sharing is a fixed cost. The only question is whether you're forced to pay it.

On the XC7A35T, LUTs are not scarce. DSPs are. That makes the DSP-eliminating variant the more practically relevant of the two shared options on this chip — not because it's universally better, but because it addresses the constraint you're actually likely to hit.

---

*Target device: XC7A35T-1CPG236C (Basys 3). Available resources: 20,800 LUTs, 41,600 flip-flops, 90 DSP slices. Measurements taken post-routing at three array sizes with a fixed accumulation depth of 32. Interpolation accepted within the measured range only.*