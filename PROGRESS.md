# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-06 20:35 (Run 55: Pillar 6 Emulation Architecture Planning & Hardware Matrix Finalization)

### [Built]
- **`PROGRESS.md` & `HANDOFF.md`:** Synchronized state for Pillar 6 pre-silicon emulation architecture and complete hardware accessories matrix.
- **`implementation_plan.md`:** Comprehensive design document establishing the dual-FPGA emulation architecture: PYNQ-Z2 AXI-Lite MMIO hardware bridge ($50\text{--}100\text{ MHz}$) and DE10-Lite tactile switch & 7-segment hex display console.

### [Architecture Decisions & Silicon Forensics]
- **Hardware Cabling & Instrumentation Bill of Materials (BOM):**
  - **Bench DC Power:** Korad KA3005P linear supply to PYNQ-Z2 using $4\text{ mm}$ Banana $\rightarrow$ $5.5\times 2.1\text{ mm}$ DC barrel plug ($18\text{ AWG}$, Center-Positive, preset to $12.00\text{V}$, $2.20\text{A}$ OCP, $13.00\text{V}$ OVP).
  - **Edge Vision Camera Interconnect:** Validated native compatibility of existing **Raspberry Pi Camera Module v2 NoIR** (Sony IMX219) with Raspberry Pi 5 via 22-pin ($0.5\text{ mm}$ pitch) $\rightarrow$ 15-pin ($1.0\text{ mm}$ pitch) adapter ribbon cable. Delivers high-contrast infrared/grayscale edge features for the 12.5 FPS Micro-ResNet pipeline.
  - **Signal Forensics & Bus Sniffing:** Established **DSLogic Plus (16-channel, 400 MSa/s)** as primary analyzer for full 8-bit accumulator output bus (`uo_out[7:0]`) + control flag inspection, and **HiLetgo 24M 8CH** as low-cost bus sniffer.
  - **5V Electrical Destruction Guardrail:** Selected **TXS0108E** 8-channel auto-sensing bidirectional level shifter ($V_{CCA}=3.3\text{V} \le V_{CCB}=5.0\text{V}$) for Arduino Uno R3 testing, preventing dielectric oxide breakdown on Sky130 pads.
- **Pillar 6 FPGA Architecture Roadmap:**
  - **Component 1 (PYNQ-Z2):** Memory-Mapped AXI-Lite register bridge (`tt_scim_axi_wrapper.v`) exposing `ui_in`, `uo_out`, `uio_in`, `uio_out` to Python Jupyter via `/dev/mem` MMIO, with single-step software clock and free-running $50\text{ MHz}$ PLL modes.
  - **Component 2 (DE10-Lite):** Pure RTL console (`de10_lite_top.v`) mapping 10 slide switches to input activations/control bits, pushbuttons to debounced single-clock pulses, and four 7-segment displays to real-time 13-bit signed accumulator hex values.

### [Current Pipeline State]
- **Pillars 1–5:** ✅ 100% COMPLETE, SIGNED OFF & FROZEN.
- **Tiny Tapeout SKY 26d Submission:** ✅ SUBMITTED & VERIFIED (PR #85 green).
- **Pillar 6 (Pre-Silicon Emulation):** 🚀 **ACTIVE / IN PROGRESS.**
  - Hardware power cabling and bench accessories defined.
  - Implementation Plan submitted and pending user review tomorrow.

### [Next Steps]
1. Receive user review/approval on [`implementation_plan.md`](file:///home/juliusli/.gemini/antigravity/brain/b7f6544b-fb70-432c-8eaf-25c7dba027c6/implementation_plan.md) on Laptop (`juliusli-MSI`).
2. Implement and lint `fpga/pynq_z2/rtl/tt_scim_axi_wrapper.v`.
3. Implement `fpga/de10_lite/rtl/de10_lite_top.v` and 7-segment hex decoder.
4. Build Icarus Verilog / Cocotb simulation testbench verifying the AXI MMIO register bridge prior to FPGA synthesis.
