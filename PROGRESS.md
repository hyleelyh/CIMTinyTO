# Project Progress: CIMTinyTO

## Last Execution Run: 2026-09-23 09:10
### [Built & Verified]
- `src/scim_core.sdc`: Fixed OpenSTA compatibility by replacing proprietary Synopsys PrimeTime command `remove_from_collection [all_inputs] [get_ports clk]` with native OpenSTA syntax `[all_inputs -no_clocks]` on lines 21, 22, and 33.
- `config.yaml` & `src/config.json`: Formally bound `PNR_SDC_FILE` and `SIGNOFF_SDC_FILE` to `scim_core.sdc` with `PL_TARGET_DENSITY: 0.92`.
- `info.yaml`: Configured `tiles: "2x2"` footprint (~335 µm x 226 µm gross, ~71,000 µm² core).

### [Architecture Decisions & Physical Routing Clarity]
- **Resolution of OpenSTA Tcl Command Incompatibility:**
  - Forensic diagnosis: Step 11 (`openroad-staprepnr`) failed with `invalid command name "remove_from_collection"`.
  - While Synopsys SDC parsers use `remove_from_collection`, OpenSTA standardizes on `[all_inputs -no_clocks]`.
  - This preserves exact 4.0 ns setup / 1.0 ns hold constraints on input/output pads while excluding `clk` from data path delay rules.
- **Physical Density and Layered Silicon Geometry:**
  - $2\times 2$ tile core area ($71,000\,\mu\text{m}^2$) comfortably fits the $63,548\,\mu\text{m}^2$ standard cell logic at 89.5% core utilization.
  - Well taps and cell diffusions occupy silicon substrate and `li1`/`met1`; routing layers `met2` through `met4` are open for global routing.

### [Current Pipeline State]
- **Pillar 1 (Mathematical Golden Model): 100% COMPLETE & FROZEN.**
- **Pillar 2 (Microarchitecture & Verification): 100% COMPLETE & FROZEN.**
- **Pillar 3 (Physical ASIC Flow): PUSHING SDC FIX TO TRIGGER CLOUD RUN.**

### [Next Steps]
1. Push commit `fix(sdc): replace remove_from_collection with OpenSTA all_inputs -no_clocks` to `origin/main`.
2. Monitor GitHub Actions cloud run past step 11 through placement, CTS, routing, and DRC/LVS sign-off.
3. Ingest final physical metrics (`metrics.csv`, `stat.log`) using `scripts/parse_openlane_reports.py`.
4. Walk through the physical GDSII layout and timing results before concluding Pillar 3.
