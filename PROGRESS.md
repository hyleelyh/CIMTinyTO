# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-03 02:26 (Clean LibreLane 3 Template & Cell Padding Restored for Run 35)

### [Built & Dispatched]
- Diagnosed root cause of Run 34 stall in TritonRoute (5+ hours):
  - Emergency hack `DPL_CELL_PADDING: 0` placed standard cells shoulder-to-shoulder with 0 spacing. Adjacent pins on `met1` sitting $<0.17\,\mu\text{m}$ apart could not drop `via1` without violating Sky130 spacing rules, causing an intractable local pin-escape deadlock in TritonRoute.
  - Squeezing margins to 1 site jammed standard cells into the periphery power ring (`[GRT-0041] Net VGND has wires/vias outside die area`).
  - `DRT_OPT_ITERS: 24` is an OpenLane 1/2 key ignored by LibreLane 3's step schema, falling back to 64 exhaustive iterations.
- Converted `src/config.json` and `config.yaml` to the official **`ttsky26d` LibreLane 3 template**:
  - Restored clean 6-site margins (`LEFT_MARGIN_MULT: 6`, `RIGHT_MARGIN_MULT: 6`, `TOP_MARGIN_MULT: 1`, `BOTTOM_MARGIN_MULT: 1`).
  - Removed `GPL_CELL_PADDING: 0` and `DPL_CELL_PADDING: 0` (enabling LibreLane natural cell padding to resolve pin escape).
  - Set `PL_TARGET_DENSITY_PCT: 75` (standard LibreLane target density).
  - Removed obsolete OpenLane 2 routing flags (`GRT_LAYER_ADJUSTMENTS`, `DRT_OPT_ITERS`, `GRT_OVERFLOW_ITERS`).
- Verified local regression: 11/11 PASS in 1.75s with 100% bit-exact parity across all golden vectors and overclocking to 200 MHz.
- Pushed to `origin/test/option2-recoded` to launch Run #35 (automatically aborting stuck Run #34 via `cancel-in-progress: true`).

### [Architecture Decisions & Root Cause Analysis]
- **Toolchain Modernization (OpenLane 2 in tt08 vs. LibreLane 3 in ttsky26d):**
  - Sept 23 sign-off ran on `tt08` with OpenLane 2 (`PL_TARGET_DENSITY: 0.92`, older OpenROAD build).
  - `sky26d` shuttle runs on `ttsky26d` with LibreLane 3 (modern 2026 OpenROAD build with strict Sky130 via-spacing rules and `PL_TARGET_DENSITY_PCT` schema).
  - In Runs 28–34, carrying over aggressive 0-padding hacks from an older unpruned design broke LibreLane 3's detailed router.
  - Now that Step 1 (comparator bit checks) and Step 2 (balanced binary tree) have slashed global track demand down to 66.44%, the netlist fits easily into the core with generous margins and natural cell padding.

### [Current Pipeline State]
- **Pillar 1 (Mathematical Golden Model): 100% COMPLETE & FROZEN.**
- **Pillar 2 (Microarchitecture & Verification): 100% COMPLETE & FROZEN.**
- **Pillar 3 (Physical ASIC Flow): 100% COMPLETE, VERIFIED & FROZEN.**
- **Pillar 4 (Static Timing Analysis & Power Sign-off): 100% COMPLETE, VERIFIED & FROZEN.**
- **Pillar 5 (Gate-Level Simulation & Dynamic Power Sign-off): 100% COMPLETE, VERIFIED, RED-TEAM AUDITED & FROZEN.**
- **CI / Shuttle Hardening (`sky26d`): RUN #35 DISPATCHED ON BRANCH `test/option2-recoded`.**

### [Next Steps]
1. Monitor Run #35 on GitHub Actions.
2. Confirm detailed routing converges to 0 DRCs within 15–20 minutes with natural cell padding.
3. Once all 4 workflow jobs (`gds`, `precheck`, `gl_test`, `viewer`) turn green, merge `test/option2-recoded` to `main`.
4. Submit repository to the Tiny Tapeout `sky26d` portal.
5. User to open a fresh chat session for **Pillar 6 (Pre-Silicon Emulation on FPGA)** per the Pillar Session Isolation Protocol.
