# Session Handoff: Path B Transition & Fresh Chat Launch

- **Date:** 2026-10-03 13:10
- **Machine:** Host/PC (`juliusli`)
- **Current Branch:** `test/option2-recoded` (Synchronized, clean)
- **Sept 23 Golden Archive:** Tagged at `v-sept23-openlane2-signoff`, branch `archive/sept23-openlane2-signoff`, and committed in `archive/sept23_openlane2_golden/`.
- **Target Branch for Next Session:** `test/path-b-streamlined` (branch directly from `main`).

---

## Executive Summary & Diagnostic Findings

1. **Run #36 Diagnostic:**
   - Run #36 exceeded 4.5 hours in `Build GDS via OpenLane 2`.
   - **Root Cause Identified:**
     - LibreLane 3 / OpenLane 2 Pydantic schema expects `GRT_LAYER_ADJUSTMENTS` as a `Dict[str, float]` (`{"met1": 0.99, ...}`).
     - In Run #36, passing an array `[0.99, 0, 0, 0, 0, 0]` caused LibreLane's step parser to silently drop the parameter and default to `None` (0% derating), causing FastRoute to dump 84,000 µm on `met1` and triggering stubborn tiles maze routing in TritonRoute.
   - User should cancel Run #36 on GitHub Actions UI to free the runner.

2. **Architectural Decision: Path B "Best of Both Worlds"**:
   - Instead of microarchitectural compromises, we deploy **Path B**:
     * **Remove Mode 1 (Bipolar Mode):** Deletes 256 XNORs and 256 PE MUXes (saves 528 cells, ~3,820 µm²). Each PE becomes a pure 2-input AND gate with zero MUX overhead. Mode 2 (Hybrid ReLU) retains 100% of our targeted signed-weight deep learning inference capability.
     * **Reinstate 4:2 Compressor Wallace Tree:** Restores the original fast logarithmic reduction tree (`scim_compressor_42.v`), which actually uses ~200 fewer cells than the binary adder tree (~800 µm² savings).
     * **Keep 2-Gate Sign-Bit Saturation:** Retains the 1,120-cell (~4,800 µm²) savings over 14-bit ripple comparators with superior radiation hardness.
     * **Target Density ~64.5% (~47,400 µm² core cell area):** The golden sweet spot for standard-cell ASICs, providing 35.5% open whitespace for effortless TritonRoute convergence (< 15 mins) and massive decoupling capacitor (`DECAP_CELL`) arrays.

---

## Instructions for the Fresh Chat Session

When opening the new chat session:

1. **Create and Switch to the New Clean Branch:**
   ```bash
   git checkout -b test/path-b-streamlined main
   ```
   *(Note: Branching from `main` is optimal because `main` already contains the original `scim_wallace_tree.v` and `scim_compressor_42.v`!)*

2. **Implement Path B:**
   - **`src/scim_pe.v`:** Simplify to pure 2-input AND gate:
     ```verilog
     assign pe_out = act_bit & weight_bit;
     ```
   - **`src/scim_accumulator.v`:** Apply the 2-gate sign-bit overflow check (`pos_overflow = ~sum_ext[13] & sum_ext[12]`).
   - **`src/tt_um_scim_core.v`:** Simplify the column delta logic to Mode 0 (Unipolar) and Mode 2 (Hybrid ReLU).
   - **`src/config.json`:** Set:
     - `"PL_TARGET_DENSITY_PCT": 65`
     - `"GRT_LAYER_ADJUSTMENTS": {"met1": 0.99, "met2": 0.0, "met3": 0.0, "met4": 0.0}`
     - `"ROUTING_CORES": 2`
     - Ensure official `ttsky26d` margins and decap arrays are active.

3. **Run the 40-Second Automated Regression Loop:**
   - `python3 model/sim_scim.py` (Pillar 1 Gate 0)
   - `make -C test test_all` (Pillar 2 Gate 1 Cocotb)
   - `make -C test test_gls` (Pillar 5 Gate-Level Simulation)

4. **Push and Dispatch:**
   - Push to `origin/test/path-b-streamlined` to trigger the fast, clean GDS build on `ttsky26d`.
