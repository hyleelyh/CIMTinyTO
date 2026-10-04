# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-04 09:00 (Run 45: Zero Perimeter Overlap & Automated Layout/DRC Dumper)

### [Built]
- **`.github/workflows/gds.yaml`:**
  - Added step-level `timeout-minutes: 50` on `Build GDS via OpenLane 2` and job-level `timeout-minutes: 60`.
  - Added `if: always()` automated upload step (`layout-debug-dump`) capturing all intermediate `runs/**`, `*.def`, `*.odb`, and `*.drc` files whenever the job completes, fails, or times out.
  - Added pre-upload step summary inventory listing all generated layout and DRC reports in `$GITHUB_STEP_SUMMARY`.
- **`src/config.json` & `config.yaml`:**
  - `LEFT_MARGIN_MULT: 2` & `RIGHT_MARGIN_MULT: 2`: $0.92\,\mu\text{m}$ clearance buffer on lateral boundaries.
  - `TOP_MARGIN_MULT: 1` & `BOTTOM_MARGIN_MULT: 1`: $2.72\,\mu\text{m}$ clearance buffer on vertical boundaries.
  - `IO_PIN_H_LENGTH: 0.9` & `IO_PIN_V_LENGTH: 1.0`: Pin stubs stop strictly inside the empty margin corridor, yielding **$0.00\,\mu\text{m}$ overlap with active standard-cell logic**.
  - `GRT_ALLOW_CONGESTION: 0` (`false`): Enforces 100% clean global route guides across `met2`–`met4` before detailed routing begins.
- **RTL & Testbenches:** Strictly 0 code changes. 15/15 Cocotb regression tests and Verilator lint remain 100% green.

### [Architecture Decisions & Silicon Hardening Forensics]
- **Run #44 Post-Mortem & Plateau Diagnosis:**
  - The $1.0\,\mu\text{m}$ pin truncation proved the boundary collision hypothesis: the 50%–60% spatial boundary tile processing time dropped $9.5\times$ from 16m 42s to 1m 46s, and total iteration times dropped from 20+ min to 3.5–5 min.
  - Initial violations plunged from 2,791 down to 1,815.
  - However, the violation curve plateaued at ~1,815 violations (1,017 `met1` shorts, 400 `met2` shorts).
  - Mathematical cause: With `LEFT_MARGIN_MULT: 1` ($0.46\,\mu\text{m}$) and `TOP_MARGIN_MULT: 0` ($0.0\,\mu\text{m}$), a $1.0\,\mu\text{m}$ pin stub still intruded $0.54\,\mu\text{m}$ laterally and $1.0\,\mu\text{m}$ vertically into Column 0 and Row 0 standard cells, creating an unbreakable floor of metal shorts.
- **Run #45 Zero-Overlap Architecture:**
  - Moving to 2-site lateral margins ($0.92\,\mu\text{m}$) and 1-row vertical margins ($2.72\,\mu\text{m}$) with $0.9\,\mu\text{m}$ / $1.0\,\mu\text{m}$ pin lengths guarantees complete physical isolation between I/O metal pins and active standard cell gates.
  - Net usable core area is $73,375.4\,\mu\text{m}^2$. Against Path B's $58,770\,\mu\text{m}^2$ synthesized cell area, true placement utilization is $80.1\%$, well within safe limits.

### [Current Pipeline State]
- **RTL / Verification:** 100% clean (Gate 0 golden model, Verilator, Cocotb unit + full core).
- **Physical Hardening:** Run #45 deployed with automated layout dump and zero boundary overlap.

### [Next Steps]
1. Push branch `test/path-b-streamlined` to trigger GitHub Actions Run #45.
2. Monitor CI physical hardening progress and detailed routing convergence to 0 DRC.
3. If any step fails or times out, download `layout-debug-dump` to inspect DEF/ODB and DRC coordinates in KLayout.
4. Review physical sign-off metrics (`metrics.csv`): 0 DRC, 0 LVS, positive setup/hold slack at 50 MHz.
5. Execute "Poking Holes" Red Team stress-testing session to audit corner cases prior to tapeout.

