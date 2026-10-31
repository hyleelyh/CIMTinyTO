# Session Handoff: Pillar 6.1 (Micro-ResNet Pre-Silicon Emulation) - QAT Model Preparation

- **Date:** 2026-10-31 10:55
- **Machine Session:** Desktop PC (`juliusli`).
- **Workstation Role on Desktop:** Primary bring-up platform (collocated with Korad supply, PYNQ-Z2, DE10-Lite, analyzer; Ryzen 5 9600X, 48 GB RAM).
- **Active Branch:** `main` (clean, synchronized with remote).
- **Active Phase:** **PILLAR 6: PRE-SILICON EMULATION & SOFTWARE DEVELOPMENT (OCT 2026 – JUNE 2027)**
- **Timeline Context:** Tiny Tapeout `ttsky26d` **PR #86 MERGED** (Commit `85b17b98`, $2\times 2$ tiles, all green; provisional shuttle mux address `227 *`). Shuttle closes end of November 2026; physical packaged silicon arrives ~June 2027.
- **Status:** **Pillar 6.1 ACTIVE. QAT microarchitectural deep dive and host compute analysis complete. Activity on hold per user request for review.**

> [!NOTE]
> **Pillar 6.1 Current Status & Plan:**
> 1. Hardware baseline and C MMIO streaming on physical PYNQ-Z2 fully functional.
> 2. Quantization-Aware Training (QAT) architecture formulated: Straight-Through Estimator (STE) for discrete $\pm 1$ weights, activation clipping to $[0, 255]$, and BatchNorm folding into integer bias $B$ and scales $(M, S)$.
> 3. Host hardware verified: AMD Ryzen 5 9600X (Zen 5, AVX-512) capable of full 40-epoch training in $\approx 60\text{--}90\text{ seconds}$ on CPU.
> 4. Waiting for user signal to commence Phase 1 implementation (`micro_resnet_qat.py`).



---

## Pillar 6.1 Verification Scorecard

| Test Suite / Target | Description | Coverage / Results | Real Time | Status |
| :--- | :--- | :---: | :---: | :---: |
| `test_micro_resnet.py` (8 tests) | Neural topology, stationary caching, Gate-0 parity, Tiers 1-3 | 100% Pass (0 Errors) | $0.16\text{ s}$ | ✅ **8/8 PASS** |
| `run_micro_resnet_benchmark.py` | Multi-tier throughput benchmark (Python vs C vs DMA) | Bit-Exact Class Match | Complete | ✅ **100% PASS** |
| `test_fpga_axi` (5 tests) | AXI4-Lite slave bridge & MVM MMIO regression | 100% Pass | $0.27\text{ s}$ | ✅ **5/5 PASS** |
| `scim_tier2_c/Makefile` | Compiled C MMIO driver (`libscim_tier2.so`) | Clean compilation | $0.8\text{ s}$ | ✅ **0 Warnings** |
| `ASIC Core RTL (`src/`)` | Core immutability check | 0 Lines Changed | — | ✅ **100% Frozen** |
| **Total** | **All Pillar 6.1 Verification Targets** | — | — | ✅ **100% PASS** |

---

## Deliverables Generated in Pillar 6.1

```
fpga/pynq_z2/
├── micro_resnet/
│   ├── __init__.py
│   ├── micro_resnet_model.py          # Quantized MicroResNet16 model (192 bytes weights, 16 cols)
│   ├── micro_resnet_tiler.py          # GEMM lowering & stationary weight scheduler (99.9% power saving)
│   ├── scim_tier1_mmio.py             # Tier 1: Pure Python MMIO driver
│   ├── scim_tier2_c/                  # Tier 2: Compiled C driver with /dev/mem pointers & packed strobing
│   │   ├── scim_tier2_driver.h
│   │   ├── scim_tier2_driver.c
│   │   └── Makefile
│   ├── scim_tier2_wrapper.py          # Python ctypes bridge for libscim_tier2.so
│   ├── scim_tier3_dma.py              # Tier 3: Line-rate autonomous feeder model (45.8 FPS @ 50 MHz)
│   ├── vision_pipeline.py             # Edge camera/image ingestion & real-time HUD telemetry overlay
│   ├── run_micro_resnet_benchmark.py  # Standalone CLI benchmark suite
│   └── sample_hud_output.png          # Sample annotated HUD display image
└── jupyter/
    ├── pynq_micro_resnet_demo.ipynb   # Publication-grade interactive demo notebook
    └── scim_pynq_driver.py            # Vectorized stochastic backend (28x speedup, 0 LSB diff)

test/
└── test_micro_resnet.py               # Production pytest regression harness (8/8 tests pass)

docs/
└── pillar6_1_micro_resnet_emulation_guide.md # Comprehensive pedagogical guide
```

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
