# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-04 15:20 (Run 52: COMPLETE 100% PILLAR 5 GLS & DYNAMIC POWER SIGN-OFF!)

### [Built]
- **`gds/tt_um_scim_core.v` / `gds/tt_um_scim_core.gds` / `gds/tt_um_scim_core.lef` / `gds/metrics.csv`:** Updated and synchronized with GitHub Actions Run #51 (`8378012`, Path B clean tapeout build with 1-bit mode and 256 single-gate AND PEs).
- **`test/gate_level_netlist.v`:** Synced to Run #51 post-layout gate-level netlist.
- **`scripts/gls_power_audit.py`:** Enhanced with automated 6-gate physical sign-off verification (`verify_gls_signoff`), automated `--check-signoff` CLI flag, and JSON metrics generation (`docs/pillar5_power_metrics.json`).
- **`test/Makefile`:** Added `gls_power_audit` target, added `waves_golden_vectors.vcd` generation for VCD-driven dynamic power analysis, and updated wave cleaning rules.
- **`.github/workflows/docs.yaml` & `docs/info.md`:** Added official Tiny Tapeout `ttsky26d` documentation build workflow and reformatted datasheet template for seamless PDF datasheet compilation (100% green on CI).
- **`docs/pillar5_gls_and_dynamic_power_signoff.md`:** Comprehensive sign-off report updated with Run #51 physical netlist metrics, VCD activity profiling, 6-gate physical sign-off scorecard, and silicon forensics.
- **`docs/walkthrough_pillar5_gls_power.md`:** Verification walkthrough updated with 11/11 GLS test results, power profiling breakdown, and reproduction commands.
- **`docs/pillar5_power_metrics.json`:** Structured JSON artifact containing exact dynamic switching power, energy-per-MAC, and hierarchical power domain breakdowns.

### [Architecture Decisions & Silicon Forensics]
- **Full Gate-Level Silicon Equivalence (11/11 PASS):**
  - All 10 golden model Gate-0 test vectors pass with 0 bit errors against the physical standard-cell netlist.
  - Constrained random verification (182 µs MVM stress), saturation/overflow clamping (+4095 clamp & sticky flag), DFT scan loopback (256-bit weight chain), and back-to-back inference pipelines verified on silicon gates.
  - Overclocking ladder passes cleanly through 80 MHz, 100 MHz, 125 MHz, 166 MHz, and 200 MHz in zero-delay gate simulation.
- **True VCD-Driven Dynamic Switching Power ($P_{\text{switch}}$):**
  - **$0.454\text{ mW}$** measured across 4,249 clock cycles of active MVM inference at $50\text{ MHz}, 1.80\text{V}$, compared to OpenROAD static STA estimate of $0.806\text{ mW}$ (a **$43.7\%$ dynamic power reduction**).
  - Physical origin: OpenROAD static STA assumes a pessimistic default switching activity factor ($\alpha = 0.1$ across all internal logic). In contrast, our stochastic compute-in-memory architecture leverages activation sparsity and unipolar zero-suppression, drastically reducing average node toggling.
- **Hierarchical Power Distribution:**
  - Clock Network: $0.264\text{ mW}$ ($58.2\%$ of dynamic switching), dominated by the global root buffer net `clknet_0_clk` ($88.23\text{ fF}, \alpha = 2.0$).
  - SNG LFSR Bank: $0.0156\text{ mW}$ ($3.44\%$).
  - PE Array ($16\times 16$ single-gate AND array): $0.0127\text{ mW}$ ($2.80\%$).
  - Accumulators ($16\times 13$-bit): $0.0114\text{ mW}$ ($2.52\%$).
  - Internal Cell Power: $2.441\text{ mW}$.
  - Leakage Power: $87.31\text{ nW}$ ($<0.01\%$).
  - Total Active Workload Power: **$2.895\text{ mW}$** ($\le 5.0\text{ mW}$ budget).
- **Energy Efficiency:**
  - Energy per $16\times 16$ MVM: **$14.82\text{ nJ}$**.
  - Energy per MAC: **$57.91\text{ pJ/MAC}$** (beating the $<100\text{ pJ/MAC}$ limit by $42\%$).
- **Hole #8 Pad Quiescence Verification:**
  - Output pads `uo_out` remain clamped at static `8'h00` during active compute (`!busy`).
  - Output pad dynamic switching power during compute is **$0.228\,\mu\text{W}$** ($\le 5.0\,\mu\text{W}$ limit), eliminating board-level capacitive pad charging ($\sim 5.45\text{ mW}$ at 15 pF pin load) and preventing $L \cdot di/dt$ ground bounce during computation.

### [Current Pipeline State]
- **Pillar 1 (Mathematical Modeling):** ✅ SIGNED OFF.
- **Pillar 2 (Verilog RTL & Verification):** ✅ SIGNED OFF (0 Verilator errors/warnings, strictly 0 RTL changes).
- **Pillar 3 (Physical ASIC Flow & Tapeout Hardening):** ✅ SIGNED OFF (GDSII clean, Magic/KLayout DRC 0, LVS 0).
- **Pillar 4 (Static Timing Analysis & PVT Sign-Off):** ✅ SIGNED OFF (All 9 PVT corners closed, 0 hold violations, 50 MHz closure).
- **Pillar 5 (Gate-Level Simulation & Dynamic Power Sign-Off):** ✅ **100% COMPLETE & SIGNED OFF!**
  - 11/11 GLS tests passed; 6/6 physical sign-off gates passed; VCD-driven dynamic power signed off at $2.895\text{ mW}$ and $57.91\text{ pJ/MAC}$.

### [Next Steps]
1. Transition to **Pillar 6: Pre-Silicon Emulation (FPGA Testbench)** in a **fresh chat session** per the Strict Single-Pillar Session Scope Directive.
