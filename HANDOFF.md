# Session Handoff: Run #37 Dispatch (Choice 1 Test)

- **Date:** 2026-10-03 13:18
- **Machine:** Host/PC (`juliusli`)
- **Active Branch:** `test/option2-recoded`
- **Sept 23 Golden Archive:** Tagged at `v-sept23-openlane2-signoff`, branch `archive/sept23-openlane2-signoff`, and committed in `archive/sept23_openlane2_golden/`.
- **Target:** Run #37 on GitHub Actions (`https://github.com/hyleelyh/CIMTinyTO/actions`).

---

## Active Experiment: Run #37 (LibreLane Dict Syntax Fix for met1 Derating)

1. **Hypothesis:**
   - Run #36 ran for 4.5 hours because LibreLane 3 dropped `"GRT_LAYER_ADJUSTMENTS": [0.99, ...]` due to list-vs-dict type mismatch, leaving `met1` un-derated.
   - By converting to the proper dictionary format:
     ```json
     "GRT_LAYER_ADJUSTMENTS": {
       "met1": 0.99,
       "met2": 0.0,
       "met3": 0.0,
       "met4": 0.0,
       "met5": 0.0
     }
     ```
     FastRoute will actually enforce 99% `met1` derating. With our 72% density and balanced binary adder tree, TritonRoute should converge cleanly in 15–25 minutes.

2. **Goal:**
   - Achieve a 100% green build on `ttsky26d` immediately.
   - Submit to `app.tinytapeout.com` so Tiny Tapeout can officially assign physical real estate on the `sky26d` shuttle wafer.
   - Once wafer real estate is locked in, we can evaluate implementing Path B (No Mode 1 + 4:2 Compressors) on a fresh branch.
