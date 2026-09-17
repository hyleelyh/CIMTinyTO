# Microarchitecture: Unified Column Delta Reduction & Mode Arithmetic

## 1. Silicon Problem: The Physical Reality of CMOS Digital Wires

In algorithmic modeling (Pillar 1 / Gate 0 in Python), software effortlessly manipulates signed and ternary states:
```python
# Mode 2: Hybrid ReLU in sim_scim.py
if a_bit == 0:
    step = 0        # HOLD
else:
    step = +1 if w_val > 0 else -1
```
Python sums these steps across all 16 rows using `int(np.sum(pe_steps))` without considering the physical electrical medium.

In physical CMOS standard-cell silicon (Pillar 2 / Gate 1 in Verilog), however:
* **Digital wires only carry two electrical states:** $V_{DD}$ (logic `1`) and $GND$ (logic `0`).
* There is no intermediate "$-1\text{ V}$" digital logic voltage.
* Standard Wallace tree compressors constructed with 4:2 compressors and full adders only compress **positive single-bit** inputs ($\{0, 1\}$).

---

## 2. The Silicon Trap: Dual Compressor Trees vs. Unified Reduction

To represent the ternary step $\{-1, 0, +1\}$ on silicon, a conventional digital designer might use **two separate wires per PE**:
1. `pe_pos`: pulsed high when the PE contributes $+1$.
2. `pe_neg`: pulsed high when the PE contributes $-1$.

### Why Dual Trees Fail the Tiny Tapeout Budget:
* Each column would require **two 16-input Wallace trees** (one for positive bits, one for negative bits).
* Across 16 columns: $16 \times 2 = \mathbf{32\text{ Wallace trees}}$.
* 32 trees consume $\approx 1,824$ standard cells.
* Combined with 256 weight DFFs, 16 accumulators, and SNGs, the core would exceed **$>3,200$ cells**, far exceeding the **$1\times 2$ Tiny Tapeout macro budget (~1,600–2,000 cells)** and causing severe routing congestion.

---

## 3. Mathematical Derivation of Mode 2 (Hybrid ReLU): $\Delta_{\text{col}} = 2P_{\text{col}} - A$

Let:
* $a_i \in \{0, 1\}$: Stochastic activation bit from SNG channel $i$.
* $w_{ij} \in \{0, 1\}$: Weight bit in row $i$, column $j$ ($1 \implies +1$, $0 \implies -1$).

### Truth Table Analysis:

| $a_i$ | $w_{ij}$ | Target Step $\text{step}_i$ | Boolean Term $a_i \land w_{ij}$ |
|:---:|:---:|:---:|:---:|
| `0` | `0` | **`0`** ($a=0 \implies$ HOLD) | `0` |
| `0` | `1` | **`0`** ($a=0 \implies$ HOLD) | `0` |
| `1` | `0` | **`-1`** ($a=1$, weight is $-1$) | `0` |
| `1` | `1` | **`+1`** ($a=1$, weight is $+1$) | `1` |

### Algebraic Factorization:
When $a_i = 1$, the step is $+1$ if $w_{ij} = 1$ and $-1$ if $w_{ij} = 0$:
$$\text{step}_i = a_i \cdot (2w_{ij} - 1)$$

Distributing $a_i$:
$$\text{step}_i = 2(a_i \cdot w_{ij}) - a_i$$

Since $a_i, w_{ij} \in \{0, 1\}$, scalar multiplication is equivalent to the Boolean bitwise AND ($\land$):
$$\mathbf{\text{step}_i = 2(a_i \land w_{ij}) - a_i}$$

### Column Summation:
Summing across all 16 rows ($i = 0, \dots, 15$) in column $j$:
$$\Delta_{\text{col}} = \sum_{i=0}^{15} \text{step}_i = \sum_{i=0}^{15} \Big( 2(a_i \land w_{ij}) - a_i \Big)$$

Using summation distributivity:
$$\Delta_{\text{col}} = 2 \underbrace{\left( \sum_{i=0}^{15} (a_i \land w_{ij}) \right)}_{P_{\text{col}}} - \underbrace{\left( \sum_{i=0}^{15} a_i \right)}_{A}$$

$$\mathbf{\Delta_{\text{col}} = 2 \cdot P_{\text{col}} - A}$$

### The Shared Activation Reduction Insight ($A$):
* $P_{\text{col}} = \sum_{i=0}^{15} (a_i \land w_{ij})$ is a sum of 16 single bits, computed by a standard unsigned 16-to-5 Wallace tree ($P_{\text{col}} \in [0, 16]$).
* Notice that **$A = \sum_{i=0}^{15} a_i$ contains no weight index $j$**.
* The 16 activation streams $a[15:0]$ are broadcast to all columns.
* Therefore, **$A$ is identical for all 16 columns** in any given clock cycle!
* A single 16-to-5 Wallace tree computes $A$ once for the entire chip and broadcasts it to all column subtractors, **saving 15 entire Wallace trees (~855 standard cells)**.

```
                    a[15:0] (16 stochastic activation bits)
                                      │
              ┌───────────────────────┴───────────────────────┐
              │                                               ▼
              │                                    ┌─────────────────────┐
              │                                    │  Shared Tree (1x)   │ ──► A (5-bit)
              │                                    └──────────┬──────────┘
              ▼                                               │ (Broadcast)
   ┌──────────────────────┐                                   │
   │  Col 0 PE Array      │ ──► 16-to-5 Wallace Tree ──► P_0 ─┤──► Δ_0 = 2·P_0 - A
   └──────────────────────┘                                   │
   ┌──────────────────────┐                                   │
   │  Col 1 PE Array      │ ──► 16-to-5 Wallace Tree ──► P_1 ─┤──► Δ_1 = 2·P_1 - A
   └──────────────────────┘                                   │
             ...                                              │
   ┌──────────────────────┐                                   │
   │  Col 15 PE Array     │ ──► 16-to-5 Wallace Tree ──► P_15 ┴──► Δ_15 = 2·P_15 - A
   └──────────────────────┘
```

---

## 4. Mathematical Derivation of Mode 1 (Bipolar XNOR): $\Delta = 2X - 16$

In **Bipolar Stochastic Computing (Mode 1)**, real continuous values in $[-1, +1]$ map to probability $P = (y + 1)/2$.
Multiplication of two signs is implemented by a single **XNOR gate**:
$$x_i = \text{XNOR}(a_i, w_{ij})$$

* If $x_i = 1$: PE wants to add $+1$.
* If $x_i = 0$: PE wants to add $-1$.

$$\text{step}_i = 2x_i - 1$$

Summing across all 16 rows:
$$\Delta_{\text{col}} = \sum_{i=0}^{15} (2x_i - 1) = 2 \left( \sum_{i=0}^{15} x_i \right) - \sum_{i=0}^{15} 1 = \mathbf{2X - 16}$$

Where:
* $X = \sum_{i=0}^{15} x_i$ is the unsigned count of PEs with $x_i = 1$ ($X \in [0, 16]$).
* The 16-to-5 Wallace tree directly computes $X$.
* Multiplying by 2 in binary is a **hardwired 1-bit left shift** (`{X, 1'b0}`): **0 gates, 0 delay!**
* Subtracting 16 is a simple 6-bit subtraction: `$signed({1'b0, X, 1'b0}) - 6'sd16`.

---

## 5. Mode Unification Summary Table

Across all three modes, every column uses the **exact same single-bit PE output and unsigned 16-to-5 Wallace tree**:

| Mode | Mathematical Operation | PE Output Wire $p_i$ | Tree Output Range | Final Column Delta $\Delta_{\text{col}}$ |
|---|---|---|---|---|
| **Mode 0: Unipolar** | $a \in [0, 1], w \in \{0, 1\}$ | $a_i \land w_{ij}$ | $P \in [0, 16]$ | $\Delta = P$ |
| **Mode 1: Bipolar** | $a \in [-1, +1], w \in \{-1, +1\}$ | $\text{XNOR}(a_i, w_{ij})$ | $X \in [0, 16]$ | $\Delta = 2X - 16$ |
| **Mode 2: Hybrid ReLU** | $a \in [0, 1], w \in \{-1, +1\}$ | $a_i \land w_{ij}$ | $P \in [0, 16]$ | $\Delta = 2P - A$ |

### Hardware Savings:
* **Wallace Trees Needed:** 17 trees (16 column + 1 shared) vs. 32 trees in naive approach.
* **Cell Count Savings:** $\approx 855$ standard cells saved (~47% area reduction).
* **Timing Critical Path:** Wallace tree ($<1.3\text{ ns}$) + 5-bit subtractor ($\approx 0.2\text{ ns}$) $< 1.5\text{ ns}$ total (huge timing margin for $50\text{ MHz}$ / $20\text{ ns}$).
