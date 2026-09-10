# Pillar 1: System & Mathematical Modeling (Gate 0) Specification

## 1. Executive Summary & Pedagogical Scope

In ASIC design, **Gate 0** is the prerequisite phase where algorithms are translated into hardware-viable mathematics before writing a single line of synthesizable RTL. A bug discovered at the architecture stage costs $1\times$ to fix; in RTL, $10\times$; in physical synthesis, $100\times$; and on physical silicon, $\$10,000+$ and months of shuttle turnaround.

Because this project is both a **silicon tapeout** and an **educational masterclass**, Pillar 1 encompasses **6 core technical and pedagogical dimensions**:

```
[PyTorch / High-Level Algorithm]
              │
              ▼
[Pillar 1: System & Mathematical Modeling (Gate 0)]
   • SNG LFSR Architecture & Decorrelation Modeling
   • Tri-Mode PE Multiplier Logic (Unipolar, Bipolar, Hybrid ReLU)
   • 4:2 Compressor Tree & 12-Bit Accumulator Dynamic Sizing
   • Statistical Convergence, Noise Analysis & Quantization (1/√N)
   • Golden Model Simulator (`model/sim_scim.py`)
   • Test Vector Generator (`model/test_vectors_gate0.json`)
   • EDA Log Hygiene Parsers (`scripts/parse_yosys_stat.py`, `scripts/parse_openlane_reports.py`)
              │
              ▼
[Downstream: Pillar 2 Parameterized RTL & Pillar 3 Cocotb Verification]
```

---

## 2. Stochastic Number Generation (SNG) & Silicon Decorrelation

```
  Fixed-Point Input X ∈ [0, 255]
             │ (8-bit)
             ▼
        ┌─────────┐
        │    >    ├────────► Stochastic Bitstream S[t] ∈ {0, 1}
        └────┬────┘          P(S[t] = 1) = X / 256
             ▲
             │ (8-bit)
        ┌────┴────┐
        │  LFSR   │ ◄─────── Clock & Seed
        └─────────┘
```

### The Silicon Concept
In conventional digital accelerators, an $8\text{-bit} \times 8\text{-bit}$ multiplier requires $\sim 280\text{–}400$ standard cells (adders and partial-product gates). In Stochastic Computing, a real-valued probability $p \in [0, 1]$ is encoded as the density of $1\text{s}$ in a Bernoulli bitstream of length $N$:
$$P(S = 1) = \frac{1}{N} \sum_{k=1}^N S[k]$$

An SNG consists of:
1. **A Pseudo-Random Number Generator (PRNG):** Synthesized as a Linear Feedback Shift Register (**LFSR**).
2. **A Digital Comparator:** Comparing an 8-bit input value $X$ against the LFSR state. If $X > \text{LFSR}$, output `1`; else `0`.

### The Silicon Trap: Cross-Correlation ($r_{AB}$)
If two inputs $A$ and $B$ share the same LFSR or correlated seeds, their bitstreams will be correlated:
$$\mathbb{E}[S_A \cdot S_B] = P(A \cap B) \ne P(A) \cdot P(B)$$
On silicon, this correlation produces massive deterministic calculation errors that no amount of averaging can fix.

### Implementation Aspects in Pillar 1:
* Mathematical models of **Galois vs. Fibonacci LFSRs** using primitive irreducible polynomials (e.g., $x^8 + x^6 + x^5 + x^4 + 1$).
* **Decorrelation techniques:** Seed displacement, polynomial tap swapping, and circular bit-shuffling.
* Automated Pearson correlation metric $r(S_A, S_B)$ checks ensuring $|r| < 0.05$ across all 16 parallel channels.

---

## 3. Tri-Mode Processing Element (PE) Arithmetic

We mathematically model and verify three distinct arithmetic representations:

```
[Mode 0: Unipolar AND]       [Mode 1: Bipolar XNOR]       [Mode 2: Hybrid ReLU (Ours)]
   a ──┐                        a ──┐                        a (Unipolar [0,1]) ─┐
       ├─► AND ──► s_y              ├─► XNOR ──► s_y                             ├──► Ternary Step
   w ──┘                        w ──┘                        w (Bipolar [-1,+1]) ┘    {+1, 0, -1}
   P_y = a · w                  y = (2P_y - 1) = a · w       Zero toggling when a = 0
```

| Metric | Mode 0: Unipolar | Mode 1: Bipolar | Mode 2: Hybrid ReLU (CIMTinyTO) |
|---|---|---|---|
| **Domain** | Inputs $\in [0, 1]$, Weights $\in [0, 1]$ | Inputs $\in [-1, +1]$, Weights $\in [-1, +1]$ | Inputs $\in [0, 1]$ (ReLU), Weights $\in [-1, +1]$ |
| **Silicon Gate** | Single **AND** (6 transistors) | Single **XNOR** (8–10 transistors) | **Tri-State Up/Down/Hold** step logic |
| **Probability Mapping** | $p = X$ | $p = \frac{X + 1}{2}$ | Activation: $P_a = a$; Weight: $w \in \{-1, +1\}$ |
| **Idle Switching Power** | Zero ($a=0 \implies s_a=0$, zero toggling) | **High:** $0.0$ is encoded as $P=0.5$ (50% clock toggling!) | **Zero:** If $a=0$, accumulator holds (no switching) |
| **Neural Net Suitability** | Poor (Cannot do negative weights) | Moderate (Inefficient for ReLU layers) | **Optimal** (Matches standard deep learning activations) |

### Silicon Reality: Dynamic Power $P_{\text{dyn}} = \alpha \cdot C_L \cdot V_{DD}^2 \cdot f$
In standard bipolar stochastic computing, encoding zero requires a $50\%$ probability bitstream, meaning half of the clock cycles cause gate output transitions ($\alpha = 0.5$). For neural networks with sparse ReLU activations (where $50\%\text{–}70\%$ of activations are zero), bipolar computing wastes huge amounts of dynamic power. 
Our **Hybrid ReLU Mode** solves this at the mathematical level: when $a_i = 0$, the PE emits an accumulator `HOLD` command, freezing the downstream adder flip-flops and reducing dynamic power by $>60\%$.

---

## 4. Spatial & Temporal Accumulation: 12-Bit Sizing & 4:2 Compressor Trees

In a $16 \times 16$ SCIM core:
* **Spatial Dimension:** In every clock cycle, 16 PEs in a column emit bits simultaneously.
* **Temporal Dimension:** Computation runs for $N = 256$ clock cycles.

```
Cycle 1..256:
 Column j (16 PEs) ──► [4:2 Compressor Tree] ──► 5-bit Column Sum [0..16]
                                                        │
                                                        ▼
                                            [12-bit Accumulator Register]
                                            (Final result after 256 cycles)
```

### Mathematical Bit-Growth Sizing
To prevent overflow without saturating or dropping bits:
$$\text{Max Accumulator Value} = \text{Rows} \times N = 16 \times 256 = 4096 = 2^{12}$$
$$\text{Bit Width } W_{\text{acc}} = \lceil \log_2(16 \times 256) \rceil = 12\text{ bits}$$

### The Silicon Alternative: Wallace Tree (4:2 Compressor) vs. Ripple Adder
* **Ripple-Carry Adder:** Propagating carries through 16 bits takes $\mathcal{O}(M)$ delay ($\approx 16 \times t_{\text{carry}}$), causing severe glitching and limiting clock speed to $<25\text{ MHz}$.
* **4:2 Compressor Tree:** Compresses 4 inputs down to 2 outputs with only 3 XOR gate delays. Slices the spatial addition of 16 rows into a 4-level tree with critical path $< 2.5\text{ ns}$ ($>100\text{ MHz}$ capability in Sky130).

---

## 5. Statistical Convergence, Precision & Quantization Analysis

Stochastic computation is inherently probabilistic. In Pillar 1, we characterize the fundamental error bounds:

$$\sigma_{\text{stochastic}} = \sqrt{\frac{p(1-p)}{N}}$$

```
Accuracy vs. Bitstream Length N:
  N = 16 cycles   ──► ~4-bit equivalent precision (High speed, coarse inference)
  N = 64 cycles   ──► ~6-bit equivalent precision
  N = 256 cycles  ──► ~8-bit equivalent precision (Our baseline: 12.48 µs at 25 MHz)
  N = 1024 cycles ──► ~10-bit equivalent precision
```

### Implementation Aspects in Pillar 1:
* **Monte Carlo Engine:** Sweeping $N \in \{16, 64, 256, 1024\}$ across $10,000+$ trials.
* **Empirical vs. Theoretical Bounds:** Verifying that standard error follows $\frac{1}{\sqrt{N}}$ and matches Gaussian $\pm 3\sigma$ bounds.
* **Signal-to-Noise Ratio (SNR) & PSNR Curves:** Quantifying dynamic range degradation.

---

## 6. Gate 0 Golden Model & Test Vector Generation (`model/sim_scim.py`)

The Python model serves as the **single source of truth** across the entire project life cycle:

```
[sim_scim.py] ──► Generates `test_vectors_gate0.json`
                         │
                         ├──► Cocotb Pre-Silicon Verification (Pillar 3)
                         ├──► Gate-Level Simulation with Timing (Pillar 6)
                         └──► PYNQ-Z2 / RP2040 Silicon Bring-Up (Pillar 7)
```

### Verified Vector Classes:
1. **Deterministic Edge Cases:**
   - Zero matrix $\times$ Zero vector.
   - Identity matrix $\times$ Max activation vector.
   - Alternating checkerboard patterns (`0xAA55`).
   - Saturation extremes (all $+1$ or all $-1$).
2. **Quantized Neural Network Layers:**
   - Real quantized weights from a Micro-ResNet layer.
   - ReLU-sparse activation vectors (testing the zero-suppression power-saving mode).

---

## 7. EDA Log Hygiene Parsers (`scripts/`)

Modern silicon flows generate massive text logs (OpenROAD and Yosys runs produce $10,000+$ lines per run). To maintain strict project discipline and fast AI inspection, Pillar 1 implements automated log parsers:

### 1. `scripts/parse_yosys_stat.py`
* Audits standard-cell mapping (`sky130_fd_sc_hd`).
* **Registers & Clock Gating:** Confirms all 256 weight DFFs exist and flags if Yosys pruned undriven registers.
* **Inferred Latch Detector:** Scans for unintentional latches caused by incomplete `case` or `if-else` blocks.
* Emits a clean $<30$-line summary table showing sequential vs. combinational cell breakdown and area utilization.

### 2. `scripts/parse_openlane_reports.py`
* **Static Timing Analysis Check:**
  - Setup Slack ($T_{\text{slack, setup}} \ge 0$). *Fixable on the bench by lowering clock frequency.*
  - **Hold Slack ($T_{\text{slack, hold}} \ge 0$).** *FATAL if violated on silicon; cannot be fixed by changing clock speed!*
* **Core Placement Density:** Confirms placement density is near our targeted $\approx 58.8\%$ (below the $65\%$ congestion ceiling).
* **DRC / LVS / Antenna Sign-Off:** Verifies 0 Magic DRC violations, 0 Netgen LVS mismatches, and 0 antenna violations.

---

## 8. Directory Structure of Pillar 1 Deliverables

```plaintext
CIMTinyTO/
├── docs/
│   └── pillar1_system_and_mathematical_modeling.md  <- Complete specification & pedagogical guide
├── scripts/
│   ├── parse_yosys_stat.py                          <- Yosys synthesis & netlist cell hygiene parser
│   └── parse_openlane_reports.py                    <- OpenLane/OpenSTA timing & physical sign-off parser
├── model/
│   ├── sim_scim.py                                  <- Complete Gate 0 Python Golden Model
│   └── test_vectors_gate0.json                      <- Golden stimulus/expected response vectors
├── PROGRESS.md                                      <- Updated living status
└── HANDOFF.md                                       <- Session handoff between PC and Laptop
```
