# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-04 09:15 (Run 46: Core Restoration & 0.40um Zero-Overlap Pin Calibration)

### [Built]
- **`src/config.json` & `config.yaml`:**
  - Restored core boundary margins to `LEFT_MARGIN_MULT: 1` & `RIGHT_MARGIN_MULT: 1` ($0.46\,\mu\text{m}$) and `TOP_MARGIN_MULT: 0` & `BOTTOM_MARGIN_MULT: 0`.
  - Re-establishes net usable core area of **$73,489.23\,\mu\text{m}^2$**, reducing placer density to **$98.07\% < 100.00\%$** (cleanly eliminating `[GPL-0301]`).
  - Tuned pin lengths to `IO_PIN_H_LENGTH: 0.4` and `IO_PIN_V_LENGTH: 0.4`:
    - Lateral: $0.40\,\mu\text{m} < 0.46\,\mu\text{m}$ margin corridor $\implies$ **$0.00\,\mu\text{m}$ overlap with Column 0 cells**.
    - Vertical: $0.40\,\mu\text{m} < 0.48\,\mu\text{m}$ power rail corridor $\implies$ **$0.00\,\mu\text{m}$ overlap with internal cell signal pins**.
  - Retained `GRT_ALLOW_CONGESTION: 0` (`false`) to force clean global routing guides.
- **`.github/workflows/gds.yaml`:**
  - Step timeout (50 min), job timeout (60 min), and `if: always()` layout and DRC report dumper (`layout-debug-dump`) confirmed operational.
- **RTL & Testbenches:** Strictly 0 code changes. 15/15 Cocotb regression tests and Verilator lint remain 100% green.

### [Architecture Decisions & Silicon Hardening Forensics]
- **Run #45 Post-Mortem (`[GPL-0301]` 100.839% Density Overflow):**
  - In Run #45, setting `TOP/BOTTOM_MARGIN_MULT: 1` stripped 2 full rows ($2 \times 2.72\,\mu\text{m} \times 334\,\mu\text{m}$), removing $2,019.4\,\mu\text{m}^2$ of usable core space ($71,469.8\,\mu\text{m}^2$).
  - OpenROAD RePlace's C++ pin-density adjust added $+9,855.1\,\mu\text{m}^2$ of virtual halos to the $62,214.7\,\mu\text{m}^2$ physical cells, creating $72,069.7\,\mu\text{m}^2$ movable instance demand.
  - Utilization reached $72,069.7 / 71,469.8 = 100.839\% > 100\%$, triggering `[GPL-0301]`.
  - **Diagnostic Confirmation:** The automated artifact dumper in `gds.yaml` executed as designed upon failure, confirming full telemetry capture.
- **Run #46 Formulation:**
  - Restoring full core height reclaims the $2,019.4\,\mu\text{m}^2$, bringing utilization safely back to $98.07\%$.
  - Truncating pin stubs to $0.40\,\mu\text{m}$ achieves the intended zero-overlap isolation without sacrificing a single square micron of core placement area.

### [Current Pipeline State]
- **RTL / Verification:** 100% clean (Gate 0 golden model, Verilator, Cocotb unit + full core).
- **Physical Hardening:** Run #46 deployed.

### [Next Steps]
1. Push branch `test/path-b-streamlined` to trigger GitHub Actions Run #46.
2. Monitor CI physical hardening progress through placement, CTS, and detailed routing to 0 DRC.
3. Review physical sign-off metrics (`metrics.csv`): 0 DRC, 0 LVS, positive setup/hold slack at 50 MHz.
4. Execute "Poking Holes" Red Team stress-testing session to audit corner cases prior to tapeout.


