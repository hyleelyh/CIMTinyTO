# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-03 13:10 (Run 36 Diagnostic & Path B Architectural Synthesis)

### [Built, Verified & Archived]
- **Permanent Archive of Sept 23 OpenLane 2 Sign-Off Created:**
  - Preserved the full September 23 golden milestone (100% clean DRC/LVS, original 4:2 compressor tree, 14-bit comparators).
  - Pushed permanent Git Tag: `v-sept23-openlane2-signoff` (commit `1525ffd`).
  - Pushed permanent Git Branch: `archive/sept23-openlane2-signoff`.
  - Created standalone archive directory: `archive/sept23_openlane2_golden/` containing:
    - `gds/tt_um_scim_core.gds` (16.15 MB binary layout)
    - `gds/tt_um_scim_core.lef` (Macro abstract LEF)
    - `gds/tt_um_scim_core.v` (Gate-level netlist)
    - `gds/metrics.csv` & `sky130.lyp`
    - All original synthesizable Verilog source files in `src/`
    - `README.md` with step-by-step instructions for post-tapeout KLayout overlay comparison.
- **Run #36 Diagnostic Analysis:**
  - Evaluated the 4.5+ hour runtime of Run #36 on GitHub Actions.
  - Identified the root causes:
    1. *Syntax Mismatch in LibreLane 3:* `GRT_LAYER_ADJUSTMENTS` in LibreLane/Pydantic step architecture expects a dictionary mapping (`{"met1": 0.99, ...}`) rather than a list (`[0.99, ...]`). The list format was silently treated as `None` (0% derating), causing FastRoute to dump the same 84,000 µm on `met1` and triggering stubborn tiles maze routing.
    2. *Congestion Overload:* Evicting nets from `met1` while keeping the full 3-mode design (256 XNORs, 256 MUXes, 256 mode wires) caused track congestion on `met2`/`met3`.
- **Created Comprehensive Walkthrough Artifact:**
  - Generated `walkthrough.md` documenting the 98% -> 72% density optimization, accumulator sign-bit overflow recoding, balanced binary adder tree, and explicit penalty highlights.
- **Exhaustive Formal Verification Completed:**
  - Wallace tree: 65,536 / 65,536 patterns PASS (0 errors).
  - Accumulator sign-bit overflow: 270,336 / 270,336 combinations PASS (0 errors).
  - Cocotb regression suite: 11/11 test suites PASS in 1.73s.
  - Gate-level simulation: 11/11 test suites PASS on Sky130 standard cells in 9.46s (including 200 MHz overclocking).

### [Architecture Decision: Path B "Best of Both Worlds"]
- Agreed to eliminate Mode 1 (Bipolar Mode) to fund the return of the original 4:2 compressor Wallace tree:
  1. **Mode 1 Removal:** Mode 2 (Hybrid ReLU) already handles signed weights for deep learning (ResNets). Deleting Mode 1 eliminates 256 XNOR gates and 256 MUXes across all 256 PEs, freeing 528 standard cells (~3,820 µm²) and 256 global mode routing nets.
  2. **Reinstate 4:2 Compressor Wallace Tree:** Brings back the original logarithmic reduction tree (`scim_compressor_42.v`), which actually uses ~200 fewer cells than the binary adder tree (~800 µm² savings).
  3. **Keep 2-Gate Sign-Bit Saturation:** Retains the 1,120-cell (~4,800 µm²) savings over 14-bit ripple comparators with zero SEU penalty.
  4. **Golden Density (64.5%):** Total cell area drops to ~47,400 µm² (density ~64.5%), opening 35.5% whitespace for effortless TritonRoute convergence (< 15 mins) and massive decoupling capacitor (`DECAP_CELL`) filling.

### [Current Pipeline State]
- **Sept 23 Golden Archive:** 100% PRESERVED, TAGGED, AND PUSHED.
- **Active Branch `test/option2-recoded`:** Diagnostic complete, synchronized, and clean.
- **Target Shuttle:** Tiny Tapeout `ttsky26d` (requires `TinyTapeout/tt-gds-action@ttsky26d`).
- **Next Operational Phase:** Launch Path B implementation on a dedicated clean branch in a fresh chat session.

### [Next Steps for Fresh Chat Session]
1. Open a **fresh chat session** per the Single-Pillar Session Scope Directive.
2. Branch `test/path-b-streamlined` from `main` (which already contains the original 4:2 compressor tree).
3. Implement Path B in `src/scim_pe.v`, `src/scim_accumulator.v`, and `src/tt_um_scim_core.v`.
4. Update `src/config.json` with the dictionary syntax:
   `"GRT_LAYER_ADJUSTMENTS": {"met1": 0.99, "met2": 0.0, "met3": 0.0, "met4": 0.0}` and `PL_TARGET_DENSITY_PCT: 65`.
5. Run the 40-second local automated verification suite (`sim_scim.py` + Cocotb + GLS).
6. Push to `test/path-b-streamlined` to dispatch the clean, fast (<20 min) GDS build on `ttsky26d`.
