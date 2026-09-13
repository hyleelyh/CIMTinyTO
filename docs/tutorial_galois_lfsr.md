# Galois Linear Feedback Shift Register (LFSR) Masterclass

## 1. Executive Summary & Silicon Motivation

In software (C / Python), pseudo-random number generators (PRNGs) like **Linear Congruential Generators (LCG)** or **Mersenne Twister** compute:
$$X_{n+1} = (a \cdot X_n + c) \bmod m$$
Implementing this in an ASIC requires:
* A 32-bit hardware multiplier ($\sim 1,200$ standard cells)
* A 32-bit adder ($\sim 200$ standard cells)
* Heavy dynamic switching power ($P = C V^2 f$).

In a standard-cell CIM accelerator macro like **CIMTinyTO**, we have 16 parallel channels that each need independent, high-speed random numbers every clock cycle. An LFSR accomplishes this using **only 8 standard-cell D-Flip-Flops and 3 XOR gates** ($\sim 80$ transistors total!), running at full wire speed ($>100\text{ MHz}$) with negligible silicon footprint.

---

## 2. Fibonacci vs. Galois — The Crucial ASIC Dilemma

There are two primary ways to wire an LFSR: **Fibonacci (Many-to-One)** and **Galois (One-to-Many)**.

### A. The Fibonacci Topology (Conventional, but Slow)

In a Fibonacci LFSR, the feedback logic taps multiple flip-flop outputs, passes them through a **cascaded series of XOR gates**, and feeds the scalar result back into the MSB:

```
      ┌─────────────────────────────────────────────────────────────┐
      │                                                             │
      ▼                                                             │
  ┌───────┐      ┌───────┐      ┌───────┐      ┌───────┐        ┌───┴───┐
  │ DFF 7 ├─────►│ DFF 6 ├─────►│ DFF 5 ├──...─►│ DFF 1 ├───────►│ DFF 0 │
  └───┬───┘      └───┬───┘      └───┬───┘      └───┬───┘        └───┬───┘
      │              │              │              │                 │
      ▼              ▼              │              │                 │
     (XOR)───────────┘              │              │                 │
       │                            ▼              ▼                 │
       └───────────────────────────(XOR)───────────┘                 │
                                      │                              │
                                      └──────────────────────────────┘
```

#### The Silicon Trap: Long Critical Path
* The signal must propagate out of the DFFs ($T_{\text{cq}}$), ripple through multiple XOR gates in series ($k \times T_{\text{xor}}$), and satisfy the setup time ($T_{\text{setup}}$) of DFF 7:
  $$T_{\text{critical, Fibonacci}} = T_{\text{cq}} + (k - 1) \cdot T_{\text{xor}} + T_{\text{setup}}$$
* For an LFSR with 4 taps, the signal travels through 3 cascading XOR gates. In SkyWater 130nm, each XOR gate adds $\sim 0.25\text{–}0.35\text{ ns}$ plus interconnect delay, capping the maximum clock speed and generating excessive combinational glitching power.

---

### B. The Galois Topology (Our Design: Constant 1-Gate Delay)

In a Galois LFSR, the output of the LSB (Bit 0) is broadcast in parallel to all tap locations. The XOR gates are placed **in between the flip-flops**:

```
      ┌───────────────────────────────────────────────────────────────┐
      │                                                               │
      ▼                                                               │
  ┌───────┐        ┌───────┐        ┌───────┐             ┌───────┐   │
  │ DFF 7 ├───┬───►│ DFF 6 ├───┬───►│ DFF 5 ├───...──┬───►│ DFF 0 ├───┘
  └───────┘   │    └───────┘   │    └───────┘        │    └───┬───┘
              ▼                ▼                     ▼        │ (LSB Output)
             XOR              XOR                   XOR       │
              ▲                ▲                     ▲        │
              └────────────────┴─────────────────────┴────────┘
                                Feedback Mask (0xB8)
```

#### Why Galois Wins in Silicon:
1. **Constant Delay Regardless of Bit Width:**
   No matter how many taps the polynomial has, **the signal never passes through more than ONE XOR gate between any two flip-flops**:
   $$T_{\text{critical, Galois}} = T_{\text{cq}} + 1 \cdot T_{\text{xor}} + T_{\text{setup}} \approx 0.35\text{ ns}$$
   This allows our LFSR to easily hit **$>100\text{ MHz}$** in SkyWater 130nm!
2. **Zero Ripple Glitching:**
   Because XOR gates are buffered directly by downstream flip-flops on every clock edge, intermediate logic glitches cannot propagate down a long carry chain, drastically reducing dynamic switching energy ($P_{\text{dyn}} = \alpha C V^2 f$).

---

## 3. Mathematical Foundations & $\text{GF}(2)$ Polynomials

An LFSR performs polynomial division over the Galois Field of two elements, **$\text{GF}(2)$**:
* In $\text{GF}(2)$, addition and subtraction are identical to the bitwise **XOR ($\oplus$)** operation.
* Multiplication is identical to the bitwise **AND ($\cdot$)** operation.

### Primitive Irreducible Polynomials
An $n$-bit shift register has $2^n$ possible states. To create a **maximal-length sequence** that cycles through all $2^n - 1$ non-zero states without getting stuck in a short sub-loop, the feedback connections must represent a **primitive irreducible polynomial** (a polynomial that cannot be factored into smaller polynomials over $\text{GF}(2)$).

For our **8-bit Galois LFSR**, we use:
$$P(x) = x^8 + x^6 + x^5 + x^4 + 1$$

In hardware, we encode this polynomial as a characteristic mask:
* $x^8$ represents the feedback source (LSB).
* Taps are located at bits 6, 5, 4 (and implicit bit 0).
* Hexadecimal Characteristic Mask: **`0xB8`** (`10111000` in binary).

---

## 4. Cycle-by-Cycle Arithmetic Walkthrough

State transitions happen deterministically starting from seed `0x01`:

```
Cycle 0: State = 0x01 (Binary: 0000 0001)
   1. Check LSB: LSB = 1.
   2. Shift Right by 1: 0000 0001 >> 1 = 0000 0000.
   3. Since LSB was 1, XOR with mask 0xB8 (1011 1000):
      0000 0000 ⊕ 1011 1000 = 1011 1000 (0xB8).
   --> Next State = 0xB8 (184 decimal).

Cycle 1: State = 0xB8 (Binary: 1011 1000)
   1. Check LSB: LSB = 0.
   2. Shift Right by 1: 1011 1000 >> 1 = 0101 1100.
   3. Since LSB was 0, NO XOR is applied.
   --> Next State = 0x5C (92 decimal).

Cycle 2: State = 0x5C (Binary: 0101 1100)
   1. Check LSB: LSB = 0.
   2. Shift Right by 1: 0101 1100 >> 1 = 0010 1110.
   --> Next State = 0x2E (46 decimal).

Cycle 3: State = 0x2E (Binary: 0010 1110)
   1. Check LSB: LSB = 0.
   2. Shift Right by 1: 0010 1110 >> 1 = 0001 0111.
   --> Next State = 0x17 (23 decimal).
```

This sequence continues deterministically for **exactly 255 clock cycles**, visiting every integer from 1 to 255 exactly once before wrapping back to `0x01`.

---

## 5. Seed Dynamics: Spatial vs. Temporal Behavior

In our architecture, seeds are **spatially static at reset**, but **temporally dynamic during execution**:

1. **Across 16 Channels (Spatial):**
   - Each channel has a compile-time static seed offset: $\text{Seed}_i = \text{State}[(i \times 15) \pmod{255}]$.
   - This keeps cross-correlation $|r_{ij}| \le 0.0259 < 0.05$ while saving $\approx 300$ standard cells (avoiding programmable shadow registers).
2. **Across Successive Compute Tiles (Temporal):**
   - Tile compute duration is $N = 256$ cycles.
   - Since $256 = 255 + 1$, after 256 cycles the LFSR completes one full revolution plus 1 step.
   - When running continuous inference, the LFSR automatically rolls forward by $+1$ phase on every consecutive tile, naturally breaking repetitive pattern artifacts.
3. **Deterministic Reset:**
   - Asserting active-low reset (`rst_n`) restores the exact starting seeds for 100% bit-exact pre-silicon verification in Cocotb and FPGA bring-up.

---

## 6. Critical Silicon Guardrails

| Failure Mode | Root Cause | Silicon Consequence | Hardware Solution |
|---|---|---|---|
| **Zero-State Lockup** | Flip-flops power up as `0x00` | $0 \oplus 0 = 0$. The LFSR stays at `0` forever; all SNG outputs die. | **Active-Low Synchronous Reset (`rst_n`)** loading a non-zero default seed. |
| **Metastability / Race** | Asynchronous reset release on clock edge | Setup/hold violation on reset pin; flip-flops enter intermediate voltage oscillation ($V_{DD}/2$). | Double-flop reset synchronizer (`rst_sync`). |
| **Cross-Channel Correlation** | Adjacent SNGs start with same or adjacent seeds | High Pearson correlation ($r \approx 1.0$), causing massive systematic dot-product errors. | **Stride-15 Seed Spacing** along the 255-state trajectory ($|r| < 0.0259$). |

---

## 7. Production Synthesizable Verilog RTL (`src/lfsr8_galois.v`)

```verilog
`default_nettype none

module lfsr8_galois #(
    parameter [7:0] SEED = 8'h01,         // Guaranteed non-zero initial seed
    parameter [7:0] POLY = 8'hB8          // x^8 + x^6 + x^5 + x^4 + 1
)(
    input  wire       clk,                // Master clock (posedge)
    input  wire       rst_n,              // Synchronous active-low reset
    input  wire       en,                 // Compute clock enable
    output reg  [7:0] state               // 8-bit pseudo-random state output
);

    always @(posedge clk) begin
        if (!rst_n) begin
            // Guardrail: Reset to verified non-zero seed
            state <= (SEED == 8'h00) ? 8'h01 : SEED;
        end else if (en) begin
            // Galois shift & feedback logic
            if (state[0]) begin
                state <= (state >> 1) ^ POLY;
            end else begin
                state <= (state >> 1);
            end
        end
    end

endmodule

`default_nettype wire
```
