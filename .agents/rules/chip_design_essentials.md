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
 
We structure our implementations and explanations around the 7 core pillars of the ASIC tapeout lifecycle:

1. **Pillar 1: System & Mathematical Modeling (Gate 0)**
   - Algorithm-to-silicon quantization, Python reference model (`sim_scim.py`), correlation metrics, statistical SNR.
2. **Pillar 2: Microarchitecture, RTL & Verification (Gate 1)**
   - Parameterized Verilog core (`tt_um_scim_core.v`), PEs, Wallace tree compressor, Cocotb testbenches, defensive silicon hardening (Holes #1–#11).
3. **Pillar 3: Physical ASIC Flow (OpenLane 2 / OpenROAD)**
   - Macro configuration (`config.yaml`), logic synthesis, high-fanout buffering, floorplanning, placement, clock tree synthesis (CTS), detailed routing, DRC/LVS physical sign-off.
4. **Pillar 4: Static Timing Analysis & Sign-Off (STA)**
   - SDC timing constraints, arrival times, setup/hold slack closure across PVT corners, multicycle paths, clock skew analysis.
5. **Pillar 5: Gate-Level Simulation (GLS) & Power Analysis**
   - Post-synthesis and post-route netlist simulation, SDF back-annotation, VCD-driven dynamic switching power estimation.
6. **Pillar 6: Pre-Silicon Emulation (FPGA Testbench)**
   - High-speed 50–100 MHz validation on PYNQ-Z2 (Xilinx Zynq-7020) and DE10-Lite (Intel MAX 10), MMIO AXI driver, hardware-in-the-loop testing.
7. **Pillar 7: Post-Silicon Bring-Up & Board Characterization**
   - Tiny Tapeout RP2040/RP2350 carrier board bring-up, lab oscilloscope characterization, end-to-end Micro-ResNet inference demonstration.

---

## 3. Strict Single-Pillar Session Scope Rule (CRITICAL)
* **One Pillar Per Chat Session:** To protect context windows and ensure complete verification boundaries, each conversation session MUST focus exclusively on ONE Pillar. Implementing more than one Pillar in the same chat is strictly prohibited.
* **Session Conclusion Protocol:** When the active Pillar is signed off, the agent must update `PROGRESS.md`, update `HANDOFF.md`, commit all files via Git, and explicitly prompt the user to start a fresh chat session for the next Pillar.
