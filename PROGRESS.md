# Project Progress: CIMTinyTO

## Last Execution Run: 2026-10-03 13:38 (Run 38 Dispatched: 6-Element Metal Layer Derating & Modern LibreLane 3 Schema on test/option2-recoded)

### [Built & Dispatched]
- **Discovered Ground-Truth Router Layer Indexing:**
  - Audited LibreLane 3.0.14 source code (`steps/common_variables.py`, `scripts/odbpy/reader.py`, `scripts/openroad/common/set_layer_adjustments.tcl`).
  - `GRT_LAYER_ADJUSTMENTS` strictly requires `List[Decimal]`, mapped directly to routing level $\ge 1$:
    - **Index 0:** `li1` (Routing level 1 — Titanium Nitride local interconnect)
    - **Index 1:** `met1` (Routing level 2 — Metal 1 / standard-cell pin layer)
    - **Index 2:** `met2` (Routing level 3 — Metal 2)
    - **Index 3:** `met3` (Routing level 4 — Metal 3)
    - **Index 4:** `met4` (Routing level 5 — Metal 4)
    - **Index 5:** `met5` (Routing level 6 — Metal 5)
  - Tiny Tapeout default `[0.99, 0, 0, 0, 0, 0]` set 99% derating on `li1` (preventing long routes on high-resistance local interconnect), while `met1` (Index 1) was left at **0.0 (0% derating)** across all previous runs.
  - Set `GRT_LAYER_ADJUSTMENTS: [0.99, 0.50, 0, 0, 0, 0]` to enforce 50% capacity reduction specifically on `met1` (reserving 50% routing tracks for standard-cell pin access) while retaining 99% block on `li1`.
- **Modernized LibreLane 3 Schema & Deprecations:**
  - Replaced all deprecated keys with official LibreLane 3 names:
    - `ROUTING_CORES` $\rightarrow$ `DRT_THREADS: 2`
    - `FP_IO_HLENGTH` $\rightarrow$ `IO_PIN_H_LENGTH: 2`
    - `FP_IO_VLENGTH` $\rightarrow$ `IO_PIN_V_LENGTH: 2`
    - `FP_PDN_VPITCH` $\rightarrow$ `PDN_VPITCH: 38.87`
    - `FP_PDN_MULTILAYER` $\rightarrow$ `PDN_MULTILAYER: false`
    - `DECAP_CELL` $\rightarrow$ `DECAP_CELLS`
  - Replaced integer flags (`1`/`0`) with explicit JSON booleans (`true`/`false`) as strictly mandated by LibreLane 3 validator.
- **Local Validation & Testing:**
  - Ran local `librelane.config.Config.load` validation: **0 errors, 0 warnings**.
  - Cocotb regression suite (`make -C test test_all`): **11/11 PASS in 1.74s** (including 200 MHz overclocking).
- **Pushed to `origin/test/option2-recoded` to launch Run #38 on GitHub Actions.**

### [Architecture Decisions]
- **Why Index 1 is `met1`:** In SkyWater 130nm, `li1` is physical routing layer 1 in the LEF. When FastRoute sees 0% derating on `met1`, it routes global signals across cell pin landing pads. FastRoute now reserves 50% of `met1` tracks, allowing TritonRoute to complete pin access without "stubborn tiles" deadlock.
- **Strict Boolean Types:** LibreLane 3 rejects integer coercion for booleans (`Refusing to automatically convert '1' at 'RUN_CTS' to a Boolean`). Pure booleans ensure uninterrupted headless CI execution.

### [Current Pipeline State]
- **Sept 23 Golden Archive:** 100% PRESERVED in `archive/sept23_openlane2_golden/`, tag `v-sept23-openlane2-signoff`, and branch `archive/sept23-openlane2-signoff`.
- **Active Branch:** `test/option2-recoded` (testing true 50% `met1` derate on current 72% density netlist).
- **Run #38 Status:** Dispatched to GitHub Actions on `ttsky26d`.

### [Next Steps]
1. Monitor **Run #38** on GitHub Actions (`https://github.com/hyleelyh/CIMTinyTO/actions`).
2. Confirm TritonRoute converges quickly with 50% `met1` routing headroom.
3. If Run #38 passes:
   - Submit immediately to the Tiny Tapeout `sky26d` portal to lock in and assign wafer real estate.
   - Once space is assigned, create fresh branch `test/path-b-streamlined` to implement Path B in a new chat session.
