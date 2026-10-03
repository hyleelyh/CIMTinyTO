# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-03 13:18 (Run 37 Dispatched: LibreLane Dict Syntax for GRT_LAYER_ADJUSTMENTS on test/option2-recoded)

### [Built & Dispatched]
- **Run #36 Concluded:**
  - Cancelled at 4h 33m after confirming TritonRoute entered stubborn tiles mode due to un-derated `met1` signal congestion.
  - Confirmed root cause: LibreLane 3's Pydantic step validator expects a `dict` mapping for `GRT_LAYER_ADJUSTMENTS`, silently dropping the previous `list` format.
- **Applied Choice 1 Configuration Fix for Run #37:**
  - Updated `src/config.json` and `config.yaml` to the proper LibreLane dictionary mapping:
    ```json
    "GRT_LAYER_ADJUSTMENTS": {
      "met1": 0.99,
      "met2": 0.0,
      "met3": 0.0,
      "met4": 0.0,
      "met5": 0.0
    }
    ```
  - This ensures FastRoute explicitly derates `met1` by 99%, keeping inter-cell signal routing strictly on `met2`/`met3` and preserving `met1` for standard-cell pin access.
  - Retains target placement density at 72% with standard 6-site margins and decap cells.
- **Committed and Pushed to `origin/test/option2-recoded` to launch Run #37.**

### [Current Pipeline State]
- **Sept 23 Golden Archive:** 100% PRESERVED in `archive/sept23_openlane2_golden/`, tag `v-sept23-openlane2-signoff`, and branch `archive/sept23-openlane2-signoff`.
- **Active Branch:** `test/option2-recoded` (testing Choice 1: dictionary syntax on current 72% density code).
- **Run #37 Status:** Dispatched to GitHub Actions on `ttsky26d`.

### [Next Steps]
1. Monitor **Run #37** on GitHub Actions (`https://github.com/hyleelyh/CIMTinyTO/actions`).
2. Verify that with active `met1` derating, TritonRoute resolves pin access and converges in 15–25 iterations (< 25 mins).
3. If Run #37 passes:
   - Submit immediately to the Tiny Tapeout `sky26d` portal to lock in and assign wafer real estate.
   - Once space is assigned, decide whether to transition to Path B (removing Mode 1, reinstating 4:2 compressors) on a fresh branch.
