# Session Handoff

- **Date:** 2026-10-03 02:26
- **Machine:** Host/PC (`juliusli`)
- **Branch:** test/option2-recoded (Main branch remains untouched and frozen)
- **Sync Status:** Restored official Tiny Tapeout `ttsky26d` LibreLane 3 template defaults (6-site margins, natural cell padding, PL_TARGET_DENSITY_PCT 75) on branch `test/option2-recoded` for Run #35.

---

## Active Experiment: Run #35 (Official LibreLane 3 Defaults & Cell Padding Restoration)

1. **Active Branch:** `test/option2-recoded`
2. **Changes Applied:**
   - `src/config.json` & `config.yaml`:
     - Restored standard 6-site margins (`LEFT_MARGIN_MULT: 6`, `RIGHT_MARGIN_MULT: 6`, `TOP_MARGIN_MULT: 1`, `BOTTOM_MARGIN_MULT: 1`). Eliminates Net VGND boundary warning.
     - Removed `GPL_CELL_PADDING: 0` and `DPL_CELL_PADDING: 0` to enable LibreLane 3's natural cell padding. Physically eliminates adjacent `met1` pin `via1` DRC collisions.
     - Set `PL_TARGET_DENSITY_PCT: 75` (official TT recommendation).
     - Removed obsolete OpenLane 2 flags (`GRT_LAYER_ADJUSTMENTS`, `DRT_OPT_ITERS: 24`).
3. **Verification:** 11/11 Cocotb regression suites passing locally in 1.75s with 100% bit-exact mathematical parity.
4. **Safety:** `main` branch is 100% untouched and safe at commit `d42b67e`.
5. **Target:** Run #35 on GitHub Actions (cancels stuck Run #34 via `cancel-in-progress: true`).

---

## Tiny Tapeout sky26d Submission & CI Sign-Off Checklist

To complete submission to the Tiny Tapeout `sky26d` shuttle:

1. **Verify GitHub Pages Source Configuration:**
   - Navigate to: `https://github.com/hyleelyh/CIMTinyTO/settings/pages`
   - Under **Build and deployment > Source**, ensure **"GitHub Actions"** is selected (NOT "Deploy from a branch").
   - This allows the `viewer` action to automatically deploy the 3D GDS interactive viewer.

2. **Trigger and Monitor the GitHub Actions Run:**
   - Monitor the latest run at:
     `https://github.com/hyleelyh/CIMTinyTO/actions`
   - All 4 workflow jobs must succeed (turn GREEN):
     - `gds`: Hardens the RTL into GDSII via LibreLane 3.0 on SkyWater 130nm ($2 \times 2$ tile).
     - `precheck`: Runs DRC and physical design rule checks.
     - `gl_test`: Executes gate-level simulation regression with power rail back-annotation.
     - `viewer`: Deploys the interactive 3D GDS viewer to GitHub Pages.

3. **Submit on the Tiny Tapeout Portal:**
   - Navigate to: `https://app.tinytapeout.com/`
   - Select the `sky26d` shuttle.
   - Choose your purchased **2x2 tile**.
   - Link the repository: `https://github.com/hyleelyh/CIMTinyTO`.
   - The portal will verify the green CI status and 3D viewer deployment, and confirm your submission!

---

## Laptop Review & Walkthrough Access

To review the complete verification results, test matrix, and waveforms on your laptop:

1. **Pull the latest commits & ensure dependencies:**
   ```bash
   git pull origin main
   pip install -r test/requirements.txt
   ```
2. **Execute local regression verification:**
   ```bash
   source .venv/bin/activate && make -C test
   ```
