# Wallace Tree & 4:2 Compressor Masterclass

## 1. Executive Summary & Silicon Motivation

In our **$16 \times 16$ SCIM core**, each column contains 16 Processing Elements (PEs). In every clock cycle, all 16 PEs generate a 1-bit multiplication output simultaneously.

To accumulate these bits into our 13-bit accumulator register, we must sum all 16 rows into a 5-bit number ($0 \text{ to } 16$) **within a single clock cycle** ($< 10\text{ ns}$ at $100\text{ MHz}$).

```
Cycle t:
Row 0:  PE[0]  ──► 1-bit ──┐
Row 1:  PE[1]  ──► 1-bit ──┤
Row 2:  PE[2]  ──► 1-bit ──┼──► [Spatial Reduction Logic] ──► 5-bit Delta [-16..+16]
 ...                       │                                       │
Row 15: PE[15] ──► 1-bit ──┘                                       ▼
                                                             [Accumulator DFF]
```

### The Naive Ripple-Carry Adder (The Silicon Trap)
If you cascade 15 standard full adders sequentially in a chain:
* **Linear Delay $\mathcal{O}(M)$:** The carry must ripple through 15 stages. In SkyWater 130nm:
  $$T_{\text{delay}} \approx 15 \times T_{\text{carry}} \approx 15 \times 0.40\text{ ns} = \mathbf{6.0\text{ ns}}$$
* **Massive Dynamic Glitching Power ($P_{\text{glitch}}$):**
  Intermediate nodes toggle up to 10–15 times before settling, wasting **$30\%\text{–}50\%$ of dynamic power**.

---

## 2. What is a 4:2 Compressor?

A **4:2 Compressor** is a specialized slice cell that accepts **5 inputs** and produces **3 outputs**:

```
                 x1    x2    x3    x4
                  │     │     │     │
                  ▼     ▼     ▼     ▼
                ┌─────────────────────┐
Cin (Weight 1) ─►                     ├──► Cout (Weight 2, to next column)
(from right)    │   4:2 Compressor    │
                │                     ├──► Carry (Weight 2)
                └──────────┬──────────┘
                           │
                           ▼
                       Sum (Weight 1)
```

### The Arithmetic Identity
$$x_1 + x_2 + x_3 + x_4 + C_{\text{in}} = \text{Sum} + 2 \cdot (\text{Carry} + C_{\text{out}})$$

* **Primary Inputs ($x_1, x_2, x_3, x_4$):** 4 bits of weight $2^0$ in the current column.
* **Carry-In ($C_{\text{in}}$):** 1 bit of weight $2^0$ from the adjacent less significant column.
* **Sum ($S$):** 1 output bit of weight $2^0$.
* **Carry ($C$):** 1 output bit of weight $2^1$ in the current slice.
* **Carry-Out ($C_{\text{out}}$):** 1 output bit of weight $2^1$ feeding horizontally to the next more significant slice.

### The Magic Silicon Property: Zero Horizontal Carry Propagation
In a properly designed 4:2 compressor:
$$\mathbf{C_{\text{out}} \text{ depends ONLY on } x_1, x_2, x_3, x_4 \quad (\text{Independent of } C_{\text{in}}!)}$$
Because $C_{\text{out}}$ is strictly independent of $C_{\text{in}}$, **there is NO horizontal carry ripple across columns**. All $C_{\text{out}}$ bits across all columns are generated in parallel!

---

## 3. Optimized Boolean Equations & Gate Breakdown

1. **Sum Output (Parity of all 5 inputs):**
   $$\text{Sum} = x_1 \oplus x_2 \oplus x_3 \oplus x_4 \oplus C_{\text{in}}$$
2. **Intermediate Carry-Out ($C_{\text{out}}$):**
   $$C_{\text{out}} = (x_1 \oplus x_2) \cdot x_3 + \overline{(x_1 \oplus x_2)} \cdot x_1$$
3. **Carry Output ($C$):**
   $$\text{Carry} = (x_1 \oplus x_2 \oplus x_3 \oplus x_4) \cdot C_{\text{in}} + \overline{(x_1 \oplus x_2 \oplus x_3 \oplus x_4)} \cdot x_4$$

---

## 4. Building the 16-Input Wallace Tree for CIMTinyTO

By cascading 4:2 compressors in a tree structure, delay scales logarithmically as $\mathcal{O}(\log_2 M)$:

```
Input: 16 PE Bits (Row 0 .. 15)
│
├── Level 1: [Four 4:2 Compressors]
│     16 inputs ──► Reduced to 8 signals (4 Sums, 4 Carries)
│     Delay: ~0.70 ns
│
├── Level 2: [Two 4:2 Compressors]
│     8 inputs ──► Reduced to 4 signals (2 Sums, 2 Carries)
│     Delay: ~0.70 ns
│
├── Level 3: [One 4:2 Compressor]
│     4 inputs ──► Reduced to 2 signals (1 Sum, 1 Carry)
│     Delay: ~0.70 ns
│
└── Level 4: [Final 4-bit Vector Merge Adder]
      Final Sum + Carry ──► 5-bit Column Value [0..16]
      Delay: ~0.40 ns
───────────────────────────────────────────────────────────
Total Critical Path Delay: ~2.50 ns  (Supports >100 MHz in Sky130!)
```

---

## 5. Physical Gate Delay & Liberty Model Derivation (SkyWater 130nm)

In the official SkyWater 130nm standard cell library (`sky130_fd_sc_hd__tt_025C_1v80.lib`), gate delay is characterized using Non-Linear Delay Model (NLDM) lookup tables based on input slew and output capacitance $C_L$:

### Why the Level 4 Adder Takes Only $\approx 0.40\text{ ns}$:
1. **Bit Width is Only 4 Bits:** 16 single-bit inputs sum to a maximum of $16 = 10000_2$ (5 bits). The Level 4 adder only adds two 4-bit vectors ($S[3:0] + (C[3:0] \ll 1)$).
2. **Standard Cell Numbers (`sky130_fd_sc_hd` at TT corner, $1.80\text{V}, 25^\circ\text{C}$):**
   - Full Adder carry propagation (`fa_1` $C_{\text{in}} \to C_{\text{out}}$): **$\sim 0.123\text{ ns}$** ($123\text{ ps}$).
   - Full Adder sum generation (`fa_1` $C_{\text{in}} \to \text{Sum}$): **$\sim 0.122\text{ ns}$** ($122\text{ ps}$).
   - 2-input XOR (`xor2_1`): **$\sim 0.15\text{ ns}$** intrinsic, **$\sim 0.25\text{ ns}$** with routing wire parasitics.
3. **Ripple vs CLA for 4 Bits:**
   - 4-bit CLA: $T_{\text{XOR}} (0.15) + T_{\text{AOI}} (0.12) + T_{\text{Sum}} (0.15) \approx \mathbf{0.42\text{ ns}}$.
   - 4-bit Ripple: $T_{\text{HA}} (0.10) + 2 \times T_{\text{carry}} (0.25) + T_{\text{Sum}} (0.12) \approx \mathbf{0.47\text{ ns}}$.

---

## 6. Synthesizable Verilog Implementation (`src/scim_compressor_42.v`)

```verilog
`default_nettype none

module scim_compressor_42 (
    input  wire x1,
    input  wire x2,
    input  wire x3,
    input  wire x4,
    input  wire cin,
    output wire sum,
    output wire carry,
    output wire cout
);

    // Internal wires
    wire x12;
    wire x1234;

    // First XOR stage
    assign x12   = x1 ^ x2;
    assign x1234 = x12 ^ x3 ^ x4;

    // Sum output: Parity of all 5 inputs
    assign sum = x1234 ^ cin;

    // Cout output: Independent of cin (zero horizontal rippling!)
    assign cout = x12 ? x3 : x1;

    // Carry output: 2:1 MUX controlled by x1234
    assign carry = x1234 ? cin : x4;

endmodule

`default_nettype wire
```
