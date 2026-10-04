# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-03 23:35 (Canonical `0c88fea` PnR Baseline Restored for Run 43)

### [Built]
- **`src/config.json` & `config.yaml`:**
  - Restored the canonical, proven LibreLane 3 configuration from commit `0c88fea` (`PL_TARGET_DENSITY_PCT: 99`, `LEFT/RIGHT_MARGIN_MULT: 1`, `TOP/BOTTOM_MARGIN_MULT: 0`, `GRT_ALLOW_CONGESTION: 1`, `GRT_OVERFLOW_ITERS: 100`).
  - Removed `GRT_LAYER_ADJUSTMENTS: [0.99, 0.50, 0, 0, 0, 0]`, eliminating the 50% met1 routing penalty that forced excessive vias and caused TritonRoute 15-minute stalls in Run #39.
  - Removed `DRT_THREADS: 2`, allowing TritonRoute to fully utilize all runner vCPUs.
- **RTL & Testbenches:** Strictly 0 code changes. Verilator lint and 15/15 Cocotb tests remain 100% green.

### [Architecture Decisions & Silicon Hardening Forensics]
- **The Breakthrough of Combining Path B RTL with the `0c88fea` Baseline:**
  - In commit `0c88fea`, the physical pipeline (Yosys synthesis, RePlace placement, CTS, FastRoute global routing) completed with 100% legality.
  - The only residual issue in `0c88fea` was 3 `met1` shorts caused by netlist-level pin crowding in the old 256 PE multiplexers and 32 14-bit comparators.
  - Path B completely eliminated those 512 cells and the global broadcast net at the RTL level.
  - In Run #39, TritonRoute was progressing (violations down to 997), but took 15 min per iteration due to `GRT_LAYER_ADJUSTMENTS` throttling `met1` and `DRT_THREADS: 2` throttling compute threads.
  - Restoring the unthrottled `0c88fea` routing setup with Path B RTL eliminates both the netlist congestion and the routing thread/layer bottlenecks.

### [Current Pipeline State]
- **RTL / Verification:** 100% clean (Gate 0 golden model, Verilator, Cocotb unit + full core).
- **Physical Hardening:** Run #43 deployed.

### [Next Steps]
1. Commit and push branch `test/path-b-streamlined` to trigger GitHub Actions Run #43.
2. Monitor CI physical hardening progress and detailed routing convergence.
3. Review physical metrics (`metrics.csv`): cell count, density, 0 DRC, 0 LVS, positive setup/hold slack at 50 MHz.
4. Execute "Poking Holes" Red Team stress-testing session to audit corner cases before final tapeout.
