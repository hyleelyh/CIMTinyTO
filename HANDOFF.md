# Session Handoff: Pillar 6 Pre-Silicon Emulation Planning & Bench Matrix Complete

- **Date:** 2026-10-07 07:46
- **Machine:** Laptop (`juliusli-MSI` / user `juliusli`)
- **Active Branch:** `main`
- **Active Phase:** **PILLAR 6: PRE-SILICON EMULATION (FPGA TESTBENCH)**
- **Status:** Hardware accessories BOM finalized, cable dimensions verified, Implementation Plan prepared for review.

---

## Pillar 6 Hardware Bench & Cabling Matrix

| Platform / Equipment | Interface & Cable Specs | Safety & Operating Parameter | Verification Role |
| :--- | :--- | :--- | :--- |
| **PYNQ-Z2** (Zynq-7020) | $4\text{ mm}$ Banana $\rightarrow$ $5.5\times 2.1\text{ mm}$ DC Barrel (Center +) | Korad KA3005P: $12.00\text{V}$, $2.20\text{A}$ OCP, `JP5` = `REG`, `JP1` = `SD` | High-speed $50\text{--}100\text{ MHz}$ AXI MMIO regressions via Jupyter |
| **DE10-Lite** (MAX 10) | USB Type-A to Type-B (Standard printer cable) | USB Bus Power ($5\text{V} / 500\text{ mA}$) | Tactile switches, clock button & 6-digit 7-segment hex display |
| **RPi 5 + NoIR Cam v2** | 22-pin ($0.5\text{ mm}$) to 15-pin ($1.0\text{ mm}$) FFC cable | Sony IMX219 native Linux `libcamera` | Micro-ResNet Live Video Inference (12.5 FPS) with night-vision |
| **Logic Analyzer** | DSLogic Plus (16-ch) or HiLetgo (8-ch) | $+3.3\text{V}$ LVCMOS thresholds | Sniffing serial weight chain, accumulator bus, and control handshakes |
| **Level Shifter** | TXS0108E (8-channel bidirectional) | $V_{CCA} = 3.3\text{V}$, $V_{CCB} = 5.0\text{V}$ | Arduino Uno R3 electrical isolation |

---

## Current Architecture Document
- [`implementation_plan.md`](file:///home/juliusli/.gemini/antigravity/brain/b7f6544b-fb70-432c-8eaf-25c7dba027c6/implementation_plan.md) is active and in review stage on Laptop.

---

## Next Steps for Pillar 6 Execution

1. User reviews and approves `implementation_plan.md`.
2. Implement `fpga/pynq_z2/rtl/tt_scim_axi_wrapper.v` (AXI4-Lite slave bridge for ARM PS MMIO).
3. Implement `fpga/de10_lite/rtl/de10_lite_top.v` (Intel MAX 10 tactile wrapper and 7-segment driver).
4. Run Verilator lint and Icarus Verilog testbench on the AXI wrapper.
5. Create Vivado overlay batch synthesis scripts and PYNQ Jupyter notebook driver.
