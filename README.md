# CIMTinyTO: Stochastic & Digital Compute-in-Memory Accelerator

> 📌 **Laptop Resumption Notice (Antigravity Pairing)**  
> **Status:** Pillar 2 (RTL & Verification) complete and 100% passing.  
> **Next Step:** [Phase 1 of Pedagogical RTL Review](docs/pedagogical_rtl_review_roadmap.md) (`src/scim_pe.v` & `src/scim_compressor_42.v`).  
>
> **Quick Start on Laptop:**
> ```bash
> git pull origin main
> source .venv/bin/activate
> ```
> **Prompt for Antigravity on Laptop:**
> > *"Let's follow Phase 1 of `docs/pedagogical_rtl_review_roadmap.md`: walk me through `src/scim_pe.v` and `src/scim_compressor_42.v` from a manufacturing & standard-cell perspective."*

---

## Overview

**CIMTinyTO** is an open-source standard-cell **Stochastic Compute-in-Memory (SCIM)** and **Digital Compute-in-Memory (DCIM)** accelerator macro designed for Tiny Tapeout shuttles targeting the SkyWater 130nm (`sky130_fd_sc_hd`) and IHP SG13G2 process design kits (PDKs).

The architecture features:
1. **Unified Reconfigurable PE Array:** 16×16 single-wire PEs supporting Unipolar AND (Mode 0), Bipolar XNOR (Mode 1), and Hybrid ReLU (Mode 2) without dual-wire routing overhead.
2. **Central Shared Activation Tree:** Mathematically collapses the column delta to $\Delta = 2P - A$, computing the activation reduction $A = \sum a_i$ once for the whole chip and cutting macro Wallace trees from 32 to 17 (~47% area reduction).
3. **High-Speed Wallace Reduction:** 16-to-5 spatial reduction using 4:2 carry-save compressors with $C_{\text{out}}$ independent of $C_{\text{in}}$ (zero horizontal carry ripple, critical path $< 1.30\text{ ns}$).
4. **Spatial Decorrelation via Galois Phase Offsets:** 16 parallel 8-bit Galois LFSRs loaded with stride-15 trajectory seeds, maintaining $|r_{ij}| \le 0.0259 \ll 0.05$ without extra programmable shadow registers.
5. **Non-Destructive DFT Readback:** Serial weight shift chain with MSB `w_dout` loopback for 100% test observability over SPI.

---

## Repository Map & Documentation

- [`docs/pedagogical_rtl_review_roadmap.md`](docs/pedagogical_rtl_review_roadmap.md): The 5-phase "Tour & Harden" RTL review and vulnerability patching guide.
- [`docs/rtl_audit_and_poking_holes.md`](docs/rtl_audit_and_poking_holes.md): Line-by-line silicon vulnerability analysis and edge case traps.
- [`PROGRESS.md`](PROGRESS.md): Live log of architectural decisions, completed gates, and deliverables.
- [`HANDOFF.md`](HANDOFF.md): Workstation $\leftrightarrow$ Laptop synchronization and session state.
- [`model/`](model/): Python NumPy bit-exact golden reference model (`sim_scim.py`) and Gate 0 vectors (`test_vectors_gate0.json`).
- [`src/`](src/): Synthesizable Verilog submodules (`tt_um_scim_core.v`, `scim_pe.v`, `scim_compressor_42.v`, etc.).
- [`test/`](test/): Cocotb unit tests and end-to-end regression harness (`Makefile`).

---

## Current Status

- **Pillar 1 (Gate 0 - System & Mathematical Modeling):** 100% Verified & Frozen.
- **Pillar 2 (Gate 1 - Microarchitecture & Verilog RTL):** 100% Complete & Passing (Verilator lint: 0 warnings; Cocotb: 8/8 vectors bit-exact).
- **In Progress:** Pedagogical RTL Review & Defensive Hardening (Holes #1–#5) prior to Pillar 3 (Physical ASIC Implementation / OpenLane 2).
