# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-03 23:15 (Path B Hardening Optimization: Cell Padding & Routability Placement for Run 40)

### [Built]
- **`src/config.json`:**
  - `PL_ROUTABILITY_DRIVEN`: Set to `1` (enables routability-driven placement in RePlace).
  - `GPL_CELL_PADDING`: Set to `1` (adds 1-site = 0.46 µm spacing between cells during global placement).
  - `DPL_CELL_PADDING`: Set to `1` (maintains cell pin separation during detailed placement).
  - `PL_TARGET_DENSITY_PCT`: Set to `70` (virtual density ~78%, safely below the 100% GPL-0301 limit).
  - `LEFT_MARGIN_MULT`: Restored to `6` (2.76 µm buffer between core cells and left I/O pad tracks).
  - `RIGHT_MARGIN_MULT`: Restored to `6` (2.76 µm buffer between core cells and right I/O pad tracks).
  - `TOP_MARGIN_MULT` & `BOTTOM_MARGIN_MULT`: Set to `1` (standard row spacing from top/bottom boundaries).
  - `GRT_LAYER_ADJUSTMENTS`: Adjusted to `[0.99, 0.30, 0, 0, 0, 0]` (providing 70% routing capacity on met1).
- **RTL & Testbenches:** Strictly 0 code changes. Verilator lint and 15/15 Cocotb tests remain 100% green.

### [Architecture Decisions]
- **TritonRoute Iteration Bottleneck Diagnosis:** Run #39 confirmed that Path B wirelength dropped significantly (275k -> 235k µm) and vias dropped (58k -> 53k). However, `GPL_CELL_PADDING: 0` caused cells to abut, causing local pin congestion on `li1`/`met1`. Pins on adjacent cells forced TritonRoute to execute dense maze-routing detours, taking ~15–18 minutes CPU time per iteration and timing out after 23 iterations.
- **Routability & 1-Site Padding Resolution:** With Path B cell area reduced to ~47,400 µm² in a 72,654 µm² core (raw density ~65%), adding 1-site padding raises virtual density to ~78%, which is well below the 100% threshold while physically spacing cell pins apart. This unlocks fast, clean routing convergence in OpenROAD.

### [Current Pipeline State]
- **RTL / Verification:** 100% clean (Gate 0 golden model, Verilator, Cocotb unit + full core).
- **Physical Hardening:** Run #39 timed out at iteration 23; Run #40 configured and ready to push to CI.

### [Next Steps]
1. Commit `src/config.json` and push branch `test/path-b-streamlined` to trigger GitHub Actions Run #40.
2. Monitor CI physical hardening progress and detailed routing convergence.
3. Review physical metrics (`metrics.csv`): cell count, density, 0 DRC, 0 LVS, positive setup/hold slack at 50 MHz.
4. Execute "Poking Holes" Red Team stress-testing session to audit corner cases before final tapeout.
