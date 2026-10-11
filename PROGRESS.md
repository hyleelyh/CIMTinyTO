# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-11 15:56 (Run 62: Application Architecture Blueprint & Physical Bring-Up Matrix Finalized)

### [Built]
- **`fpga/pynq_z2/constrs/pynq_z2.xdc`:** AMD Xilinx Zynq-7020 pin assignments for PMOD A (Header JA, `uo_out[7:0]` accumulator byte) and PMOD B (Header JB, control/status signals `clk`, `rst_n`, `busy`, `done`, `w_dout`, `ovf`, `ctrl_strobe`, `wr_act`) operating at safe +3.3V LVCMOS with false-path timing exceptions.
- **`fpga/pynq_z2/scripts/build_overlay.tcl`:** Headless batch Vivado 2022.2 Tcl compilation script automating Block Design construction, RTL module reference instantiation, AXI4-Lite interconnect synthesis, placement, routing, bitstream generation, and hardware handoff export.
- **`fpga/pynq_z2/overlay/scim_pynq.bit` & `scim_pynq.hwh`:** Production hardware bitstream (3.9 MB) and hardware handoff definition (131 KB) ready for direct loading on PYNQ Linux via Python `pynq.Overlay`.
- **`fpga/pynq_z2/overlay/timing_summary.rpt` & `utilization.rpt`:** Complete physical implementation sign-off reports on Zynq-7020:
  - **Timing Slack:** **Worst Negative Slack (WNS) = +5.791 ns** at 50 MHz ($f_{\max} \approx 70.4\text{ MHz}$), **Worst Hold Slack (WHS) = +0.059 ns**, **0 failing endpoints**.
  - **Logic Utilization:** **1,597 / 53,200 LUTs (3.00%)**, **1,258 / 106,400 Registers (1.18%)**, **0 Latches (0.00%)**.
  - **Hardware DSP Multipliers:** **0 / 220 (0.00%)** — confirms pure stochastic single-gate math.
  - **Block RAM Bits:** **0 / 140 (0.00%)** — confirms true standard-cell in-memory DFF architecture.
- **`fpga/pynq_z2/jupyter/scim_pynq_driver.py`:** Production Python MMIO driver supporting direct hardware register access and bit-exact software fallback with Application #10 stochastic shuffling and Gate-0 parity validation.
- **`fpga/pynq_z2/jupyter/pynq_scim_validation.ipynb`:** Publication-grade interactive Jupyter notebook with 10-vector Gate-0 regression (100% bit-exact PASS), convergence curve plotting, and throughput analysis.

### [Architecture Decisions & Silicon Forensics]
- **Vivado Global Synthesis for RTL Module Reference in Block Design:**
  - *Symptom:* Batch synthesis initially failed during standalone elaboration with `module 'scim_bd_ps7_0' not found`.
  - *Resolution:* Configured `set_property synth_checkpoint_mode None [get_files scim_bd.bd]` in `build_overlay.tcl` to enforce global top-down synthesis, allowing the Verilog RTL module reference and Zynq Processing System to elaborate seamlessly in a unified netlist without out-of-context checkpoint latency.
- **Activation Dynamic Range Bound Guardrail:**
  - *Symptom:* Test case 10 initially reported a 256 LSB difference between hardware register readback and golden simulation.
  - *Root Cause Analysis:* The test vector scaled activations with `16 * (i + 1)`, reaching `256` on column 15. The ASIC's hardware activation registers are strictly 8-bit unsigned (`reg [7:0] act_regs`), where `256 & 0xFF == 0`.
  - *Resolution:* Fixed activation vector scaling to $[0, 255]$ dynamic range (`15 * (i + 1)`), restoring 100% bit-for-bit parity across all 10 test cases.
- **Application #10 Stochastic Shuffling Noise Cancellation:**
  - Demonstrated that row permutations $y = (P \cdot W) \cdot (P \cdot x)$ dynamically randomize the Galois LFSR assigned to each dimension across inferences, canceling spatial cross-correlation noise and achieving the theoretical $\sqrt{K}$ noise reduction factor without silicon area overhead.

### [Current Pipeline State]
- **Pillars 1–5:** ✅ 100% COMPLETE, SIGNED OFF & FROZEN.
- **Tiny Tapeout SKY 26d Submission:** ✅ SUBMITTED & VERIFIED (PR #85 green, Mux 265 confirmed).
- **Pillar 6 (Pre-Silicon FPGA Emulation):** ✅ **100% COMPLETE & SIGNED OFF.**
  - **Component 1 (PYNQ-Z2 AXI4-Lite Wrapper):** ✅ 100% COMPLETE & VERIFIED.
  - **Component 2 (Pre-Synthesis Simulation Regression):** ✅ 100% COMPLETE (5/5 PASS in 0.27s).
  - **Component 3 (DE10-Lite Tactile Console & Synthesis):** ✅ 100% COMPLETE (4/4 PASS in 0.05s, Quartus SOF generated with +4.253ns setup slack).
  - **Component 4 (PYNQ-Z2 Overlay & Jupyter Driver):** ✅ 100% COMPLETE (Bitstream & HWH exported with +5.791ns setup slack, 10/10 Jupyter tests PASS).
- **Verilator Linter:** **0 Errors, 0 Warnings** across all FPGA wrappers.
- **ASIC Core RTL (`src/`):** **100% Frozen & Untouched.**

### [Next Steps]
1. Conclude Pillar 6 and close session per Strict Single-Pillar Session Scope Directive.
2. Open a **fresh chat session** for **Pillar 7: Post-Silicon Laboratory Bring-Up & Multi-Tier Hardware Execution** (RP2040/RP2350 carrier bring-up, PYNQ-Z2 live hardware regressions, sensor interface bring-up, and automotive telemetry demos).
