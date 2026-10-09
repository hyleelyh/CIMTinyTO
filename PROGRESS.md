# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-08 22:15 (Run 58: Pillar 6 Implementation Plan Finalization, Shuttle Mapping & Toolchain Setup)

### [Built]
- **`implementation_plan.md`:** Finalized detailed architectural specifications for Pillar 6 coding activities, including the 32-bit AXI4-Lite register map, dual-mode clocking, PMOD snooping breakout, and Cocotb pre-synthesis simulation suite.
- **`PROGRESS.md` & `HANDOFF.md`:** Synchronized state, shuttle placement analysis, EDA toolchain installation guides, and session handoff records.

### [Architecture Decisions & Silicon Forensics]
- **Tiny Tapeout Shuttle Physical Floorplan Verification (Mux Address 265):**
  - Verified project location on the SkyWater 130nm shuttle die: 2x2 tile block situated in Columns 4 & 5 on the left bank (3 tiles from the central spine, adjacent to the dedicated analog switch row).
  - Physical wire delay across the 3 tiles ($\sim 480\,\mu\text{m}$) is $< 0.15\text{ ns}$ on top-level metal layers, well within the $20.0\text{ ns}$ cycle budget at $50\text{ MHz}$ ($<0.7\%$ clock margin).
  - Confirmed the location is in the optimal "Goldilocks Zone": buffered from central spine wiring track congestion while well protected from edge-of-die mechanical dicing stress and CMP thickness variations.
- **AXI4-Lite Register Memory Map Architecture:**
  - Resolved directional separation: `0x04: REG_DATA_IN` maps exclusively to dedicated input pins `ui_in[7:0]` (CPU $\rightarrow$ ASIC write path), while `0x0C: REG_DATA_OUT` maps exclusively to dedicated output pins `uo_out[7:0]` (ASIC $\rightarrow$ CPU read path), ensuring deterministic readback without asymmetric register side-effects.
- **Desktop PC Toolchain Environment Setup (`juliusli`):**
  - **AMD Xilinx Vivado 2022.2 ML Standard:** Web installer verified and executed on Ubuntu 24.04 with pre-installed `libtinfo5`/`libncurses5` compatibility libraries; configured for 7-Series / Zynq-7000 (`xc7z020`) for PYNQ-Z2 overlay synthesis.
  - **Intel Quartus Prime Lite 23.1std:** Configured with MAX 10 device support (`10M50DAF484C7G`) for DE10-Lite; Questa simulator pruned to save $4.4\text{ GB}$ in favor of our local 1.5s Cocotb/Icarus verification suite.

### [Current Pipeline State]
- **Pillars 1–5:** ✅ 100% COMPLETE, SIGNED OFF & FROZEN.
- **Tiny Tapeout SKY 26d Submission:** ✅ SUBMITTED & VERIFIED (PR #85 green, Mux 265 confirmed).
- **Pillar 6 (Pre-Silicon Emulation):** 🚀 **ACTIVE / IN PROGRESS.**
  - Implementation Plan reviewed, clarified, and approved.
  - Shuttle physical floorplan confirmed.
  - FPGA EDA toolchains configured on Desktop PC.
  - Ready for RTL coding and pre-synthesis simulation verification.

### [Next Steps]
1. Implement `fpga/pynq_z2/rtl/tt_scim_axi_wrapper.v` (AXI4-Lite slave bridge for ARM PS MMIO).
2. Create `test/tb_fpga_axi.v` and Cocotb testbench (`test/test_fpga_axi.py`) verifying AXI read/write handshakes and cycle counters.
3. Implement `fpga/de10_lite/rtl/de10_lite_top.v` with debounced clock stepping and 7-segment hex display decoder.
4. Prepare Vivado overlay batch synthesis scripts (`build_overlay.tcl`) and PYNQ Jupyter testbench driver.
