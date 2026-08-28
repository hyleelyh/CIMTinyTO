# AGENTS.md — Stochastic & Digital CIM (CIMTinyTO) Configuration

## Project Core Goal
Design, verify, synthesize, and validate an open-source standard-cell **Stochastic Compute-in-Memory (SCIM)** and **Digital Compute-in-Memory (DCIM)** accelerator macro targeted for Tiny Tapeout shuttles (SkyWater 130nm / IHP SG13G2).

The system integrates:
1. **Mathematical Golden Model:** Python/NumPy simulation of stochastic number generators (SNGs), unipolar/bipolar multiplication, and accumulator precision.
2. **Standard-Cell RTL & Verification:** Parameterized Verilog core + Cocotb / Icarus Verilog regression testbenches.
3. **Physical ASIC Flow:** OpenLane 2 / OpenROAD push-button synthesis, CTS, placement, routing, and DRC/LVS physical sign-off.
4. **Multi-Tier Hardware Bring-Up:** Tiny Tapeout RP2040/RP2350 carrier board (Level 1) and PYNQ-Z2 FPGA PMOD testbench at $50\text{–}100+\text{ MHz}$ (Level 2).

---

## Operating Rules & Workflow Expectations

### 1. Bi-Directional State Synchronization (CRITICAL)
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

## Workspace Structure
```plaintext
├── AGENTS.md               <- System directive file
├── PROGRESS.md             <- Living state summary updated by Antigravity
├── HANDOFF.md              <- Session handoff between PC and Laptop
├── FeasibilityStudy/       <- Initial feasibility reports & literature
├── docs/                   <- Architectural specs and design notes
├── model/                  <- Python golden reference models (sim_scim.py)
├── src/                    <- Verilog RTL source files (tt_um_*, scim_core, etc.)
├── test/                   <- Cocotb testbenches and verification scripts
└── fpga/                   <- PYNQ-Z2 testbench overlays and Jupyter notebooks
```
