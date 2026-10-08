# Session Handoff: Pillar 6 Pre-Silicon Emulation & Stochastic Shuffling Research

- **Date:** 2026-10-07 21:15
- **Machine:** Desktop PC (`juliusli` / Primary Bring-Up Host)
- **Active Branch:** `main`
- **Active Phase:** **PILLAR 6: PRE-SILICON EMULATION (FPGA TESTBENCH)**
- **Hardware Logistics:** Bench accessories (Banana-to-barrel cable, Pi 5 camera cable) arriving Sunday; live FPGA bring-up scheduled for next week.
- **Status:** Implementation Plan reviewed and approved; Application #10 ("Stochastic Shuffling & Seed Permutation Study") integrated; ready to implement `tt_scim_axi_wrapper.v`.

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

1. Implement `fpga/pynq_z2/rtl/tt_scim_axi_wrapper.v` (AXI4-Lite slave bridge for ARM PS MMIO).
2. Create `test/tb_fpga_axi.v` and Cocotb testbench to verify AXI read/write cycles and cycle latency counter.
3. Implement `fpga/de10_lite/rtl/de10_lite_top.v`, debouncer, and 7-segment hex display decoder.
4. Prepare Vivado overlay batch synthesis scripts (`build_overlay.tcl`) and PYNQ Jupyter notebook driver.
