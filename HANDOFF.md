# Session Handoff

- **Date:** 2026-10-03 08:36
- **Machine:** Host/PC (`juliusli`)
- **Branch:** test/option2-recoded (Main branch remains untouched and frozen at `d42b67e`)
- **Sync Status:** Dispatched **Run #36** with targeted 99% `met1` derating (`GRT_LAYER_ADJUSTMENTS`), tuned density (`PL_TARGET_DENSITY_PCT: 72`), and 2-core routing (`ROUTING_CORES: 2`).

---

## Active Experiment: Run #36 (Physical Pin Protection & Convergence Tuning)

1. **Active Branch:** `test/option2-recoded`
2. **Changes Applied in Run #36:**
   - `src/config.json` & `config.yaml`:
     - `"GRT_LAYER_ADJUSTMENTS": [0.99, 0, 0, 0, 0, 0]`: Derates `met1` by 99% in FastRoute. Directly eliminates the 84,090 µm `met1` wire congestion and the 11 `met1` spacing/short violations observed in Run 35.
     - `"PL_TARGET_DENSITY_PCT": 72`: Provides extra whitespace between cell rows to eliminate the remaining 5 shorts on `met2` and `met4`.
     - `"ROUTING_CORES": 2`: Binds detailed routing to 2 cores matching GitHub runner vCPUs.
     - Retains standard 6-site margins, natural cell padding, and `GRT_ALLOW_CONGESTION: 1`.
3. **Verification:** 11/11 Cocotb regression suites passing locally in 1.71s with 100% bit-exact mathematical parity across all golden vectors and overclocking to 200 MHz.
4. **Safety:** `main` branch is 100% untouched and safe at commit `d42b67e`.
5. **Target:** Run #36 on GitHub Actions.

---

## Fresh Chat Session Instructions (Clean Slate)

When starting the fresh chat session:

1. **Check Status of Run #36:**
   - Visit: `https://github.com/hyleelyh/CIMTinyTO/actions`
   - Review Run #36 logs:
     - Verify FastRoute routes inter-cell signals on `met2`/`met3` instead of `met1`.
     - Verify TritonRoute converges to **0 DRC violations** in under 30 iterations.
2. **If Run #36 is 100% Green:**
   - Confirm all 4 jobs pass: `gds`, `precheck`, `gl_test`, `viewer`.
   - Merge `test/option2-recoded` into `main`.
   - Complete Tiny Tapeout `sky26d` portal registration on `https://app.tinytapeout.com/`.
   - Proceed to **Pillar 6 (Pre-Silicon Emulation on FPGA)**.
3. **If Any Violations Remain:**
   - Inspect the exact violation layer and count from the log and apply surgical adjustments with full context from this handoff.
