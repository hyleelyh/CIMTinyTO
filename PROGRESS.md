# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-07 08:34 (Run 56: Pillar 6 Architecture Review, Workstation Roles & FPGA Trade-Off Alignment)

### [Built]
- **`.agents/skills/lab-hardware-inventory/SKILL.md` & `AGENTS.md`:** Added Section 0 formally establishing the Desktop PC as the primary bring-up platform and the Laptop as the reviewing/planning/learning platform for Pillar 6.
- **`.device_profile`:** Created local device profile identifying `juliusli-MSI` as the Laptop and recording its specific role.
- **`HANDOFF.md` & `PROGRESS.md`:** Synchronized state for Pillar 6 pre-silicon emulation architecture, workstation role division, and implementation plan review.

### [Architecture Decisions & Silicon Forensics]
- **Workstation Roles in Emulation & Bring-Up:**
  - **Desktop PC (`juliusli`):** Primary bring-up platform for Pillar 6 hardware execution. Collocated with Korad KA3005P linear power supply, PYNQ-Z2, DE10-Lite, DSLogic Plus analyzer, breadboards, and dedicated AC outlets; provides superior compute/memory for Vivado/Quartus synthesis and live JTAG programming.
  - **Laptop (`juliusli-MSI`):** Reviewing work, planning, architecture study, and learning from Pillar 6 activities. Testing or hardware debugging on the laptop occurs only when explicitly called out by the user.
- **Pre-Tapeout 50-Day Strategy & FPGA vs. ASIC Physical Trade-Offs:**
  - **Selected Option 1:** Keep the physical SkyWater 130nm ASIC RTL strictly frozen to protect zero-hold-violation timing closure ($+120\text{ ps}$ slack) and $64.5\%$ standard-cell density.
  - **Emulation Scope:** FPGA emulation validates cycle-accurate logical FSM transitions, math parity, and host software/driver integration at $50\text{--}100\text{ MHz}$, while ASIC transistor physics, wire parasitics, and true power are signed off via STA/GLS.
  - **The "FPGA Silicon Tax" vs. Custom Silicon:** FPGA requires $\sim 1,000$ transistors (LUT6 + SRAM bits) to emulate a single 2-input AND gate that takes 4 discrete transistors in Sky130 standard cells. The custom ASIC achieves a $1,000\times$ power reduction ($2.895\text{ mW}$ vs $2.5\text{W}$ on Zynq), enabling 10 days of continuous operation on a CR2032 coin cell vs 15 minutes on FPGA.
- **Pillar 6 FPGA Architecture Roadmap:**
  - **Component 1 (PYNQ-Z2):** Memory-Mapped AXI-Lite register bridge (`tt_scim_axi_wrapper.v`) exposing `ui_in`, `uo_out`, `uio_in`, `uio_out` to Python Jupyter via `/dev/mem` MMIO, with single-step software clock and free-running $50\text{ MHz}$ PLL modes.
  - **Component 2 (DE10-Lite):** Pure RTL console (`de10_lite_top.v`) mapping 10 slide switches to input activations/control bits, pushbuttons to debounced single-clock pulses, and four 7-segment displays to real-time 13-bit signed accumulator hex values.

### [Current Pipeline State]
- **Pillars 1–5:** ✅ 100% COMPLETE, SIGNED OFF & FROZEN.
- **Tiny Tapeout SKY 26d Submission:** ✅ SUBMITTED & VERIFIED (PR #85 green).
- **Pillar 6 (Pre-Silicon Emulation):** 🚀 **ACTIVE / IN PROGRESS.**
  - Implementation Plan reviewed on Laptop; Option 1 approved.
  - Workstation roles (PC vs Laptop) and device profiles finalized.

### [Next Steps]
1. Implement `fpga/pynq_z2/rtl/tt_scim_axi_wrapper.v` (AXI4-Lite slave bridge for ARM PS MMIO).
2. Create `test/tb_fpga_axi.v` and Cocotb testbench to verify AXI MMIO read/write cycles and cycle latency counter.
3. Implement `fpga/de10_lite/rtl/de10_lite_top.v`, debouncer, and 7-segment hex display decoder.

