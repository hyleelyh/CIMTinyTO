# Session Handoff: Pillar 6 Pre-Silicon Emulation Kickoff & Power Hardware Setup

- **Date:** 2026-10-05 22:05
- **Machine:** Host/PC (`juliusli`)
- **Active Branch:** `main`
- **Active Phase:** **PILLAR 6: PRE-SILICON EMULATION (FPGA TESTBENCH)**
- **Hardware Status:** PYNQ-Z2 & DE10-Lite power, boot jumpers, and Korad KA3005P safety presets established.

---

## Pillar 6 Hardware Bench Configuration

| Platform | Power Method | Safety Preset / Jumper | Logic Level | Verification Role |
| :--- | :--- | :--- | :--- | :--- |
| **PYNQ-Z2** (Zynq-7020) | Korad KA3005P Linear DC Supply | $12.00\text{V}$, $2.20\text{A}$ OCP, $13.00\text{V}$ OVP, `JP5` = `REG`, `JP1` = `SD` | $+3.3\text{V}$ LVCMOS | 50–100 MHz MMIO bit-exact MVM regressions & Jupyter testbench |
| **DE10-Lite** (MAX 10) | USB Type-B (PC Port) | Standard USB Bus ($5\text{V} / 500\text{ mA}$ limit) | $+3.3\text{V}$ LVCMOS | Tactile switch input & 7-segment hex accumulator monitoring |

---

## Next Steps for Pillar 6 Execution

1. Build Vivado synthesis flow for `src/tt_um_scim_core.v` targeting Zynq-7020 (`xc7z020clg400-1`).
2. Implement AXI-Lite MMIO register bridge wrapping the Tiny Tapeout 8-bit bidirectional pin interface (`ui_in`, `uo_out`, `uio_in`, `uio_out`).
3. Connect PYNQ Jupyter environment to execute bit-exact validation against Gate-0 golden test vectors.
