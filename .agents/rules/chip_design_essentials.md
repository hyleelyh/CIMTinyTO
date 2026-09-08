# Rule: Chip Design Essentials & Pedagogical Explanations

## Purpose
Enforce continuous, deep, pedagogical explanations throughout all stages of the CIMTinyTO chip design implementation to ensure the engineer masters the complete end-to-end ASIC design lifecycle.

---

## 1. Pedagogical Directives for Every Implementation Step

Whenever writing code, configuring tools, or executing flow stages, the agent MUST explicitly explain:

### A. The "Why" and Underlying Silicon Realities
* Connect Verilog constructs and architectural choices to physical IC consequences:
  - Transistor-level implementations (PMOS/NMOS counts, drive strength, cell area).
  - Dynamic power dissipation ($P_{\text{dyn}} = \alpha \cdot C_L \cdot V_{DD}^2 \cdot f$) and static leakage.
  - Setup time ($T_{\text{setup}}$), hold time ($T_{\text{hold}}$), clock-to-Q ($T_{cq}$), and clock skew.
  - Metastability, asynchronous inputs, and multi-flop synchronization.
  - Physical layout phenomena: wire resistance/capacitance ($RC$ delay), electromigration, IR drop, antenna rules.

### B. Architectural Trade-Off Analysis
* Contrast the selected design against conventional alternatives:
  - Wallace tree compressor vs. ripple-carry adder (area vs. delay $\mathcal{O}(\log N)$ vs. $\mathcal{O}(N)$).
  - Standard-cell DFFs vs. custom 6T SRAM vs. D-Latches.
  - Integrated Clock Gating (ICG) vs. free-running clock with multiplexer recirculate.
  - Unipolar (AND) vs. Bipolar (XNOR) vs. Hybrid (Tri-state up/down) arithmetic.

### C. Silicon Guardrails & Failure Prevention
* Explain why certain software-valid constructs are lethal in silicon:
  - Why inferred latches cause timing closure nightmares and race conditions.
  - Why internal tri-state buses cause floating-gate leakage or bus contention.
  - Why ripple clocks / gated clocks cause uncontrollable clock jitter and hold violations.

---

## 2. Chip Design Curriculum Flow

We will structure our explanations around the 7 core pillars of the ASIC tapeout lifecycle:

1. **Pillar 1: System & Mathematical Modeling (Gate 0)**
   - Algorithm-to-silicon quantization, stochastic bitstream correlation, statistical Signal-to-Noise Ratio (SNR).
2. **Pillar 2: Microarchitecture & Register-Transfer Level (RTL)**
   - Datapath vs. control FSM, pipelining, weight-stationary dataflow, clock gating.
3. **Pillar 3: Verification & Design for Testability (DFT)**
   - Cocotb Python-driven simulation, golden vector matching, scan chains, loopback testability.
4. **Pillar 4: Logic Synthesis & Technology Mapping (Gate 2)**
   - RTL to G-tech netlist, cell library mapping (`sky130_fd_sc_hd`), cell budget enforcement.
5. **Pillar 5: Static Timing Analysis (STA)**
   - Constraining clocks, arrival times, setup/hold slack, multicycle paths, clock tree synthesis (CTS).
6. **Pillar 6: Physical Design & Sign-Off (PnR, DRC, LVS)**
   - Floorplanning, power rings, macro placement, detailed routing, DRC/LVS physical verification.
7. **Pillar 7: Silicon Bring-Up & Board-Level Characterization**
   - MicroPython carrier firmware, FPGA PMOD high-speed stimulus, live classification demo.
