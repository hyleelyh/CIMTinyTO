# Session Handoff

- **Date:** 2026-09-21 17:45
- **Machine:** Host (`juliusli-MSI`)
- **Branch:** main
- **Sync Status:** Up to date with origin/main

---

## 1. Current State: Pillar 3 (Physical ASIC Flow) — Placement Sizing Decision Point

1. **Artifacts Built & Verified Clean:**
   - `info.yaml`, `docs/info.md`, `src/config.json`, `config.yaml`, `src/scim_core.sdc`, `.github/workflows/gds.yaml`.
   - Lint: Verilator 0 errors, 0 warnings.
   - Cocotb: 3/3 test suites pass bit-exact (100.00%).

2. **First Cloud Hardening Run Result (`[GPL-0301]`):**
   - GitHub Actions CI ran OpenLane 2 on Sky130 HD PDK.
   - Global Placement failed with:
     ```plaintext
     CoreArea: 34,255.35 µm² (1x2 Tile)
     PlaceInstsArea: 63,548.45 µm² (5,769 standard cells)
     Utilization: 192.12% (> 100% floorplan capacity)
     ```
   - **Forensic Diagnosis:** The physical mapping expanded front-end generic cell counts into standard cells:
     - 16x 13-bit saturating accumulators (adders + dual magnitude comparators + clamping MUXes): ~1,920 cells.
     - 17 Wallace trees (153 4:2 compressors synthesized into discrete gates): ~1,224 cells.
     - DFFs (256 weight + 208 accumulator + control): ~500+ DFFs (~9,000 µm²).
     - 618 fixed well-tap cells + CTS repeater buffers.

3. **Pending User Decision (Shuttle Cost vs. Compute Footprint):**
   - **Option 1 ($2\times 2$ Tile Allocation):** Core area $\approx 70,000\,\mu\text{m}^2$. Fits $63,548\,\mu\text{m}^2$ macro at ~64% utilization with 0 RTL changes and 100 MMAC/s throughput. Trade-off: Higher Tiny Tapeout submission cost (~2x).
   - **Option 2 ($8\times 8$ Array Downscale on $1\times 2$ Tile):** Fits in current $1\times 2$ budget ($34,255\,\mu\text{m}^2$) at ~58% density with no extra cost. Trade-off: 4x lower compute throughput; requires matrix tiling for inference.
   - **Option 3 (Time-Multiplexing Arithmetic):** Share accumulator/Wallace tree columns across cycles.

---

## 2. Next Session Instructions

1. Retrieve user decision on Option 1 ($2\times 2$ tile) vs. Option 2 ($8\times 8$ array on $1\times 2$ tile).
2. If Option 1:
   - Modify `info.yaml` to `tiles: "2x2"`.
   - Re-trigger OpenLane 2 cloud hardening on GitHub Actions.
   - Inspect placement and routing reports.
3. If Option 2:
   - Parameterize array dimensions in `scim_core.v`, `scim_pe_array.v`, `scim_wallace_tree.v`, and `scim_acc_array.v`.
   - Re-run Verilator lint and Cocotb regressions.
   - Re-trigger hardening on $1\times 2$ tile.
4. Maintain strict Pillar 3 scope until physical GDS generation and placement closure succeed.
