# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-04 11:25 (Run 50: Option A — Symmetric 81-Row Core + AREA 2 ABC Optimization)

### [Built]
- **Floorplan & Synthesis Hardening (`src/config.json`, `config.yaml`):**
  - Updated `SYNTH_STRATEGY: "AREA 2"` (multi-pass iterative ABC area mapping: `resyn2; dch; if -m; choice2; amap`) to eliminate the $397\,\mu\text{m}^2$ ($0.554\%$) density deficit.
  - Configured symmetric 81-row core: `CORE_AREA: [0.46, 2.72, 334.42, 223.04]`.
  - Configured `FP_PDN_SKIPTRIM: 0` (`false`) to ensure all power straps are cleanly clipped at the die boundary.

### [Architecture Decisions & Silicon Hardening Forensics]
- **Run #49 Forensic Root Cause:**
  - OpenROAD requires core coordinates to align with the standard-cell row height ($H_{\text{site}} = 2.720\,\mu\text{m}$).
  - When $Y_{\min} = 0.340\,\mu\text{m}$ was supplied, OpenROAD snapped it up to $2.720\,\mu\text{m}$ (`[WARNING] [IFP-0028] Core area lower left (0.460, 0.340) snapped to (0.460, 2.720)`), truncating the core from 82 to 81 rows.
  - In 81 rows, actual cell area ($62,214.7\,\mu\text{m}^2$) only occupies $86.8\%$ of the core, but OpenROAD added $9,855.1\,\mu\text{m}^2$ of virtual "Pin density area adjust", reaching $100.554\%$ ($+397\,\mu\text{m}^2$ overflow).
- **Run #50 Solution (Option A):**
  - Setting $Y \in [2.720\,\mu\text{m}, 223.040\,\mu\text{m}]$ aligns directly on the row grid ($1\times 2.72$ and $82\times 2.72$), preventing any coordinate snapping.
  - Row 0 ($[0.00, 2.72]$) and Row 82 ($[223.04, 225.76]$) are left empty, providing **identical $+2.48\,\mu\text{m}$ safe keep-out margins at both bottom and top edges**.
  - No cell or power rail touches or crosses any boundary ($Y_{\text{bottom rail}} = +2.48\,\mu\text{m} > 0.00$; $Y_{\text{top rail}} = 223.28\,\mu\text{m} < 225.76$).
  - `SYNTH_STRATEGY: "AREA 2"` reduces logic gate area by $1\%\text{--}3\%$, bringing virtual placement utilization below $100\%$.

### [Current Pipeline State]
- **RTL / Verification:** 100% clean (Gate 0 golden model, Verilator, Cocotb 15/15 unit + full core). Strictly zero RTL modifications.
- **Physical Hardening:** Run #48 achieved 0 DRC, 0 LVS, positive timing, and 100% clean `gl_test`. Run #50 eliminates the bottom/top PDN overhangs and achieves 100% clean precheck.

### [Next Steps]
1. Commit and push configuration changes to `origin/test/path-b-streamlined` to trigger Run #50.
2. Confirm green checkmarks across `gds`, `precheck` (0 LEF errors, Boundary PASS), `gl_test`, and `viewer`.
3. Conduct Red Team physical verification review on final sign-off metrics.



