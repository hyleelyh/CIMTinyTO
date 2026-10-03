# Session Handoff: Run #38 Dispatch (True 50% met1 Derating)

- **Date:** 2026-10-03 13:38
- **Machine:** Host/PC (`juliusli`)
- **Active Branch:** `test/option2-recoded`
- **Sept 23 Golden Archive:** Tagged at `v-sept23-openlane2-signoff`, branch `archive/sept23-openlane2-signoff`, and committed in `archive/sept23_openlane2_golden/`.
- **Target:** Run #38 on GitHub Actions (`https://github.com/hyleelyh/CIMTinyTO/actions`).

---

## Active Experiment: Run #38 (True met1 50% Derate & Modernized LibreLane 3 Schema)

1. **Root Cause Resolved:**
   - In Sky130 LEF, routing layers are ordered: `[li1, met1, met2, met3, met4, met5]`.
   - The Tiny Tapeout default `[0.99, 0, 0, 0, 0, 0]` applied 0.99 to `li1` (index 0) to block signals from local interconnect, but left `met1` (index 1) at **0% derating**, dumping signal nets on standard-cell pins.
   - Setting `GRT_LAYER_ADJUSTMENTS: [0.99, 0.50, 0, 0, 0, 0]` reduces `met1` routing capacity by 50%, reserving 50% of tracks strictly for standard-cell pin access.
   - Updated all deprecated LibreLane 3 variables (`DRT_THREADS`, `IO_PIN_H_LENGTH`, `IO_PIN_V_LENGTH`, `PDN_VPITCH`, `PDN_MULTILAYER`, `DECAP_CELLS`) and converted integer flags to JSON booleans. Verified with `Config.load` locally: 0 errors, 0 warnings.

2. **Goal:**
   - Achieve 100% green DRC/LVS/routing sign-off on `ttsky26d`.
   - Submit immediately to `app.tinytapeout.com` so Tiny Tapeout can officially assign wafer real estate for `sky26d`.
   - Once tile real estate is assigned, open a fresh branch and chat session for Path B.
