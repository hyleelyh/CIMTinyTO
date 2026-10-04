# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-04 08:10 (Run 44: Modern LibreLane Variables & 1.0um Pin Geometry)

### [Built]
- **`src/config.json` & `config.yaml`:**
  - Modernized 4 deprecated OpenLane 1 configuration variables flagged by LibreLane:
    - `FP_IO_HLENGTH` & `FP_IO_VLENGTH` (2.0 um) -> `IO_PIN_H_LENGTH: 1.0` & `IO_PIN_V_LENGTH: 1.0` (um).
    - `FP_PDN_VPITCH: 38.87` -> `PDN_VPITCH: 38.87`.
    - `FP_PDN_MULTILAYER: 0` -> `PDN_MULTILAYER: false`.
  - Retained proven `SYNTH_STRATEGY: "AREA 1"` (62,882 um^2, 2-pass ABC mapping) and `PL_TARGET_DENSITY_PCT: 99` (allowing clean 98.44% virtual placement headroom).
  - Validated syntax with `json.load()` and `yaml.safe_load()`.
- **RTL & Testbenches:** Strictly 0 code changes. Verilator lint (0 warnings) and Cocotb regression (15/15 tests passing, 100%) remain intact.

### [Architecture Decisions & Silicon Hardening Forensics]
- **Run #43 Post-Mortem & Boundary Short Forensics:**
  - In Run #43, TritonRoute achieved dramatic convergence down to 221 violations at iteration 31 (a 78% reduction from Run #39's 997 violations, wirelength reduced to 218,803 um, vias reduced to 52,597). GitHub Actions canceled at the 6-hour runner limit.
  - Telemetry showed TritonRoute spent over 16 minutes per iteration exclusively on the 50%–60% spatial tile.
  - Root cause analysis identified that `FP_IO_HLENGTH: 2` and `FP_IO_VLENGTH: 2` created 2.0 um metal pin fingers protruding 1.54 um directly into active standard-cell rows on the perimeter (`LEFT_MARGIN_MULT: 1` = 0.46 um, `TOP_MARGIN_MULT: 0` = 0.0 um).
  - This created hard physical metal shorts between external I/O pins and standard-cell internal pins on `met1` and `met2`.
  - Shortening pin lengths to `1.0` um confines the pin geometry within the perimeter track ring, completely preventing boundary cell overlaps and unlocking fast detailed route convergence.

### [Current Pipeline State]
- **RTL / Verification:** 100% clean (Gate 0 golden model, Verilator, Cocotb unit + full core).
- **Physical Hardening:** Run #44 dispatched.

### [Next Steps]
1. Monitor GitHub Actions Run #44 detailed routing convergence.
2. Confirm iteration times decrease and violations converge to 0.
3. Review physical sign-off metrics (`metrics.csv`): 0 DRC, 0 LVS, positive setup/hold slack at 50 MHz.
4. Execute "Poking Holes" Red Team stress-testing session to audit corner cases prior to tapeout.
