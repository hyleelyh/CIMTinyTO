# Session Handoff: Pillar 6 Pre-Silicon Emulation — Toolchain Setup & Plan Approved

- **Date:** 2026-10-10 12:40
- **Machine:** Desktop PC (`juliusli` / Primary Bring-Up Host)
- **Active Branch:** `main`
- **Active Phase:** **PILLAR 6: PRE-SILICON EMULATION (FPGA TESTBENCH)**
- **Hardware Logistics:** Physical bench cables (Banana-to-barrel, Pi 5 camera ribbon) arriving Sunday; FPGA toolchains (Vivado 2022.2 & Quartus Prime Lite 23.1) configured on Desktop PC.
- **Status:** **Components 1 & 2 100% COMPLETE & VERIFIED.** PYNQ-Z2 AXI4-Lite slave bridge (`tt_scim_axi_wrapper.v`) implemented and fully verified via Cocotb regression suite (`test_fpga_axi.py`) with 5/5 PASS in 0.27s real time.

---

## Pillar 6 Verification Scorecard (Pre-Synthesis Simulation)

| Test Case | Description | Simulated Time | Real Time | Status |
| :--- | :--- | :---: | :---: | :---: |
| `test_axi_handshake` | AMBA AXI4-Lite register access & decode logic | $1,030\text{ ns}$ | $< 0.01\text{ s}$ | ✅ **PASS** |
| `test_reset_and_control` | Synchronous active-low reset & control strobes | $870\text{ ns}$ | $< 0.01\text{ s}$ | ✅ **PASS** |
| `test_weight_shift_loopback`| 256-bit DFT scan chain serial loopback (`w_dout`) | $77,330\text{ ns}$ | $0.08\text{ s}$ | ✅ **PASS** |
| `test_axi_mvm_computation` | 256-cycle MVM via MMIO + 16-channel readback | $44,730\text{ ns}$ | $0.10\text{ s}$ | ✅ **PASS** |
| `test_stochastic_shuffling`| Application #10 permutation invariance | $44,730\text{ ns}$ | $0.09\text{ s}$ | ✅ **PASS** |
| **Total** | **Full Pre-Synthesis Regression Suite** | **$168,690\text{ ns}$** | **$0.27\text{ s}$** | ✅ **5/5 PASS** |

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

1. Implement DE10-Lite tactile console RTL (`fpga/de10_lite/rtl/`):
   - `hex7seg_decoder.v`, `debounce.v`, `de10_lite_top.v`, `constrs/de10_lite.qsf`, and `scripts/build_max10.tcl`.
2. Run Verilator lint checks (`verilator --lint-only -Wall -Isrc`) on all top wrappers.
3. Implement Vivado overlay batch synthesis scripts (`fpga/pynq_z2/scripts/build_overlay.tcl`) and PYNQ Jupyter driver (`fpga/pynq_z2/jupyter/scim_pynq_driver.py`).
