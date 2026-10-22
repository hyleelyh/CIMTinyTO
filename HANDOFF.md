# Session Handoff: Pillar 6.0 Physical Silicon Emulation Complete & Ready for Pillar 6.1 (Micro-ResNet)

- **Date:** 2026-10-22 08:20
- **Machine Handoff:** Switching from Laptop (`juliusli-MSI`) $\longrightarrow$ Desktop PC (`juliusli`).
- **Workstation Role on PC:** Primary hardware bring-up and emulation workstation (collocated with Korad KA3005P, AMD PYNQ-Z2, Intel MAX 10 DE10-Lite, Logic Analyzer).
- **Active Branch:** `main` (clean, fully synchronized).
- **Active Phase:** **PILLAR 6: PRE-SILICON EMULATION & SOFTWARE DEVELOPMENT (OCT 2026 – JUNE 2027)**
- **Timeline Context:** Tiny Tapeout `ttsky26d` **PR #86 MERGED** (Commit `85b17b98`, $2\times 2$ tiles, all green; provisional shuttle mux address `227 *`). Shuttle closes end of November 2026; physical packaged silicon & carrier board delivery arrives ~June 2027. All work between October 2026 and June 2027 constitutes **Pillar 6 pre-silicon emulation, software driver polish, and application pipelines**. Pillar 7 (physical chip bring-up) begins strictly in June 2027 upon physical silicon arrival.
- **Hardware Logistics:** Both Terasic DE10-Lite tactile mode AND AMD PYNQ-Z2 50 MHz AXI4-Lite Macro **100% verified on physical silicon hardware**.
- **Status:** **Pillar 6.0 Baseline Emulation Infrastructure & Handshake SIGNED OFF ON SILICON. Datapath walkthrough complete. Ready for Pillar 6.1 (Micro-ResNet) on Desktop PC.**

> [!IMPORTANT]
> **Action Note for Next Session (Tomorrow at Desktop PC):**
> 1. On Desktop PC (`juliusli`), run `git pull` to ensure local repository is up to date with `main`.
> 2. Per the **Strict Single-Pillar Session Scope Directive** in `AGENTS.md`, launch a **FRESH CHAT SESSION** for:  
>    **Pillar 6.1: Micro-ResNet Pre-Silicon Emulation & Edge AI Software Development** (Application #6 / Tier 1-3 inference pipeline on PYNQ-Z2 hardware).

---

## Pillar 6.0 Physical Verification Scorecard

| Test Suite / Target | Description | Timing Closure | Real Time | Status |
| :--- | :--- | :---: | :---: | :---: |
| `test_fpga_axi` (5 tests) | PYNQ-Z2 AXI4-Lite slave bridge & MVM MMIO | — | $0.27\text{ s}$ | ✅ **5/5 PASS** |
| `test_de10_lite` (4 tests)| DE10-Lite tactile console (reset, 7-seg, debouncer, MVM)| — | $0.05\text{ s}$ | ✅ **4/4 PASS** |
| `scim_pynq_driver.py` (3 tests)| Physical Python MMIO driver & Application #10 on Zynq | — | Real Hardware | ✅ **3/3 PASS (0 LSB Diff)** |
| `pynq_scim_validation.ipynb` (10 tests)| Live 10-vector Gate-0 regression on physical FPGA | — | Real Hardware | ✅ **10/10 PASS (100% Bit-Exact)** |
| `build_max10.tcl` (Quartus)| Intel MAX 10 FPGA synthesis & SOF generation | **+4.331 ns** slack | $17\text{ s}$ | ✅ **SOF Generated** |
| **DE10-Lite Physical Silicon**| Tactile 256-cycle MVM, 5 Hz auto/manual clock on Max 10 | — | Real Hardware | ✅ **100% VERIFIED** |
| `build_overlay.tcl` (Vivado)| Xilinx Zynq-7020 synthesis & bitstream generation | **+5.791 ns** slack | $1\text{m } 40\text{s}$ | ✅ **BIT + HWH Generated** |
| **PYNQ-Z2 Physical Silicon**| Live 50 MHz AXI4-Lite Stochastic MVM on XC7Z020 | **+5.791 ns** slack | Real Hardware | ✅ **100% VERIFIED** |
| `verilator` linting | All FPGA wrappers (`de10_lite_top.v`, `tt_scim_axi_wrapper.v`) | — | $1.2\text{ s}$ | ✅ **0 Errors, 0 Warnings** |
| **Total** | **All Pre-Silicon FPGA Emulation Sign-Off Targets** | — | — | ✅ **100% PASS ON SILICON** |

---

## Deliverables Generated in Pillar 6

```
fpga/
├── pynq_z2/
│   ├── rtl/
│   │   └── tt_scim_axi_wrapper.v        # AMBA AXI4-Lite 32-bit slave bridge wrapping frozen ASIC core
│   ├── constrs/
│   │   └── pynq_z2.xdc                  # PMOD A/B snooping pinouts (LVCMOS33) & false path constraints
│   ├── scripts/
│   │   └── build_overlay.tcl            # Headless Vivado batch synthesis script
│   ├── overlay/
│   │   ├── scim_pynq.bit                # 3.9 MB bitstream ready for PYNQ Linux
│   │   ├── scim_pynq.hwh                # 131 KB hardware handoff metadata for pynq.Overlay
│   │   ├── timing_summary.rpt           # +5.791 ns setup slack, 0 hold violations @ 50 MHz
│   │   └── utilization.rpt              # 3.00% LUTs, 0 BRAM, 0 DSP slices
│   └── jupyter/
│       ├── scim_pynq_driver.py          # High-level Python MMIO driver with Application #10 shuffling
│       └── pynq_scim_validation.ipynb   # Interactive validation notebook (10-test Gate-0 parity)
│
└── de10_lite/
    ├── rtl/
    │   ├── de10_lite_top.v              # Tactile console mapping switches, buttons & 6 hex displays
    │   ├── hex7seg_decoder.v            # Active-low common-anode 7-segment hex decoder
    │   └── debounce.v                   # Glitch-free clock-step pushbutton filter
    ├── constrs/
    │   ├── de10_lite.qsf                # Intel MAX 10 pin assignments (3.3V LVTTL)
    │   └── de10_lite.sdc                # 50 MHz SDC timing constraints
    └── scripts/
        └── build_max10.tcl              # Headless Quartus Prime Lite compilation script
```

---

## Application Demonstration Matrix

### Core Demonstration Portfolio (Applications 1–10: High Priority)
*Targeted for full physical implementation across pre-silicon emulation (Pillar 6) and post-silicon bring-up (Pillar 7) barring unexpected hardware failures.*

| # | Demo Application | Host Platform | Sensors / Input Source | Interface | SCIM Role | Status |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| **1** | **Bit-Exact HW Verification** | PYNQ-Z2 FPGA | Python NumPy vectors | PMOD / MMIO (3.3V) | 50 MHz Parity Verification | ✅ Signed Off |
| **2** | **RISC-V Coprocessor** | SiFive HiFive 1 | Synthetic Matrix Stream | SPI (3.3V) | Math Hardware Offload | ⏳ Upcoming |
| **3** | **Tactile Logic Console** | DE10-Lite | Slide Switches & Clock Button | 40-pin GPIO (3.3V) | 7-Segment Hex Display | ✅ Signed Off |
| **4** | **Voice Keyword Spotting** | STM32 B-U585I | Dual `MP23DB01HP` Mics | PMOD / SPI (3.3V) | 16-channel MFCC Acoustic Model | ⏳ Upcoming |
| **5** | **Motor Vibration Anomaly** | STM32 B-U585I | `ISM330DHCX` 3D IMU | PMOD / SPI (3.3V) | 16-bin FFT Spectral Anomaly | ⏳ Upcoming |
| **6** | **Real-Time Video Vision** | Raspberry Pi 5 | NoIR Camera Module v2 | High-Speed SPI (3.3V) | Micro-ResNet @ 12.5 FPS | ⏳ Upcoming |
| **7** | **Optical Gesture / ToF** | STM32 B-U585I | `VL53L5CX` ToF Sensor | PMOD / SPI (3.3V) | 8x8 Depth Swipe Classifier | ⏳ Upcoming |
| **8** | **8-Bit MCU Math Offload** | Arduino Uno R3 | Synthetic vectors | SPI (+ TXS0108E) | Legacy 5V MCU Acceleration | ⏳ Upcoming |
| **9** | **In-Car CVT Diagnostics** | OBDLink LX + RPi5 | Car CAN Bus Telemetry | Bluetooth $\rightarrow$ SPI | 16-PID Engine/CVT Stress Model | ⏳ Upcoming |
| **10** | **Stochastic Shuffling Study** | PYNQ-Z2 & RP2040 / RPi5 | Permuted Benchmark Vectors | PMOD / SPI (3.3V) | Seed effect & noise decorrelation across 20.9T permutations | ✅ Signed Off |

---

### Extended / "Nice-to-Try" Applications (Beyond Application 10)
*Applications beyond #10 are categorized as **Nice to Try / Stretch Explorations** and will remain secondary unless experimental findings or specific performance requirements justify moving up their priority.*

#### **Application #11: Multi-Tier Micro-ResNet Throughput & AXI-DMA Benchmark**
* **Host Platform:** PYNQ-Z2 FPGA
* **Input Source:** $32 \times 32$ CIFAR-10 / Camera Stream ($\approx 7,800$ tiles per frame)
* **Goal:** Quantify and benchmark the software-to-hardware speedup across the three transport tiers, testing the transition from interpreted MMIO to full hardware line-rate streaming:

| Implementation Tier | How It Works | Time per $16 \times 16$ Tile | Total Time per Frame | Achievable Frame Rate | Project Role / Priority |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Tier 1: Pure Python MMIO** | Python `for` loops call `self.mmio.write()` in Jupyter. Bytecode & AXI stalls dominate. | $\sim 180\text{ }\mu\text{s}$ | $7,800 \times 180\text{ }\mu\text{s} = \mathbf{1.4\text{ s}}$ | **$\approx 0.7\text{ FPS}$** | **Pillar 6.1 Baseline (Verification & Debug)** |
| **Tier 2: Compiled C/C++ MMIO** | Direct `/dev/mem` user-space pointer access via ARM assembly `STR`/`LDR` instructions. | $\sim 15\text{ }\mu\text{s}$ | $7,800 \times 15\text{ }\mu\text{s} = \mathbf{0.12\text{ s}}$ | **$\approx 8.3\text{ FPS}$** | **Nice to Try (Fast Software Upgrade)** |
| **Tier 3: Autonomous Feeder / AXI-DMA** | Dedicated FPGA state machine / AXI-DMA loops through tiles at 50 MHz without CPU intervention. | $\mathbf{6.08\text{ }\mu\text{s}}$ | $7,800 \times 6.08\text{ }\mu\text{s} = \mathbf{0.047\text{ s}}$ | **$\approx 21.3\text{ FPS}$** | **Nice to Try (Full Silicon Line Rate)** |

---

## Mandatory Sub-Pillar Session Handoff Instruction
Per the **Strict Single-Pillar Session Scope Directive** in `AGENTS.md`:
* **Pillar 6.0 (Baseline Emulation Infrastructure & Handshake) is complete, hardened, and verified.**
* **Pillar 6 remains active through June 2027:** Each discrete Edge AI application sprint will be executed in its own dedicated, fresh chat session under Pillar 6.
* Please open a **FRESH CHAT SESSION** for **Pillar 6.1: Micro-ResNet Pre-Silicon Emulation & Edge AI Software Development**.
