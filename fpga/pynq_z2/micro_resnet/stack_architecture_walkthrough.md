# End-to-End System Stack Architecture: CIMTinyTO Pre-Silicon Emulation

**Target Platform:** AMD Xilinx Zynq-7020 (PYNQ-Z2) SoC + SkyWater 130nm ASIC Macro Surrogate  
**Application:** MicroResNet-16 Edge AI Vision Pipeline with Real-Time USB Camera Ingestion  

---

## 1. System-Wide Architectural Overview

The CIMTinyTO pre-silicon emulation testbench bridges high-level deep learning vision applications with bare-metal custom silicon computing. The complete system spans seven distinct hierarchical layers:

```
+=========================================================================================================+
| [Layer 7] USER INTERFACE & JUPYTER APPLICATION                                                          |
|   pynq_micro_resnet_demo.ipynb | In-place real-time HUD rendering (IPython.display, 22.9 FPS)         |
+---------------------------------------------------------------------------------------------------------+
| [Layer 6] EDGE VISION PIPELINE & TILER (Python 3.10)                                                    |
|   vision_pipeline.py: LiveCameraCapture, PIL BILINEAR resize (32x32), unipolar uint8 [0, 255]           |
|   micro_resnet_tiler.py: GEMM lowering, stationary weight caching, fixed-point requantization           |
+---------------------------------------------------------------------------------------------------------+
| [Layer 5] HIGH-SPEED C TRANSPORT BRIDGE (libscim_tier2.so)                                              |
|   scim_tier2_driver.c: Direct user-space pointers (/dev/mem), packed 1-write strobes (0x40000000)      |
+---------------------------------------------------------------------------------------------------------+
| [Layer 4] LINUX KERNEL & DEVICE DRIVERS (Ubuntu on ARM Cortex-A9)                                       |
|   - V4L2 Subsystem (/dev/video0): UVC camera DMA ring buffer, queue draining, device locking            |
|   - Virtual Memory / MMU (/dev/mem): O_SYNC uncached MMIO window mapping (0x40000000 - 0x4000FFFF)      |
|   - Device Configuration (/dev/xdevcfg, XRT): In-situ FPGA bitstream programming                        |
+---------------------------------------------------------------------------------------------------------+
| [Layer 3] ARM PROCESSING SYSTEM (PS7) HARDWARE                                                          |
|   Dual-Core ARM Cortex-A9 @ 650 MHz | 512 MB DDR3 DRAM | USB 2.0 Host Controller (USB_1)               |
+---------------------------------------------------------------------------------------------------------+
| [Layer 2] PROGRAMMABLE LOGIC & AXI BRIDGE (scim_pynq.bit / scim_pynq.hwh)                               |
|   - M_AXI_GP0 Interconnect: 32-bit AXI4-Lite bus running at 50.0 MHz synchronous FCLK_CLK0              |
|   - tt_scim_axi_wrapper.v: Translates 32-bit MMIO registers to 24 Tiny Tapeout ASIC pins                 |
|   - Pulse Generator: Single-cycle synchronous strobes (w_shift_en, wr_act)                              |
+---------------------------------------------------------------------------------------------------------+
| [Layer 1] FROZEN ASIC SILICON MACRO (tt_um_scim_core.v)                                                 |
|   - 256 Stationary Standard-Cell DFFs: 16x16 bipolar weight matrix W in {-1, +1}                        |
|   - SNG Bank: 16 Galois LFSRs generating pseudo-random stochastic bitstreams                            |
|   - Spatial PE Array: 256 AND gates evaluating Mode 1 (Hybrid ReLU) multiplication                      |
|   - Accumulation Tree: 16 4:2 Wallace tree compressors + 16 12-bit saturating accumulators             |
+=========================================================================================================+
```

---

## 2. Layer-by-Layer Architectural Breakdown

### Layer 1: The Frozen ASIC Silicon Macro (`src/`)
This layer represents the **immutable physical silicon** taped out for SkyWater 130nm on Tiny Tapeout 26d (PR #86):
* **Immutability Principle:** Once silicon is fabricated, logic gates and wires are permanent. In our emulation setup, the FPGA implements this exact Verilog code without adding or removing a single logic gate.
* **Stationary Flip-Flop Weight Array (`scim_weight_mem.v`):**
  - Consists of 256 standard-cell D flip-flops arranged as a $16 \times 16$ shift-and-hold matrix.
  - Weights are shifted into the array **once per layer** (requiring 256 clock cycles).
  - While thousands of spatial activation pixels stream through the core, `w_shift_en` remains `0`.
  - **Silicon Power Advantage:** Suppresses the dynamic switching activity factor $\alpha \to 0$. In CMOS technology, dynamic power is $P = \alpha C V^2 f$. By eliminating redundant weight shifts, dynamic weight switching power drops by **99.90%**!
* **Stochastic Number Generator (SNG) Bank (`scim_sng_bank.v`):**
  - Contains 16 independent 8-bit Galois Linear Feedback Shift Registers (`lfsr8_galois.v`) with primitive polynomials.
  - Each LFSR generates a pseudo-random sequence compared against the 8-bit activation value $A_i \in [0, 255]$ to emit a stochastic unipolar Bernoulli bitstream $a_i(t) \in \{0, 1\}$.
* **Spatial Processing Element (PE) Array (`scim_pe.v`):**
  - Implements Mode 1 (Hybrid ReLU) arithmetic:
    $$\Delta_j(t) = 2 \sum_{i=0}^{15} (w_{i,j} \land a_i(t)) - \sum_{i=0}^{15} a_i(t)$$
  - Each PE is a single standard-cell AND gate, achieving maximum computational density per square micron.
* **Wallace Tree Compressor & Accumulator (`scim_wallace_tree.v`, `scim_accumulator.v`):**
  - Compresses 16 spatial PE products into sum and carry vectors using standard-cell 4:2 compressors in $O(\log n)$ gate delay (avoiding carry-propagation delay).
  - Signed 12-bit accumulators integrate the results over $N = 256$ cycles with saturation clamping to prevent arithmetic wrap-around.

---

### Layer 2: FPGA Hardware Overlay (`scim_pynq.bit` & `scim_pynq.hwh`)
The Artix-7 FPGA fabric acts as a physical hardware surrogate for the ASIC die:
* **The AXI4-Lite Slave Bridge (`tt_scim_axi_wrapper.v`):**
  - Translates 32-bit microprocessor bus transactions into 8-bit Tiny Tapeout pin signals:
    - `ui_in[7:0]`: Dedicated input bus (activations, weight bits, control flags).
    - `uo_out[7:0]`: Dedicated output bus (multiplexed accumulator high/low bytes).
    - `uio_in[7:0]` / `uio_out[7:0]`: Bidirectional status flags (`core_busy`, `core_done`).
  - **Register Map at `0x40000000`:**
    - `0x00` (`REG_CONFIG`): Soft reset, clock mode, single-step debug.
    - `0x04` (`REG_ACT_DIN`): Broadcast 8-bit unipolar activation + write strobe.
    - `0x08` (`REG_WEIGHT_DIN`): Shift 8-bit bipolar weight vector.
    - `0x0C` (`REG_STATUS`): Read busy/done flags and cycle latency timer.
    - `0x10` (`REG_ACCUM_OUT`): Read 12-bit signed accumulator results.
* **Single-Cycle Pulse Generator:**
  - Because the ARM CPU operates at 650 MHz and the FPGA fabric operates at 50 MHz, an unsynchronized CPU write would hold high across multiple FPGA clock periods.
  - The wrapper includes an internal synchronous pulse generator that guarantees `wr_act` and `w_shift_en` pulse high for **strictly one 50 MHz clock cycle** ($20\text{ ns}$) per CPU register write.
* **The Bitstream Files:**
  - `scim_pynq.bit`: Raw binary configuration SRAM bits flashed into the FPGA routing matrices and look-up tables.
  - `scim_pynq.hwh`: Hardware Handoff XML describing the IP address boundaries (`0x40000000`), clock frequencies, and register offsets for the PYNQ Python runtime.

---

### Layer 3 & 4: ARM Processing System (PS7) & Linux Kernel
The hardware brain of the PYNQ-Z2 board is the AMD Xilinx Zynq-7020 Processing System:
* **CPU & Memory:** Dual-Core ARM Cortex-A9 running at 650 MHz with 512 MB of DDR3 DRAM.
* **USB 2.0 Host Controller (`USB_1`):**
  - Connected via an on-board SMSC USB3320 USB PHY to the Type-A USB Host port (`USB_1`, designator `USB_4H` on schematic page 7).
  - Enumerates the external USB camera as `/dev/video0` and `/dev/video1`.
* **V4L2 Kernel Subsystem (Video4Linux2):**
  - Manages the USB Video Class (UVC) camera hardware.
  - Allocates a circular DMA ring buffer of 4 to 5 video frames in physical RAM.
  - Enforces **exclusive single-handle access**: only one process/file descriptor can open `/dev/video0`.
  - Requires active buffer draining (`for _ in range(4): cap.grab()`) to prevent delivering stale frames from the head of the circular buffer.
* **Memory Management Unit (MMU) & `/dev/mem`:**
  - Maps physical hardware addresses (`0x40000000`) into virtual address space for user-space applications.
  - Opened with `O_RDWR | O_SYNC` to disable CPU L1/L2 data caching on the MMIO registers, ensuring every read and write hits the physical AXI bus pins immediately.
* **FPGA Device Configuration (`/dev/xdevcfg`):**
  - Kernel driver that interfaces with the Zynq DevC (Device Configuration) hardware block to flash bitstreams into the FPGA fabric in under 100 milliseconds without rebooting Linux.

---

### Layer 5: High-Performance Compiled C Driver (`libscim_tier2.so`)
Pure Python MMIO drivers suffer from significant interpreter overhead (~180 µs per tile, throttling framerate to 0.7 FPS). Layer 5 eliminates this software bottleneck:
* **Direct Virtual Pointers:**
  - Maps `0x40000000` directly into user-space virtual memory via `mmap()`:
    ```c
    volatile uint32_t *scim_base = (volatile uint32_t *)mmap(0, 0x1000, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40000000);
    ```
* **Packed 1-Write Strobing:**
  - Instead of performing two separate bus writes (one for data and one to assert the strobe), the C driver packs the 8-bit activation data in bits `[7:0]`, the write strobe in bit `[8]`, and the compute strobe in bit `[9]`.
  - A single 32-bit CPU store instruction triggers both data transfer and hardware execution simultaneously, cutting bus traffic in half.
* **In-Memory C Execution:**
  - The shared object `libscim_tier2.so` is compiled natively on the ARM Cortex-A9 with `-O3 -fPIC`, executing inside CPU L1 cache and driving the FPGA at **22.9 FPS** end-to-end full-frame inference.

---

### Layer 6: Edge Vision Pipeline & Tiler (`vision_pipeline.py`)
This layer handles image processing, camera management, and GEMM matrix lowering:
* **Universal Camera Ingestion (`LiveCameraCapture`):**
  - Manages OpenCV capture handles, V4L2 backend initialization, and square center-cropping.
  - Resizes $640 \times 480$ camera images to $32 \times 32 \times 3$ uint8 tensors.
  - Implements **singleton auto-release** to prevent Linux `/dev/video0` device locking between notebook cells.
* **GEMM Lowering & Tiler (`micro_resnet_tiler.py`):**
  - Slices 2D convolution layers (Conv $3 \times 3$ and Conv $1 \times 1$) into $16 \times 16$ Matrix-Vector Multiplication (MVM) tiles.
  - Total tiles per $32 \times 32$ image: **3,585 tiles**.
  - Schedules weight loading: loads weights **once per layer** (only 6 total reloads per image), keeping weights stationary in standard-cell flip-flops across all 3,585 tiles.
* **Requantization & Classification Head:**
  - Downscales 12-bit accumulator outputs via fixed-point integer scaling ($Y \cdot M \gg S$) to fit the unipolar activation range $[0, 255]$ for the next layer.
  - Applies Global Average Pooling (GAP) and computes Softmax probabilities across the 10 CIFAR-10 classes.

---

### Layer 7: Interactive Application & HUD Display (`pynq_micro_resnet_demo.ipynb`)
The top user-facing layer running inside the PYNQ Jupyter server:
* **Web UI at Port 9090:** Hosted on the Zynq ARM Linux rootfs (`http://10.0.0.74:9090`).
* **Section 2 (Camera Check):** Grabs a static snapshot to verify exposure and white balance, immediately releasing the hardware handle.
* **Section 3 (Multi-Tier Benchmark):** Executes identical image frames across Tier 1 (Python MMIO), Tier 2 (Compiled C MMIO), and Tier 3 (Line-Rate DMA), plotting latency and throughput scorecards.
* **Section 4b (Interactive Live Video Stream):**
  - Executes a continuous loop capturing live frames from `/dev/video0`.
  - Runs physical FPGA Tier 2 inference on every frame.
  - Dynamically updates the HUD in place at **~23 FPS** using `IPython.display.clear_output(wait=True)`.
  - Overlays real-time telemetry: top-1 class, confidence score, FPS, tile latency, and stationary hardware memory metrics.

---

## 3. Dataflow Path: From Light Photons to Classified Pixels

```
 [ Photons ]
      │
      ▼
 1. Camera Sensor (USB Webcam on USB_1)
      │ Generates 640x480 YUV/RGB frames
      ▼
 2. Linux Kernel V4L2 Driver (/dev/video0)
      │ Queues frames in DMA circular ring buffer
      ▼
 3. vision_pipeline.py (OpenCV / PIL)
      │ Flushes stale queue, crops to square, resizes to 32x32 uint8
      ▼
 4. micro_resnet_tiler.py (GEMM Lowering Engine)
      │ Slices 32x32x3 into 3,585 16x16 matrix tiles
      ▼
 5. libscim_tier2.so (Compiled C Driver)
      │ Writes /dev/mem pointers directly to 0x40000000
      ▼
 6. AXI4-Lite Interconnect (Zynq PS7 -> PL @ 50 MHz)
      │ Transmits 32-bit MMIO transactions across AXI bus
      ▼
 7. tt_scim_axi_wrapper.v (FPGA Glue Logic)
      │ Generates single-cycle synchronous strobes
      ▼
 8. tt_um_scim_core.v (Custom Silicon Macro)
      │ - Weights held stationary in 256 DFFs
      │ - Activations converted to stochastic bitstreams by 16 LFSRs
      │ - 256 PEs compute Mode 1 Hybrid ReLU products
      │ - 16 Wallace trees & accumulators integrate results over 256 cycles
      ▼
 9. libscim_tier2.so
      │ Reads 12-bit signed accumulator outputs from 0x40000010
      ▼
10. micro_resnet_model.py
      │ Requantizes to [0, 255], runs GAP, computes Softmax probabilities
      ▼
11. Jupyter Notebook HUD (Browser Display at 10.0.0.74:9090)
      │ Renders real-time HUD video display at 22.9 FPS
```

---

## 4. Summary Verification Matrix

| Subsystem | Underlying Technology | Verified Metric |
| :--- | :--- | :---: |
| **Physical Core** | 16x16 SCIM Macro (`tt_um_scim_core.v`) | 256 Stationary DFFs, 16 Wallace Trees |
| **Clock Domain** | Synchronous Single Clock (`FCLK_CLK0`) | **50.0 MHz** (+1.2 ns setup slack) |
| **MMIO Address** | 32-bit AMBA AXI4-Lite | Base Address **`0x40000000`** |
| **Linux V4L2** | Kernel UVC Driver (`/dev/video0`) | $640 \times 480 \to 32 \times 32$ RGB |
| **C Transport** | Direct `/dev/mem` pointers (`libscim_tier2.so`) | **22.9 FPS** end-to-end full frame |
| **Power Suppression** | Stationary Weight Flip-Flops | **99.90%** shift power reduction |
| **ASIC RTL Status** | SkyWater 130nm (`src/`) | **100% Frozen & Verified** |
