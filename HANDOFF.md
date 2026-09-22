# Session Handoff

- **Date:** 2026-09-21 21:05
- **Machine:** Host (`juliusli`)
- **Branch:** main
- **Sync Status:** Committed and pushed to origin/main

---

## 1. Current State: Pillar 3 (Physical ASIC Flow) — Placement Sizing Decision Point

1. **Artifacts Built & Documented:**
   - `docs/physical_sizing_and_tradeoff_analysis.md`: Exhaustive architectural note detailing the standard-cell area forensic audit, non-linear scaling laws ($O(N^2)$ vs. $O(N)$ vs. $O(1)$), DRAM-like banking study, and end-to-end Micro-ResNet inference speed analysis.
   - Flow files verified: `info.yaml`, `docs/info.md`, `src/config.json`, `config.yaml`, `src/scim_core.sdc`, `.github/workflows/gds.yaml`.
   - Verification baseline: Verilator lint clean (0 warnings), Cocotb 3/3 test suites pass bit-exact (100.00%).

2. **Forensic Sizing & Scaling Summary:**
   - **Why 13-bit accumulators blew up:** 16 columns $\times$ 14-bit parallel adders, 32 signed comparators (`sum > +4095`, `sum < -4096`), and saturation clamping MUXes = $\approx 19,200\,\mu\text{m}^2$.
   - **Why $8\times 8$ is NOT a $4\times$ area reduction:** 2D matrix blocks (PEs, weight DFFs) scale by $1/4$, but 1D peripherals (accumulators, SNG LFSRs, activation DFFs) scale by only $1/2$, and 0D infrastructure remains constant.
   - **Why $8\times 8$ cannot fit in 1 tile ($1\times 1$):** Cell area is $\approx 20,800\,\mu\text{m}^2$. A $1\times 1$ tile provides only $\approx 11,000\text{--}13,500\,\mu\text{m}^2$ ($160\%$ utilization). It requires a $1\times 2$ tile ($60.7\%$ density).
   - **Why Option 3 (DRAM Banking) fails on $1\times 2$:** Standard-cell DFFs are bulky ($\approx 15\,\mu\text{m}^2$). Time-multiplexing the ALU reduces area only to $\approx 49,500\,\mu\text{m}^2$ ($144.5\%$ utilization on $1\times 2$).
   - **Inference Speed on Micro-ResNet ($3\text{ MMACs}$):**
     - $16\times 16$ Core ($2\times 2$ Tile): $\approx 80\text{ ms}$ total latency $\implies$ **$\approx 12.5\text{ FPS}$ (Real-Time Video Rate)**.
     - $8\times 8$ Core ($1\times 2$ Tile): $\approx 370\text{ ms}$ total latency (4 tiling passes) $\implies$ **$\approx 2.7\text{ FPS}$ (Interactive Edge Rate)**.

3. **Pending Decision (User Reflecting on Goals):**
   - **Option 1 ($2\times 2$ Tile):** Full $16\times 16$ core, 0 RTL changes, $12.5\text{ FPS}$ real-time video, ~$2\times$ submission cost.
   - **Option 2 ($8\times 8$ Core on $1\times 2$ Tile):** Parameterized RTL downscale, $2.7\text{ FPS}$ interactive rate, standard base submission cost.

---

## 2. Next Session Instructions

1. Retrieve user decision on Option 1 ($2\times 2$ tile) vs. Option 2 ($8\times 8$ array on $1\times 2$ tile).
2. If Option 1:
   - Modify `info.yaml` to `tiles: "2x2"`.
   - Re-trigger OpenLane 2 cloud hardening on GitHub Actions.
   - Inspect placement, CTS, routing, and DRC/LVS reports.
3. If Option 2:
   - Parameterize array dimensions in `scim_core.v`, `scim_pe_array.v`, `scim_wallace_tree.v`, and `scim_acc_array.v`.
   - Re-run Verilator lint and Cocotb regressions.
   - Re-trigger hardening on $1\times 2$ tile.
4. Maintain strict Pillar 3 scope until physical GDS generation and placement closure succeed.
