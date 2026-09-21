---
name: pillar-session-isolation
description: >-
  Enforces strict single-pillar isolation per chat session across the CIMTinyTO tapeout lifecycle.
  Use when planning, implementing, or transitioning between ASIC design pillars.
---

# Pillar Session Isolation Protocol

This skill enforces strict microarchitectural, verification, and physical design focus by isolating each of the 7 ASIC Tapeout Pillars into its own independent conversation/chat session.

## Core Rule: One Pillar Per Chat Session

> [!IMPORTANT]
> **Strict Isolation Directive:**
> A single chat session MUST be dedicated to exactly **ONE** Pillar.
> Implementing or transitioning to more than one Pillar in the same chat session is strictly prohibited.

### The 7 Tapeout Pillars

1. **Pillar 1: System & Mathematical Modeling (Gate 0)**
   - Algorithm-to-silicon quantization, Python reference model (`sim_scim.py`), correlation metrics, SNR.
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

## Workflow & Termination Procedure

Whenever an agent nears completion of the active Pillar:

1. **Verification Sign-Off:**
   - Execute all verification targets relevant to the Pillar (e.g., `make -C test test_all`, `verilator --lint-only -Wall`, OpenLane DRC/LVS).
   - Ensure 0 errors, 0 warnings, and 100% test coverage pass.

2. **State Synchronization:**
   - Update `PROGRESS.md` with:
     - All files built/modified.
     - Architectural decisions and physical trade-offs.
     - Current pipeline state marking the Pillar as 100% complete and frozen.
     - Next steps outlining the deliverables for the subsequent Pillar.
   - Update `HANDOFF.md` with machine session info, active branch, and sync status.

3. **Git Commit & Push:**
   - Follow Conventional Commits format (e.g., `feat(scim): complete and freeze Pillar 2 RTL and verification`).
   - Push all changes to `origin/main`.

4. **Chat Session Handoff:**
   - Summarize the accomplishments and pedagogical lessons of the completed Pillar.
   - **Do NOT begin implementation of the next Pillar.**
   - Prompt the user:
     > "Pillar [N] is 100% complete, verified, and frozen. Per our project skills and rules, please open a fresh chat session to begin Pillar [N+1] ([Pillar Title])."
