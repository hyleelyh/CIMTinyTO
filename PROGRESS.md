# Project Progress: CIMTinyTO

## Last Execution Run: 2026-09-17 21:25
### [Built]
- `docs/pedagogical_rtl_review_roadmap.md`: Comprehensive 5-phase "Tour & Harden" pedagogical RTL review roadmap connecting Verilog constructs directly to standard-cell layouts, timing paths, dynamic power, and physical silicon failure modes.
- `docs/rtl_audit_and_poking_holes.md`: Comprehensive RTL audit documenting 6 subtle silicon failure modes, signed overflow edge cases, Mode 1 test coverage blindspots, and recommended defensive hardening patches.
- `src/lfsr8_galois.v`: Parameterized 8-bit Galois LFSR with GF(2) polynomial $x^8 + x^6 + x^5 + x^4 + 1$ (`8'hB8`), synchronous active-low reset, and zero-state lockup prevention.
- `src/scim_sng_bank.v`: 16-channel decorrelated SNG bank with stride-15 Galois trajectory offsets (`8'h5C`, `8'hF1`...) and digital magnitude comparators (`act >= lfsr`).
- `src/scim_pe.v`: Single-wire unified reconfigurable PE supporting Mode 0 (Unipolar AND), Mode 1 (Bipolar XNOR), and Mode 2 (Hybrid ReLU).
- `src/scim_compressor_42.v`: 4:2 carry-save compressor with $C_{\text{out}}$ independent of $C_{\text{in}}$ (zero horizontal carry ripple).
- `src/scim_wallace_tree.v`: 16-to-5 Wallace tree reduction using 4:2 compressors. Critical path $< 1.30\text{ ns}$ in Sky130.
- `src/scim_accumulator.v`: 13-bit signed two's complement saturating accumulator with sticky overflow detection.
- `src/scim_weight_mem.v`: 256-bit shift register weight matrix with MSB serial DFT loopback (`w_dout`).
- `src/tt_um_scim_core.v`: Top-level Tiny Tapeout macro wrapper implementing central shared activation tree ($\Delta = 2P - A$), FSM control, and multiplexed accumulator readback.
- `test/test_lfsr.py`: Cocotb unit test validating 255-state trajectory, wrap-around, and clock gating (**PASS**).
- `test/test_compressor.py`: Cocotb unit test verifying all 32 combinations of 4:2 compressor and 1,000 random patterns on 16-to-5 Wallace tree (**PASS**).
- `test/test_scim_core.py`: Cocotb end-to-end regression verifying 8/8 Gate 0 vectors with 100.00% bit-exact equivalence (**PASS**).
- `test/Makefile`: Automated simulation test harness for Icarus Verilog and Cocotb.

### [Architecture Decisions]
- **"Tour & Harden" Pedagogical Strategy:** Paired architectural walkthrough with in-line defensive hardening. The user explores the nominal silicon behavior of each submodule first, analyzes the physical failure mode, and applies the hardening patch in-place.
- **Unified Column Delta Reduction ($\Delta = 2P - A$):** Implemented single central 16-to-5 Wallace tree for activation sum $A = \sum a_i$, broadcast to 16 columns. Cut macro Wallace trees from 32 to 17, saving 15 full trees (~855 standard cells).
- **Single-Wire PE Output Interface:** PE outputs a single binary bit to column Wallace tree. Mode MUX select pin toggles at 0 Hz ($\alpha = 0$) during compute, consuming zero dynamic power.
- **Hardware Initial Seed Stride-15 Alignment:** Loaded Galois registers with hardware initial values `8'h5C`, `8'hF1`... at reset, matching cycle 0 of Python golden vectors bit-for-bit without runtime overhead.
- **13-Bit Saturating Precision:** Prevented wrap-around distortion during extreme saturation ($16 \times 256 = 4096$).
- **DFT Readback Loopback:** Reused serial weight shift chain with MSB `w_dout` to enable non-destructive weight verification over MISO with zero extra pins.

### [Current Pipeline State]
- **Pillar 1 (Gate 0) Fully Complete, Verified & Frozen.**
- **Pillar 2 (Gate 1 Parameterized Verilog RTL & Simulation): 100% COMPLETE & PASSING.**
  - Static linting: `verilator --lint-only -Wall` passed with **0 warnings and 0 errors**.
  - Submodule unit tests (`test_lfsr`, `test_compressor`, `test_wallace`): **ALL PASS**.
  - Master end-to-end regression (`test_scim_core`): **8/8 golden vectors PASS with 100.00% bit-exact equivalence**.

### [Next Steps: 5-Phase "Tour & Harden" Execution on Laptop]
1. **Phase 1 (Leaf Cells):** Review `src/scim_pe.v` and `src/scim_compressor_42.v` (connecting Verilog to transistor gates and zero-ripple $C_{\text{out}}$).
2. **Phase 2 (Spatial Reduction & Accumulation):** Review `src/scim_wallace_tree.v` and apply Hole #5 `$signed` patch in `src/scim_accumulator.v`.
3. **Phase 3 (Sequential Arrays & Memory):** Review `src/lfsr8_galois.v`, `src/scim_sng_bank.v`, and `src/scim_weight_mem.v` (DFF CIM bitcells & 256-cycle phase rolling).
4. **Phase 4 (Top-Level & Control):** Review `src/tt_um_scim_core.v` and apply Holes #1 (7-bit delta), #3 (2-stage reset synchronizer), and #4 (strobe mutual exclusion).
5. **Phase 5 (Verification Closure):** Expand `model/sim_scim.py` with 2 Mode 1 vectors (Hole #2), re-export golden JSON, and verify 10/10 tests in `test/test_scim_core.py`.
