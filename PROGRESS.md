# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-03 15:20 (Branch Inception: test/path-b-streamlined for Mode 1 Removal & Clean 4:2 Compressor Sign-Off)

### [Built & Dispatched]
- **Created & Pushed Branch:** `test/path-b-streamlined` branched directly from `main` to implement **Path B**.
- **Sept 23 Sign-off Golden Archive Preserved:**
  - Git Tag: `v-sept23-openlane2-signoff`
  - Git Branch: `archive/sept23-openlane2-signoff`
  - Directory: `archive/sept23_openlane2_golden/` (with 16.15 MB GDS, LEF, DEF, netlist, and golden vectors).
- **Run #38 Audit Completed:**
  - Confirmed `met1` derating was properly applied at 50% (`[0.99, 0.50, 0, 0, 0, 0]`), but detailed routing reached 90+ minutes due to physical pin crowding inside the 256 PEs (dual XNOR/AND gates + 256 MUXes + global `mode` wire).
  - Validated that backend physical synthesis parameters cannot solve netlist-level pin crowding.
  - Concluded that **Path B (removing Mode 1 at the RTL level)** is the robust, definitive ASIC solution.

### [Architecture Decisions & Path B Blueprint]
- **Eliminating Mode 1 (Bipolar Stochastic Computing):**
  - **`src/scim_pe.v`:**
    - Delete 256 XNOR gates (`bipolar_prod = ~(a_bit ^ w_bit)`).
    - Delete 256 2:1 multiplexers (`prod_out = mode ? bipolar_prod : unipolar_prod`).
    - Remove `mode` input port; directly wire `prod_out = a_bit & w_bit`.
  - **`src/tt_um_scim_core.v`:**
    - Remove high-fanout global `mode` distribution across 256 PEs.
    - Delete 17th Wallace tree (reference stream accumulator for zero-point subtraction).
    - Delete reference SNG comparator (`sng_ref`).
    - Remove 16 column subtractor stages for bipolar offset.
    - Reclaim `ui_in[0]` (previously `mode`) as clean control or tie-off.
  - **`src/scim_wallace_tree.v`:**
    - Reinstate the original, verified 10-compressor 4:2 compressor tree (`scim_compressor_42.v`) from the Sept 23 sign-off.
  - **`src/scim_accumulator.v`:**
    - Retain sign-bit overflow saturation check (`(~sum_ext[13]) & sum_ext[12]`).
- **Physical Layout Impact:**
  - Netlist cell count reduced by **528+ standard cells** (~3,820 µm²).
  - Usable tile density drops to **~64.5%** (~47,400 µm² cell area in 73,500 µm² tile).
  - TritonRoute detailed routing runtime expected to converge cleanly in **12–18 minutes**.

### [Current Pipeline State]
- **Active Branch:** `test/path-b-streamlined` (clean baseline from `main`).
- **Safety:** `main` and `archive/sept23-openlane2-signoff` are 100% untouched and secure.
- **Ready for Fresh Session:** All diagnostics and implementation blueprints are fully documented.

### [Next Steps for Fresh Chat Session]
1. Open a **fresh chat session** on branch `test/path-b-streamlined`.
2. Implement Path B RTL pruning across `src/scim_pe.v`, `src/tt_um_scim_core.v`, `src/scim_wallace_tree.v`.
3. Update Cocotb verification suite (`test/test_scim_core.py`) for Unipolar (Mode 0) and Hybrid (Mode 2) regression.
4. Verify bit-exact mathematical parity locally (`make -C test test_all`).
5. Configure `src/config.json` with modern LibreLane 3 settings (`DRT_THREADS: 2`, `PL_TARGET_DENSITY_PCT: 65`, `GRT_LAYER_ADJUSTMENTS: [0.99, 0.50, 0, 0, 0, 0]`).
6. Dispatch CI hardening run to achieve 100% clean DRC/LVS physical sign-off and submit to `app.tinytapeout.com`.
