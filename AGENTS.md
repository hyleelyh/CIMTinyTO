# AGENTS.md — Stochastic & Digital CIM (CIMTinyTO) Configuration

## Project Core Goal
Design, verify, synthesize, and validate an open-source standard-cell **Stochastic Compute-in-Memory (SCIM)** and **Digital Compute-in-Memory (DCIM)** accelerator macro targeted for Tiny Tapeout shuttles (SkyWater 130nm / IHP SG13G2).

The system integrates:
1. **Mathematical Golden Model:** Python/NumPy simulation of stochastic number generators (SNGs), unipolar/bipolar/hybrid multiplication, and 12-bit accumulator precision.
2. **Standard-Cell RTL & Verification:** Parameterized Verilog core + Cocotb / Icarus Verilog regression testbenches.
3. **Physical ASIC Flow:** OpenLane 2 / OpenROAD push-button synthesis, CTS, placement, routing, and DRC/LVS physical sign-off.
4. **Multi-Tier Hardware Bring-Up:** Tiny Tapeout RP2040/RP2350 carrier board (Level 1) and PYNQ-Z2 FPGA PMOD testbench at $50\text{–}100+\text{ MHz}$ (Level 2) running an end-to-end Micro-ResNet inference demonstration.

---

## Operating Rules & Workflow Expectations

### 1. Pedagogical Chip Design Directive (CRITICAL LEARNING GOAL)
The primary user goal is to **learn every essential perspective of ASIC/chip design**. Every step of the implementation MUST be accompanied by clear, in-depth educational explanations:
* **The "Why" & Silicon Realities:** For every module or circuit choice, explain the underlying IC fundamentals (e.g., dynamic switching power $P = C V^2 f$, clock skew, setup/hold timing margin, metastability, transistor counts, routing track congestion).
* **Trade-Off Analysis:** Contrast the chosen approach against industry alternatives (e.g., Wallace tree compressor vs. ripple adder, standard-cell DFF vs. 6T SRAM, edge-triggered flip-flop vs. level-sensitive latch).
* **Traps & Guardrails:** Highlight common failure modes that pass functional simulation but fail on physical silicon (unintended latches, race conditions, floating buses, hold-time violations across PVT corners).
* **Clear Conceptual Visuals:** Use text/ASCII diagrams and mathematical formulations so microarchitectural concepts are visually and intuitively understood before diving into raw Verilog or Python code.

### 2. Bi-Directional State Synchronization (CRITICAL)
Whenever an agent executes a workflow, implements code, or modifies architecture, it MUST execute the following sync steps prior to job termination:

* **Update `PROGRESS.md`** at the project root with the following structure:
  ```markdown
  ## Last Execution Run: [YYYY-MM-DD HH:MM]
  ### [Built]
  - List of created or modified files.
  
  ### [Architecture Decisions]
  - Technical rationale, mathematical formulations, or design trade-offs.
  
  ### [Current Pipeline State]
  - What is functional vs. what requires testing or further implementation.
  
  ### [Next Steps]
  - Immediate logical deliverables for the next run.
  ```

* **Update `HANDOFF.md`** with machine session info, active branch, and sync status for seamless PC $\leftrightarrow$ Laptop switching.

* **Git Commit Standard:** Produce concise, descriptive commit messages following Conventional Commits (e.g., `feat(scim): implement parameterized XNOR PE array`, `test(cocotb): add bipolar SNG regression suite`).

---

## Code Standards & Tech Stack
* **Languages:** Verilog (IEEE 1364-2001 / 2005), Python 3.11+, Cocotb
* **Target EDA Tools:** Icarus Verilog (`iverilog`), GTKWave / Surfer, Verilator (lint), Yosys, OpenLane 2 / OpenROAD, Magic, Netgen, KLayout
* **Target Platforms:** Tiny Tapeout (Sky130 / IHP SG13G2), RP2040 / RP2350 Carrier Board, PYNQ-Z2 FPGA (Xilinx Zynq-7020)

---

## Hardware Guardrails & Silicon Rules
1. **Immutability of Top-Level Wrapper:** `src/tt_um_*.v` port names and bit widths must never be modified. All custom core logic lives inside modular submodules under `src/`.
2. **Strict Synchronous Discipline:** All flip-flops clocked on `posedge clk` with synchronous active-low reset (`rst_n`). No internal clock gating logic without glitch-free integrated clock gating (ICG) cells. No internal clock dividers.
3. **No Unintended Latches:** Fully specify all `if-else` branches and `case` default statements in combinatorial `always @(*)` blocks.
4. **No Internal Tri-States:** Tri-state drivers (`z`) are forbidden in internal logic and only permitted on external bidirectional I/O pads (`uio_oe`).
5. **EDA Log Hygiene:** Filter raw EDA logs through compact parser scripts under `scripts/` to keep outputs under 40 lines.

---

## Workspace Structure
```plaintext
├── AGENTS.md               <- System directive & pedagogical guidelines
├── PROGRESS.md             <- Living state summary updated by Antigravity
├── HANDOFF.md              <- Session handoff between PC and Laptop
├── FeasibilityStudy/       <- Initial feasibility reports & literature
├── docs/                   <- Architectural specs and design notes
├── model/                  <- Python golden reference models (sim_scim.py)
├── src/                    <- Verilog RTL source files (scim_pe_array, accumulators, etc.)
├── test/                   <- Cocotb testbenches and verification scripts
├── scripts/                <- EDA output parsers for log hygiene
└── fpga/                   <- PYNQ-Z2 testbench overlays and Jupyter notebooks
```
