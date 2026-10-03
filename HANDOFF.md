# Session Handoff: Path B (Mode 1 Removal & Clean 4:2 Compressor Sign-Off)

- **Date:** 2026-10-03 15:20
- **Machine:** Host/PC (`juliusli`)
- **Active Branch:** `test/path-b-streamlined` (Branched directly from `main`)
- **Sept 23 Golden Archive:** Tagged at `v-sept23-openlane2-signoff`, branch `archive/sept23-openlane2-signoff`, and committed in `archive/sept23_openlane2_golden/`.
- **Target Deliverable:** Clean RTL implementation of Path B, Cocotb regression sign-off, and LibreLane 3 hardening run for Tiny Tapeout `ttsky26d`.

---

## Instructions for Next Chat Session

### 1. Context & Motivation
- Previous runs confirmed that backend PnR knobs (density, derating) cannot eliminate pin-access deadlocks caused by micro-level congestion (256 PE MUXes, 256 XNORs, global `mode` broadcast wire).
- **Path B** resolves this definitively at the RTL source level by removing Mode 1 (Bipolar mode), cutting 528+ cells and reducing core density to ~64.5%.
- This allows reinstating the original, verified 10-compressor 4:2 compressor Wallace tree architecture.

### 2. Immediate Work Plan for Fresh Chat
1. **RTL Modifications:**
   - `src/scim_pe.v`: Remove `mode` port, XNOR gate, and MUX. Direct assignment `assign prod_out = a_bit & w_bit;`.
   - `src/tt_um_scim_core.v`: Remove `mode` wire distribution, 17th reference Wallace tree, reference SNG, and bipolar column subtractors.
   - `src/scim_wallace_tree.v`: Restore the original 4:2 compressor tree from `archive/sept23_openlane2_golden/src/scim_wallace_tree.v`.
   - `src/scim_accumulator.v`: Ensure sign-bit overflow saturation is active (`(~sum_ext[13]) & sum_ext[12]`).
2. **Verification:**
   - Update Cocotb testbenches (`test/test_scim_core.py`) to test Mode 0 (Unipolar) and Mode 2 (Hybrid).
   - Run `make -C test test_all` to confirm 100% test pass.
3. **Synthesis & Physical Hardening:**
   - Update `src/config.json` with LibreLane 3 compliant settings:
     - `PL_TARGET_DENSITY_PCT: 65`
     - `GRT_LAYER_ADJUSTMENTS: [0.99, 0.50, 0, 0, 0, 0]`
     - `DRT_THREADS: 2`
     - JSON booleans (`true`/`false`)
   - Commit and push to `origin/test/path-b-streamlined` to trigger CI build.
   - Target: Clean DRC/LVS physical sign-off in 15–20 minutes and submit to `app.tinytapeout.com`.
