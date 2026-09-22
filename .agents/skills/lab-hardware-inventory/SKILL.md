---
name: lab-hardware-inventory
description: >-
  Inventory, specifications, interface protocols, and safety rules for the user's available
  hardware laboratory equipment (PYNQ-Z2, DE10-Lite, STM32 B-U585I, RPi 5, HiFive 1,
  OBDLink LX, Korad KA3005P, Arduino Uno R3). Use when planning or executing testbenches,
  emulation (Pillar 6), post-silicon bring-up (Pillar 7), or external hardware demos.
---

# User Laboratory Hardware Inventory & Bring-Up Matrix

This skill records all bench equipment, development boards, and sensor modules owned and available by the user for testing, emulating, and demonstrating the **CIMTinyTO** ASIC.

---

## 1. Laboratory Bench Power & Bring-Up Instrumentation

### Korad KA3005P Programmable Linear DC Power Supply
* **Specifications:** $0\text{--}30\text{V}$, $0\text{--}5\text{A}$, $10\text{mV} / 1\text{mA}$ resolution, linear topology ($< 2\,\text{mV}_{\text{rms}}$ ripple), Over-Voltage Protection (OVP), Over-Current Protection (OCP), USB/RS232 serial control.
* **Primary Role:** Day-1 Silicon Bring-Up "Smoke Testing", Static Leakage & Dynamic Power ($P = C V^2 f$) profiling, and power margining.
* **Safety Preset for Tiny Tapeout Carrier:**
  * Voltage: **$5.00\text{V}$**
  * Current Limit: **$120\text{ mA}$** (trips OCP if a board short exists)
  * OVP: **$5.50\text{V}$**
  * Output State: **ALWAYS OFF** before connecting or disconnecting test leads.

---

## 2. FPGA Emulation & Logic Verification Platforms (3.3V Native)

### PYNQ-Z2 (Xilinx Zynq-7020 SoC)
* **Architecture:** Dual ARM Cortex-A9 @ 650 MHz + Artix-7 FPGA fabric (85K logic cells, 220 DSP slices).
* **Interfaces:** 2x PMOD (PMOD A, PMOD B), Arduino Uno shield headers, Raspberry Pi 40-pin header, Ethernet, USB Host, HDMI In/Out.
* **Logic Levels:** Safe **$+3.3\text{V}$ LVCMOS**.
* **Primary Role:** Pillar 6 Pre-Silicon Emulation, automated regression testing at 10–50 MHz, and interactive Jupyter Notebook bit-exact verification against Python NumPy.

### Terasic DE10-Lite (Intel MAX 10 FPGA)
* **Architecture:** Intel MAX 10 (10M50DAF484C7G, 50K LEs, built-in ADC).
* **Interfaces:** 2x 20-pin / 40-pin GPIO headers, 10 slide switches, 2 pushbuttons, 6 7-segment displays, Arduino Uno header (3.3V).
* **Logic Levels:** Safe **$+3.3\text{V}$ LVCMOS**.
* **Primary Role:** Hardware logic analyzer, manual pattern generator (switches), and real-time accumulator hex display (7-segments).

---

## 3. Microcontrollers & Edge AI Sensor Platforms (3.3V Native)

### STMicroelectronics B-U585I-IOT02A Discovery Kit
* **Architecture:** Ultra-low-power STM32U585AII6Q (Arm Cortex-M33 with TrustZone & DSP @ 160 MHz, 786 KB SRAM, 2 MB Flash).
* **On-Board Industrial Sensors:**
  * `ISM330DHCX`: Industrial 3D accelerometer + 3D gyroscope (up to 6.6 kHz ODR, $\pm 16g$, vibration monitoring).
  * `MP23DB01HP`: Dual digital MEMS microphones (high 65 dB SNR, direct hardware PDM/MDF interface).
  * `VL53L5CX`: Multi-zone Time-of-Flight (ToF) infrared ranging sensor (8x8 depth array).
  * `IIS2MDC` (Magnetometer), `LPS22HH` (Barometer), `STTS22H` (Temperature).
* **Connectivity:** Pmod connector (CN11), Arduino Uno V3 headers, STMod+ connectors, on-board Wi-Fi/BLE (MXCHIP EMW3080), ST-LINK/V3E.
* **Logic Levels:** Safe **$+3.3\text{V}$ LVCMOS**.
* **Primary Role:** Audio Keyword Spotting (dual mics) and Industrial Motor Vibration Anomaly Detection (ISM330DHCX).

### Raspberry Pi 5
* **Architecture:** Quad-core 64-bit Arm Cortex-A76 @ 2.4 GHz, 8 GB RAM, PCIe 2.0.
* **Interfaces:** 40-pin GPIO header (high-speed SPI, I2C, UART), 2x MIPI CSI/DSI 4-lane camera/display ports, Gigabit Ethernet, USB 3.0.
* **Logic Levels:** Safe **$+3.3\text{V}$ LVCMOS**.
* **Primary Role:** Real-Time Micro-ResNet Live Camera Video Inference (12.5 FPS) with HDMI monitor display.

### SiFive HiFive 1 (Rev A/B)
* **Architecture:** SiFive Freedom E310 (FE310 32-bit RISC-V RV32IMAC @ 320 MHz).
* **Interfaces:** Arduino Uno form-factor headers (SPI, UART, I2C, PWM).
* **Logic Levels:** Set to **$+3.3\text{V}$ I/O operation**.
* **Primary Role:** Heterogeneous RISC-V CPU + Custom Open-Source CIM Accelerator demonstration.

---

## 4. Automotive Telemetry Interface

### OBDLink LX Bluetooth OBD-II Scanner
* **Architecture:** Scantool `STN1110` interpreter, high-speed ISO 15765-4 CAN bus transceiver, Bluetooth 3.0 SPP.
* **Capabilities:** Reads standard Mode 01 PIDs (RPM, Load, MAF, Speed) AND Enhanced/OEM Transmission PIDs (CVT Fluid Temperature, Slip Ratio, Degradation Index) at 100–200 PIDs/second.
* **Isolation Rule:** Connects wirelessly via Bluetooth to host (RPi 5 or STM32). ASIC & host run from an **isolated external USB power bank**. Zero direct physical wiring to the vehicle's 12V electrical rail.

---

## 5. Legacy 5V Hardware & Critical Guardrails

### Arduino Uno R3 (ATmega328P @ 16 MHz)
> [!CAUTION]
> **ELECTRICAL DESTRUCTION HAZARD:**
> The Arduino Uno R3 operates strictly at **$+5.0\text{V}$ logic levels**.
> The SkyWater 130nm ASIC I/O pads (`sky130_fd_io`) operate at **$+3.3\text{V}$** (core at $1.8\text{V}$).
> Direct connection will cause **dielectric oxide breakdown** and permanently short input pads.
> **MANDATORY RULE:** NEVER connect the Arduino Uno R3 directly to the SCIM ASIC without an external bidirectional 5V $\leftrightarrow$ 3.3V level shifter (e.g. TXS0108E) or passive resistor dividers.

---

## 6. Demonstration Quick Reference Matrix

| Demo Name | Host Platform | Sensors / Input Source | Interface | SCIM Role |
| :--- | :--- | :--- | :--- | :--- |
| **Bit-Exact HW Verification** | PYNQ-Z2 | Python NumPy vectors | PMOD (3.3V) | 50 MHz Parity Verification |
| **RISC-V Coprocessor** | SiFive HiFive 1 | Synthetic Matrix Stream | SPI (3.3V) | Math Hardware Offload |
| **Tactile Logic Console** | DE10-Lite | Slide Switches & Clock Button | 40-pin GPIO (3.3V) | 7-Segment Hex Display |
| **Voice Keyword Spotting** | STM32 B-U585I | Dual `MP23DB01HP` Mics | PMOD / SPI (3.3V) | 16-channel MFCC Acoustic Model |
| **Motor Vibration Anomaly** | STM32 B-U585I | `ISM330DHCX` 3D IMU | PMOD / SPI (3.3V) | 16-bin FFT Spectral Anomaly |
| **Real-Time Video Vision** | Raspberry Pi 5 | USB / MIPI CSI Camera | High-Speed SPI (3.3V) | Micro-ResNet @ 12.5 FPS |
| **In-Car CVT Diagnostics** | OBDLink LX + RPi5 | Car CAN Bus Telemetry | Bluetooth $\rightarrow$ SPI | 16-PID Engine/CVT Stress Model |
