<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

**CIMTinyTO** is an open-source standard-cell **Stochastic Compute-in-Memory (SCIM)** and **Digital Compute-in-Memory (DCIM)** accelerator macro fabricated on **SkyWater 130nm** (`sky130_fd_sc_hd`) in a $2\times 2$ tile footprint.

Standard analog CIM macros rely on custom analog SRAM bitcells, sensitive sense amplifiers, and power-hungry ADCs—components prone to PVT mismatch and incompatible with standard digital ASIC flows. CIMTinyTO eliminates all analog circuitry by combining:

1. **Stochastic Computing (SC):** Multi-bit integer multiplications are replaced by single-gate logical AND operations between unipolar stochastic bitstreams generated on-chip.
2. **Standard-Cell Weight Memory Fabric:** A 256-bit DFF memory array organized as a serial shift register with full Design-for-Testability (DFT) loopback (`w_dout`).
3. **Unified Column Delta Reduction:** Conventional bipolar CIM requires two separate Wallace trees per column to count positive and negative pulses ($16 \times 2 = 32$ trees), exceeding the Tiny Tapeout area limit. CIMTinyTO solves this by mathematically proving that:
   
   $$\Delta_{\text{col}} = 2 \cdot P_{\text{col}} - A$$

   where $P_{\text{col}}$ is the column pulse count and $A = \sum_{i=0}^{15} a_i$ is the active activation count, computed once by a single shared activation Wallace tree and broadcast to all 16 columns. This cuts macro tree count from 32 down to 17, saving 855 standard cells!
4. **16 Parallel Saturating Accumulators:** 13-bit signed accumulators with hardware clamping at $\pm 4095$ and a sticky overflow status flag.
5. **Silicon Hardening & Hole #8 Pad Quiescence:** During the 256-cycle compute phase, the output bus `uo_out` is clamped to `8'h00`, eliminating off-chip pad dynamic power ($<0.25\,\mu\text{W}$) and protecting on-chip power rails against $L \cdot di/dt$ ground bounce.

### Operating Modes
The accelerator natively supports two operating modes configured via `ui_in[4]` during a `ctrl_strobe` pulse:
* **Mode 0: Unipolar (`ui_in[4] = 0`):** Single AND gate PE ($W \in \{0, 1\}$, $X \in [0, 1] \implies \Delta = P$).
* **Mode 1: Hybrid ReLU (`ui_in[4] = 1`):** Single AND gate PE + Subtractor ($W \in \{-1, +1\}$, $X \in [0, 1] \implies \Delta = 2P - A$), enabling direct execution of quantized neural networks (Micro-ResNet).

---

## How to test

The chip operates with a 50 MHz master clock. An end-to-end $16 \times 16$ Matrix-Vector Multiply (MVM) sequence is executed as follows:

1. **Reset Initialization:** Assert `rst_n = 0` for at least 3 clock cycles to initialize the LFSR seeds and clear the accumulators.
2. **Weight Matrix Loading (256 Cycles):**
   * Set `uio[5]` (`w_shift_en`) = 1.
   * Clock in 256 weight bits serially via `uio[4]` (`w_din`).
   * Observe `uio[2]` (`w_dout`) to verify the scan chain continuity (DFT loopback).
   * Deassert `w_shift_en` = 0.
3. **Activation Loading (16 Writes):**
   * Apply an 8-bit activation byte on `ui_in[7:0]`.
   * Pulse `uio[6]` (`wr_act`) = 1 for 1 clock cycle.
   * Repeat 16 times; an internal counter automatically auto-increments the channel address from 0 to 15.
4. **Compute Triggering:**
   * Set `ui_in[4]` to select mode (0 = Unipolar, 1 = Hybrid ReLU).
   * Set `ui_in[2]` = 1 (`START_COMPUTE` command).
   * Pulse `uio[7]` (`ctrl_strobe`) = 1 for 1 clock cycle.
   * The core asserts `uio[0]` (`busy`) = 1 and computes for exactly 256 clock cycles.
5. **Accumulator Readback:**
   * After 256 cycles, `busy` drops to 0 and `uio[1]` (`done`) pulses high for 1 cycle.
   * Set `ui_in[3:0]` to the desired column index (0 to 15).
   * Set `ui_in[4]` = 0 to read the low byte (`uo_out[7:0] = acc[7:0]`).
   * Set `ui_in[4]` = 1 to read the high byte (`uo_out[7:0] = {{3{acc[12]}}, acc[12:8]}`).
   * Check `uio[3]` (`overflow`) to verify that no numerical saturation occurred.

---

## External hardware

* **Tiny Tapeout Carrier Board:** RP2040 or RP2350 carrier board running MicroPython or C firmware.
* **FPGA Testbench (Optional):** PYNQ-Z2 or DE10-Lite connected via PMOD for high-speed hardware-in-the-loop inference testing at 50–100 MHz.
* All I/O pins operate at standard 3.3V logic levels through the Tiny Tapeout pad frame.
