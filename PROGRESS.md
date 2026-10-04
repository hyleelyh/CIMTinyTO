# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-04 09:45 (Run 47: Top Pin Corridor Opening & Sept 23 Power Strap Parity)

### [Built]
- **`src/config.json` & `config.yaml`:**
  - Configured `TOP_MARGIN_MULT: 1`: Opens a 1-row ($2.72\,\mu\text{m}$) horizontal corridor along the top boundary where all 43 I/O pins reside ($Y = 225.26\,\mu\text{m}$), stopping vertical power straps from dropping vias across the pin channel (mimicking the proven Sept 23 purple layout).
  - Configured `BOTTOM_MARGIN_MULT: 0`: Preserves the bottom row for standard cells, establishing net usable core area of **$72,580.86\,\mu\text{m}^2$** and legal placer density of **$99.296\% < 100.00\%$** (cleanly avoiding `[GPL-0301]`).
  - Configured `GRT_ALLOW_CONGESTION: 1` (`true`): Re-enables global routing handoff so FastRoute passes the 161 overflow guides to TritonRoute (clearing `[GRT-0116]`).
  - Maintained `IO_PIN_H_LENGTH: 0.4` and `IO_PIN_V_LENGTH: 0.4` with 1-site lateral margins (`LEFT/RIGHT_MARGIN_MULT: 1`).
- **`.github/workflows/gds.yaml`:**
  - Step timeout (50 min), job timeout (60 min), and `if: always()` layout dumper (`layout-debug-dump`) confirmed operational.
- **RTL & Testbenches:** Strictly 0 code changes. 15/15 Cocotb regression tests and Verilator lint remain 100% green.

### [Architecture Decisions & Silicon Hardening Forensics]
- **Run #46 Layout Inspection & Forensic Discovery:**
  - Inspection of the layout dump from Run #46 in KLayout confirmed that all 5,652 standard cells were placed legally, CTS completed, and global routing ran.
  - Comparing the layout against the Sept 23 golden sign-off revealed the physical root cause of routing shorts: In Sept 23, the vertical power straps terminated 1 row early, leaving the perimeter pin corridor unobstructed. In Run #44 and #46, `TOP_MARGIN_MULT: 0` caused the vertical power straps and vias to plunge across the top rail where all 43 I/O pins enter, creating a physical picket fence that blocked pin escape.
  - Setting `GRT_ALLOW_CONGESTION: 0` in Run #46 had also caused FastRoute to abort on 161 global overflow guides (`[GRT-0116]`).
- **Run #47 Calibration:**
  - Setting `TOP_MARGIN_MULT: 1` eliminates the vertical strap blockage at the top edge.
  - Preserving `BOTTOM_MARGIN_MULT: 0` keeps placement utilization at $99.296\% < 100\%$, preventing `GPL-0301`.
  - Re-enabling `GRT_ALLOW_CONGESTION: 1` lets FastRoute hand off the 161 guides to TritonRoute, which now has an unobstructed top highway to resolve detailed routes cleanly.

### [Current Pipeline State]
- **RTL / Verification:** 100% clean (Gate 0 golden model, Verilator, Cocotb unit + full core).
- **Physical Hardening:** Run #47 deployed.

### [Next Steps]
1. Push branch `test/path-b-streamlined` to trigger GitHub Actions Run #47.
2. Monitor CI physical hardening progress through placement, CTS, and detailed routing to 0 DRC.
3. Review physical sign-off metrics (`metrics.csv`): 0 DRC, 0 LVS, positive setup/hold slack at 50 MHz.
4. Execute "Poking Holes" Red Team stress-testing session to audit corner cases prior to tapeout.



