# Session Handoff: Pillar 6 Pre-Silicon Emulation — Toolchain Setup & Plan Approved

- **Date:** 2026-10-10 18:20
- **Machine:** Desktop PC (`juliusli` / Primary Bring-Up Host)
- **Active Branch:** `main`
- **Active Phase:** **PILLAR 6: PRE-SILICON EMULATION (FPGA TESTBENCH)**
- **Hardware Logistics:** Physical bench cables (Banana-to-barrel, Pi 5 camera ribbon) arriving Sunday; FPGA toolchains (Vivado 2022.2 & Quartus Prime Lite 23.1) configured and verified on Desktop PC.
- **Status:** **Components 1, 2, & 3 100% COMPLETE & VERIFIED.** 
  - PYNQ-Z2 AXI4-Lite slave bridge (`tt_scim_axi_wrapper.v`) verified via Cocotb (5/5 PASS in 0.27s).
  - DE10-Lite tactile console (`de10_lite_top.v`) verified via Cocotb (4/4 PASS in 0.05s) and compiled with Quartus Prime Lite (`de10_lite_scim.sof` generated, +4.253ns setup slack @ 50 MHz).

---

## Pillar 6 Verification Scorecard (Pre-Synthesis Simulation)

| Test Suite / Target | Description | Simulated Time | Real Time | Status |
| :--- | :--- | :---: | :---: | :---: |
| `test_fpga_axi` (5 tests) | PYNQ-Z2 AXI4-Lite slave bridge & MVM MMIO | $168,690\text{ ns}$ | $0.27\text{ s}$ | ✅ **5/5 PASS** |
| `test_de10_lite` (4 tests)| DE10-Lite tactile console (reset, 7-seg, debouncer, MVM)| $57,920\text{ ns}$ | $0.05\text{ s}$ | ✅ **4/4 PASS** |
| `build_max10.tcl` (Quartus)| Intel MAX 10 FPGA physical synthesis & SOF generation | — | $23\text{ s}$ | ✅ **PASS (+4.253ns slack)** |
| **Total** | **All Pre-Synthesis & Physical Sign-Off Targets** | — | — | ✅ **100% PASS** |

---

## 10-Application Demonstration & Experimental Matrix

| # | Demo Application | Host Platform | Sensors / Input Source | Interface | SCIM Role |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Bit-Exact HW Verification** | PYNQ-Z2 FPGA | Python NumPy vectors | PMOD / MMIO (3.3V) | 50 MHz Parity Verification |
| **2** | **RISC-V Coprocessor** | SiFive HiFive 1 | Synthetic Matrix Stream | SPI (3.3V) | Math Hardware Offload |
| **3** | **Tactile Logic Console** | DE10-Lite | Slide Switches & Clock Button | 40-pin GPIO (3.3V) | 7-Segment Hex Display |
| **4** | **Voice Keyword Spotting** | STM32 B-U585I | Dual `MP23DB01HP` Mics | PMOD / SPI (3.3V) | 16-channel MFCC Acoustic Model |
| **5** | **Motor Vibration Anomaly** | STM32 B-U585I | `ISM330DHCX` 3D IMU | PMOD / SPI (3.3V) | 16-bin FFT Spectral Anomaly |
| **6** | **Real-Time Video Vision** | Raspberry Pi 5 | NoIR Camera Module v2 | High-Speed SPI (3.3V) | Micro-ResNet @ 12.5 FPS |
| **7** | **Optical Gesture / ToF** | STM32 B-U585I | `VL53L5CX` ToF Sensor | PMOD / SPI (3.3V) | 8x8 Depth Swipe Classifier |
| **8** | **8-Bit MCU Math Offload** | Arduino Uno R3 | Synthetic vectors | SPI (+ TXS0108E) | Legacy 5V MCU Acceleration |
| **9** | **In-Car CVT Diagnostics** | OBDLink LX + RPi5 | Car CAN Bus Telemetry | Bluetooth $\rightarrow$ SPI | 16-PID Engine/CVT Stress Model |
| **10** | **Stochastic Shuffling Study** | PYNQ-Z2 & RP2040 / RPi5 | Permuted Benchmark Vectors | PMOD / SPI (3.3V) | Seed effect & noise decorrelation across 20.9T permutations |

---

## Next Steps for Pillar 6 Execution

1. Implement PYNQ-Z2 Vivado overlay batch synthesis scripts (`fpga/pynq_z2/scripts/build_overlay.tcl`) and constraints (`fpga/pynq_z2/constrs/pynq_z2.xdc`).
2. Implement high-level Python MMIO driver (`fpga/pynq_z2/jupyter/scim_pynq_driver.py`) and validation notebook (`fpga/pynq_z2/jupyter/pynq_scim_validation.ipynb`).
3. Run Verilator lint checks on all modules.
