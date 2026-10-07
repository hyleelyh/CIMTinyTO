# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-07 07:58 (Run 56: Pillar 6 Workstation Roles & Emulation Matrix Formalization)

### [Built]
- **`.agents/skills/lab-hardware-inventory/SKILL.md` & `AGENTS.md`:** Added Section 0 formally establishing the Desktop PC as the primary bring-up platform and the Laptop as the reviewing/planning/learning platform for Pillar 6.
- **`.device_profile`:** Created local device profile identifying `juliusli-MSI` as the Laptop and recording its specific role.
- **`HANDOFF.md` & `PROGRESS.md`:** Synchronized state for Pillar 6 pre-silicon emulation architecture and workstation role division.

### [Architecture Decisions & Silicon Forensics]
- **Workstation Roles in Emulation & Bring-Up:**
  - **Desktop PC (`juliusli`):** Primary bring-up platform for Pillar 6 hardware execution. Collocated with Korad KA3005P linear power supply, PYNQ-Z2, DE10-Lite, DSLogic Plus analyzer, breadboards, and dedicated AC outlets; provides superior compute/memory for Vivado/Quartus synthesis and live JTAG programming.
  - **Laptop (`juliusli-MSI`):** Reviewing work, planning, architecture study, and learning from Pillar 6 activities. Testing or hardware debugging on the laptop occurs only when explicitly called out by the user.
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
