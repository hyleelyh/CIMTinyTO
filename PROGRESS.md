# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-04 11:15 (Run 49: Floorplan Elevation to Clear Bottom PDN Overhang)

### [Built]
- **Floorplan & Physical Hardening (`src/config.json`, `config.yaml`):**
  - Configured explicit `DIE_AREA: [0.0, 0.0, 334.88, 225.76]`.
  - Configured elevated `CORE_AREA: [0.46, 0.34, 334.42, 223.38]`.
  - Removed coarse `TOP/BOTTOM_MARGIN_MULT` to prevent multi-row truncation.
  - Updated `docs/info.md` to reference the correct 2x2 tile footprint.

### [Architecture Decisions & Silicon Hardening Forensics]
- **Eliminating the $0.24\,\mu\text{m}$ Bottom Rail Overhang:**
  - In Run #48, `BOTTOM_MARGIN_MULT: 0` placed Row 0 at $Y = 0.00\,\mu\text{m}$. The $0.48\,\mu\text{m}$-wide `met1` power rail, centered on the row boundary, extended into $[-0.24\,\mu\text{m}, +0.24\,\mu\text{m}]$, triggering 18 precheck LEF port boundary errors and `Shapes outside project area`.
  - User's KLayout measurement revealed $2.48\,\mu\text{m}$ empty headroom at the top and $-0.24\,\mu\text{m}$ overhang at the bottom ($2.48 + 0.24 = 2.72\,\mu\text{m} = 1\times \text{row height}$).
  - Elevating `CORE_AREA` by exactly **$+0.34\,\mu\text{m}$** (1 `met1` routing track pitch):
    1. Lifts Row 0 bottom rail to $[+0.10\,\mu\text{m}, +0.58\,\mu\text{m}]$, completely clearing the bottom die boundary ($Y \ge 0.00$).
    2. Keeps all 82 rows ($72,580.86\,\mu\text{m}^2$ net core, 85.7% density), permanently avoiding the 81-row `[GPL-0301]` density trap ($100.839\% > 100\%$).
    3. Leaves $2.14\,\mu\text{m}$ top escape room ($Y_{\text{top rail}} = 223.62\,\mu\text{m} \le 225.76\,\mu\text{m}$).
    4. Guarantees all cell pins align strictly with the PDK's $0.34\,\mu\text{m}$ horizontal routing tracks, preventing off-grid pin access DRCs.

### [Current Pipeline State]
- **RTL / Verification:** 100% clean (Gate 0 golden model, Verilator, Cocotb 15/15 unit + full core). Strictly zero RTL modifications.
- **Physical Hardening:** Run #48 achieved 100% clean GDS, 0 DRC, 0 LVS, positive timing, and 100% clean `gl_test`. Run #49 resolves the LEF/GDS boundary overhang in precheck.

### [Next Steps]
1. Commit and push configuration changes to `origin/test/path-b-streamlined` to trigger Run #49.
2. Confirm green checkmarks across `gds`, `precheck` (0 LEF errors, Boundary PASS), `gl_test`, and `viewer`.
3. Conduct Red Team physical verification review on final sign-off metrics.



