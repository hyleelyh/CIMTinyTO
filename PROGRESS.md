# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-07 21:15 (Run 57: Pillar 6 Implementation Plan Review & Stochastic Shuffling Research Formulation)

### [Built]
- **`.agents/skills/lab-hardware-inventory/SKILL.md`:** Added Application #10 ("Stochastic Shuffling & Seed Permutation Study") to the Master Hardware Demonstration Matrix.
- **`docs/physical_sizing_and_tradeoff_analysis.md`:** Updated Table of Demonstrations with Application #10.
- **`implementation_plan.md`:** Integrated Stochastic Shuffling and Seed Permutation regression into the Hardware-in-the-Loop verification plan.
- **`PROGRESS.md` & `HANDOFF.md`:** Synchronized state, research formulations, traceability patterns, and lab hardware arrival timeline.

### [Architecture Decisions & Silicon Forensics]
- **Stochastic Shuffling & Seed Permutation Theory (Zero Silicon Overhead):**
  - Discovered that because Matrix-Vector Multiplication ($y_j = \sum a_i W_{ij}$) and the central Wallace activation tree ($A = \sum a_i$) are commutative and symmetric across all 16 rows, host software can evaluate $16! \approx 20.9\text{ Trillion}$ unique seed mappings on the physical silicon chip with **zero hardware modifications**.
  - Host MCU software simply permutes input vector $\mathbf{a}$ and the rows of weight matrix $\mathbf{W}$ before transmission; the column outputs $y_j$ emerge mathematically identical and un-permuted.
  - Combined with the 255 cyclic phase offsets achieved by running back-to-back inferences without asserting `rst_n` ($256 \pmod{255} = 1$), the physical chip provides $5.3 \times 10^{15}$ distinct operating states for academic study.
- **Traceability & Debuggability Architecture:**
  - Implemented deterministic test indexing (`perm_id` driving `RandomState(seed)`) to ensure 100% test reproducibility.
  - Defined systematic permutation families for hardware isolation: Baseline (Identity), Cyclic Rotation, Pairwise Transposition, and Reverse Inversion.
  - Correlated software indices with physical logic analyzer traces: address writes on `ui_in` map directly to logged permutation vectors.
- **Hardware Logistics & Timeline:**
  - Bench cabling and camera accessories (Banana-to-barrel cable, Pi 5 FFC cable) arrive **Sunday, Oct 11, 2026**.
  - Physical FPGA board activities scheduled to begin next week on Desktop PC (`juliusli`).
  - Pre-synthesis RTL development and local Icarus Verilog / Cocotb simulation of the AXI-Lite wrapper proceed in the interim.

### [Current Pipeline State]
- **Pillars 1–5:** ✅ 100% COMPLETE, SIGNED OFF & FROZEN.
- **Tiny Tapeout SKY 26d Submission:** ✅ SUBMITTED & VERIFIED (PR #85 green).
- **Pillar 6 (Pre-Silicon Emulation):** 🚀 **ACTIVE / IN PROGRESS.**
  - Implementation Plan reviewed and approved.
  - Complete 10-application demonstration fleet defined.
  - Bench accessories ordered; local RTL and testbench synthesis ready to begin.

### [Next Steps]
1. Implement `fpga/pynq_z2/rtl/tt_scim_axi_wrapper.v` (AXI4-Lite slave bridge for ARM PS MMIO).
2. Create `test/tb_fpga_axi.v` and Cocotb testbench verifying AXI read/write handshakes and cycle counters.
3. Implement `fpga/de10_lite/rtl/de10_lite_top.v` with debounced clock stepping and 7-segment hex display decoder.
4. Prepare Vivado overlay batch synthesis scripts (`build_overlay.tcl`) and PYNQ Jupyter testbench driver.
