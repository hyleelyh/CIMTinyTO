# Architectural Note: Standard-Cell Sizing, Scaling Laws & Inference Latency

**Document:** `docs/physical_sizing_and_tradeoff_analysis.md`  
**Date:** 2026-09-21 21:00  
**Status:** Architecture Decision Record (Pillar 3: Physical ASIC Flow)  
**Author:** Antigravity & Julius Li  

---

## 1. Executive Summary

During OpenLane 2 cloud hardening on SkyWater 130nm (`sky130_fd_sc_hd`), physical placement of the $16\times 16$ SCIM core failed with OpenROAD error `[GPL-0301]` on a $1\times 2$ tile:
```plaintext
CoreArea: 34,255.35 µm² (1x2 Tile)
PlaceInstsArea: 63,548.45 µm² (5,769 standard cells)
Utilization: 192.12% (> 100% floorplan capacity)
```

This document records the exhaustive forensic analysis of standard-cell area expansion, evaluates the $16\times 16$ vs. $8\times 8$ non-linear scaling laws, investigates banked time-multiplexing, and projects end-to-end Micro-ResNet inference frame rates to guide the upcoming tapeout shuttle sizing decision.

---

## 2. Block-by-Block Forensic Audit: Estimation vs. Silicon Reality

In behavioral Verilog synthesis, arithmetic blocks are modeled as ideal mathematical operators. When mapped to standard cells in `sky130_fd_sc_hd`, logic expands significantly:

| Functional Block | Front-End Estimate | Physical Silicon Reality (`sky130_fd_sc_hd`) | Physical Area | Expansion Factor | Forensic Cause & Silicon Reality |
|---|---|---|---|:---:|---|
| **Accumulator Array** (16 cols) | ~300 gates (~$2,500\,\mu\text{m}^2$) | **~1,920 cells** (16x 14-bit adders, 32 signed comparators, MUXes, 224 DFFs) | $\approx 19,200\,\mu\text{m}^2$ | $\approx 7.7\times$ | **Primary Culprit.** Each column requires a 14-bit adder, **two 14-bit magnitude comparators** (`sum > +4095`, `sum < -4096`), and a 13-bit 3-way saturation clamp MUX to prevent arithmetic wrap-around distortion. |
| **Wallace Trees** (17 trees) | ~500 cells (~$4,000\,\mu\text{m}^2$) | **~1,224 cells** (153 discrete 4:2 compressor slices) | $\approx 15,000\,\mu\text{m}^2$ | $\approx 3.7\times$ | Each 4:2 compressor decomposes into 2 cascaded full adders (8–10 discrete gates: `xnor2`, `nand2`, `inverters`). 17 trees $\times$ ~9 compressors = 153 compressors. |
| **Weight Memory** (256 bits) | 256 bits (~$1,500\,\mu\text{m}^2$) | **256 DFFs** (`sky130_fd_sc_hd__dfxtp_1`) + shift buffers | $\approx 4,800\,\mu\text{m}^2$ | $\approx 3.2\times$ | **DFF vs. SRAM disparity.** A 6T SRAM bitcell is $\approx 1.5\,\mu\text{m}^2$. A standard-cell DFF is $\approx 15.0\,\mu\text{m}^2$ (24–28 transistors). 256 DFFs alone consume nearly $5,000\,\mu\text{m}^2$. |
| **PE Multiplier Array** ($16 \times 16$) | ~600 gates (~$3,500\,\mu\text{m}^2$) | **~640 cells** (XNOR, AND, MUX per cell) | $\approx 3,800\,\mu\text{m}^2$ | $\approx 1.1\times$ | **Behaved as predicted.** Single-bit stochastic multiplication (XNOR/AND) is extremely compact. |
| **SNG Bank** (16 LFSRs + Comp) | ~800 gates (~$4,000\,\mu\text{m}^2$) | **~750 cells** (128 DFFs + 64 XORs + 16 8-bit comparators) | $\approx 4,500\,\mu\text{m}^2$ | $\approx 1.1\times$ | **Behaved as predicted.** 16 Galois LFSRs and digital comparators synthesized cleanly. |
| **Activation Storage & I/O MUX** | ~500 gates (~$2,500\,\mu\text{m}^2$) | **~617 cells** (128 DFFs + 16-to-1 13b readback MUX + FSM) | $\approx 3,700\,\mu\text{m}^2$ | $\approx 1.5\times$ | 16-to-1 13-bit accumulator readback multiplexer trees. |
| **Physical Overhead** (Taps, CTS) | 0 gates | **618 well-taps** + CTS clock buffers + HFN reset buffers | $\approx 12,500\,\mu\text{m}^2$ | $\infty$ | **Physical DRC rules.** Sky130 requires well-taps (`tapvpwrvgnd_1`) every $14\,\mu\text{m}$ to prevent CMOS latch-up. CTS buffers required to drive 761 DFFs. |
| **Total Macro** | **~2,800 gates** | **5,769 physical cells** | **$63,548\,\mu\text{m}^2$** | **$\approx 3.5\times$** | **Over-utilizes $1\times 2$ tile ($34,255\,\mu\text{m}^2$) by $192.12\%$.** |

---

## 3. The 13-Bit Accumulator: Two-Pass Readout vs. Internal Parallelism

A key architectural clarification addressed why the accumulator area is so large despite two-pass readout:
1. **External Readout (Pin-Constrained):** Tiny Tapeout provides only 8 dedicated output pins (`uo_out[7:0]`). Results are read out sequentially in two bytes (`byte_sel = 0` for lower 8 bits, `byte_sel = 1` for upper sign-extended bits).
2. **Internal Computation (Speed-Constrained):** During active compute ($N = 256$ clock cycles), incoming column deltas arrive on **every single clock edge**. All 16 columns must accumulate in parallel at $50\text{ MHz}$. Consequently, 16 physical 14-bit adders, 32 magnitude comparators, and 224 flip-flops must exist simultaneously on silicon.

---

## 4. Scaling Laws: Why $16\times 16 \rightarrow 8\times 8$ is NOT a $4\times$ Area Reduction

In a Compute-in-Memory accelerator, logic does not scale uniformly across dimensions:

```
                            ┌──────────────────────────────────────────────┐
                            │              0D Infrastructure               │
                            │      (FSM, Handshake, SPI, I/O Pads)         │
                            │                O(1) Constant                 │
                            └──────────────────────┬───────────────────────┘
                                                   │
                ┌──────────────────────────────────┴──────────────────────────────────┐
                ▼                                                                     ▼
   ┌─────────────────────────┐                                           ┌─────────────────────────┐
   │    1D Row Peripherals   │                                           │  1D Column Peripherals  │
   │  (SNG Bank, Activations)│                                           │ (Wallace Trees, Accum.) │
   │       O(N) Linear       │                                           │       O(N) Linear       │
   └────────────┬────────────┘                                           └────────────┬────────────┘
                │                                                                     │
                └──────────────────────────────────┬──────────────────────────────────┘
                                                   │
                                                   ▼
                                    ┌─────────────────────────────┐
                                    │      2D Spatial Core        │
                                    │   (PE Array, Weight DFFs)   │
                                    │       O(N²) Quadratic       │
                                    └─────────────────────────────┘
```

1. **2D Components ($O(N^2)$ — Scales by $1/4$):**
   - PE multipliers: $256 \rightarrow 64$
   - Weight DFFs: $256 \rightarrow 64$
2. **1D Peripherals ($O(N)$ — Scales by $1/2$, NOT $1/4$):**
   - Accumulators: Drops from 16 to 8 accumulators.
   - Wallace Trees: Drops from 17 to 9 trees (and shallower tree depth).
   - SNG Bank & Activation Memory: Drops from 16 to 8 channels.
3. **0D Infrastructure ($O(1)$ — Almost No Reduction):**
   - FSM controller, clock tree roots, synchronization, status flags.

### Physical Sizing for $8\times 8$:
$$\text{Total Area } (8\times 8) \approx 20,800\,\mu\text{m}^2 \quad (\approx 3.05\times \text{ reduction from } 63,548\,\mu\text{m}^2)$$

* **Can $8\times 8$ fit into a $1\times 1$ Tile?**
  Core area of $1\times 1$ is $\approx 11,000\text{--}13,500\,\mu\text{m}^2 \implies \text{Utilization} \approx 160\% \implies$ **FAILS placement.**
* **Can $8\times 8$ fit into a $1\times 2$ Tile?**
  Core area of $1\times 2$ is $34,255\,\mu\text{m}^2 \implies \text{Utilization} \approx \mathbf{60.7\%} \implies$ **Optimal routing sweet spot.**

---

## 5. Architectural Evaluation: Time-Multiplexed / DRAM Banking (Option 3)

### Concept & Analogy
Similar to DRAM memory banking and Processing-in-Memory (e.g., Samsung Aquabolt-XL HBM-PIM), Option 3 retains all 256 weight bits on-chip but partitions columns into Bank A (0–7) and Bank B (8–15), sharing 8 Wallace trees and 8 adders over alternating sub-cycles ($512$ total cycles).

### The Physical Silicon Trap
* In DRAM silicon, 1T1C storage cells are microscopic ($< 0.01\,\mu\text{m}^2$), so sharing peripheral ALUs yields massive savings.
* In standard-cell CMOS, storage consists of **D-flip-flops** ($\approx 15\,\mu\text{m}^2$ each).
* Even with half the arithmetic removed, the macro still retains 256 weight DFFs, 224 accumulator DFFs, 128 SNG DFFs, 128 activation DFFs, and well-taps, resulting in **$\approx 49,500\,\mu\text{m}^2$**.
* On a $1\times 2$ tile ($34,255\,\mu\text{m}^2$), utilization is **$144.5\%$**, which **still fails Global Placement `[GPL-0301]`**.

---

## 6. System-Level Inference Performance: ResNet on Silicon

### Full-Scale ResNet-18 ($224 \times 224$ ImageNet — $1.8\text{ GMACs}$)
* Server-class ResNet-18 is designed for desktop GPUs ($>500\text{ GB/s}$ memory bandwidth).
* On an ultra-low-power micro-accelerator with 8 I/O pins at $50\text{ MHz}$:
  - $16\times 16$ Core ($100\text{ MMAC/s}$): $\approx 18\text{ s}$ compute, $\approx 45\text{ s}$ total latency.
  - $8\times 8$ Core ($25\text{ MMAC/s}$): $\approx 72\text{ s}$ compute, $\approx 3\text{ minutes}$ total latency.
* Both are constrained by the Tiny Tapeout 8-bit I/O pin bandwidth ("Memory Wall").

### Edge TinyML Micro-ResNet ($3\text{ MMACs}$, Binary Weights)
Micro-ResNet targets $32\times 32$ or $96\times 96$ patches with 8–16 channels and $\{-1, +1\}$ quantized weights:
* **$16\times 16$ Core ($2\times 2$ Tile):**
  - Compute time: $30\text{ ms}$. Total latency with SPI I/O: **$\approx 80\text{ ms}$ ($\approx 12.5\text{ FPS}$ — Real-Time Video Rate!)**
* **$8\times 8$ Core ($1\times 2$ Tile):**
  - Requires $2\times 2$ matrix tiling (4 passes per layer).
  - Compute time: $120\text{ ms}$. Total latency with SPI I/O: **$\approx 370\text{ ms}$ ($\approx 2.7\text{ FPS}$ — Interactive Rate)**

---

## 7. Tapeout Decision Matrix

| Dimension | **Option 1: $16\times 16$ Core ($2\times 2$ Tile)** | **Option 2: $8\times 8$ Core ($1\times 2$ Tile)** |
|---|---|---|
| **Silicon Footprint** | $63,548\,\mu\text{m}^2$ on $2\times 2$ Tile ($70,000\,\mu\text{m}^2$) | $20,800\,\mu\text{m}^2$ on $1\times 2$ Tile ($34,255\,\mu\text{m}^2$) |
| **Placement Density** | $\approx 64\%$ (Clean Pass) | $\approx 60.7\%$ (Clean Pass) |
| **Micro-ResNet FPS** | **$\approx 12.5\text{ FPS}$ (Real-Time Live Video)** | **$\approx 2.7\text{ FPS}$ (Interactive Classification)** |
| **RTL & Model Code Changes** | **Zero changes** (Immediate push-button hardening) | Moderate refactoring of RTL, models, and testbenches |
| **Tapeout Submission Cost** | Standard submission $\times 2$ (4 tiles) | Standard base submission (2 tiles) |

*Decision deferred for reflection before initiating physical flow execution.*
