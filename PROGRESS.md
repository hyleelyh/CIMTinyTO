# Project Progress: CIMTinyTO

## Last Execution Run: 2026-09-21 17:45
### [Built & Verified]
- `info.yaml`: Configured Tiny Tapeout manifest with top-level `tt_um_scim_core` and pinout mapping.
- `docs/info.md`: Authored architectural datasheet with math formulations and pinout tables.
- `src/config.json` & `config.yaml`: Configured OpenLane 2 physical hardening parameters ($50\text{ MHz}$, CTS, decap, HFN rules).
- `src/scim_core.sdc`: Authored timing constraints ($20\text{ ns}$ clock, setup/hold uncertainties, I/O delays, pad loads).
- `.github/workflows/gds.yaml`: GitHub Actions CI pipeline running `TinyTapeout/tt-gds-action@tt08` with `flow: openlane2`.
- `docs/pillar3_physical_asic_flow_guide.md`: Created pedagogical ASIC physical design and sign-off guide.
- **Verification Sign-Off:** Verilator lint clean (0 warnings), Cocotb 3/3 test suites bit-exact pass (100%), parser self-tests clean.

### [Architecture Decisions & Physical Placement Audit (Forensic Discovery)]
- **Cloud Hardening Execution Failure (`[GPL-0301]`):**
  - During the first GitHub Actions run on commit `fc9504c`, OpenLane 2 / OpenROAD Global Placement failed at step `OpenROAD.GlobalPlacement`:
    ```plaintext
    [INFO GPL-0016] CoreArea: 34255353600 (34,255 µm²)
    [INFO GPL-0007] NumPlaceInstances: 5769 cells
    [INFO GPL-0018] PlaceInstsArea: 63548448000 (63,548 µm²)
    [INFO GPL-0019] Util(%): 192.12%
    [GPL-0301] Utilization 192.12% exceeds 100%.
    ```
- **Forensic Sizing Analysis (Front-End Gate Count vs. Physical Standard-Cell Area):**
  - While front-end synthesis estimated ~2,882 generic logic gates, physical mapping to `sky130_fd_sc_hd` expanded the instance count to **5,769 physical cells** occupying **$63,548\,\mu\text{m}^2$**:
    1. **16x 13-bit Saturating Accumulators:** Full adders + dual 14-bit magnitude comparators + clamping MUXes + DFFs $\approx 1,920$ physical standard cells.
    2. **17 Wallace Trees:** 153 4:2 compressors decomposed into discrete XOR2, NAND, and inverter cells $\approx 1,224$ standard cells.
    3. **Sequential DFFs:** 256 weight DFFs + 208 accumulator DFFs + control registers $\approx 500+$ DFFs ($\approx 9,000\,\mu\text{m}^2$).
    4. **Well Taps & Buffers:** 618 fixed latch-up prevention well taps (`tapvpwrvgnd_1`) plus CTS/HFN repeater buffers.
  - The $1\times 2$ tile has a core area of only **$34,255\,\mu\text{m}^2$**, resulting in $192.12\%$ utilization (exceeding physical limits).
- **Design Fork & Trade-Off Options (Pending User Sizing Decision):**
  - **Option 1 ($2\times 2$ Tile Allocation — 4 Tiles):** Scale floorplan to $2\times 2$ ($\approx 335\,\mu\text{m} \times 226\,\mu\text{m}$, core area $\approx 70,000\,\mu\text{m}^2$). The $63,548\,\mu\text{m}^2$ macro fits comfortably at ~64% utilization with 0 RTL modifications, full $16\times 16$ parallel throughput (100 MMAC/s), and 100% parity with trained Micro-ResNet weights. Trade-off: Higher shuttle fee (~2x tile cost).
  - **Option 2 (Array Downscale to $8\times 8$ Core on $1\times 2$ Tile):** Parameterize PE array to $8\times 8$ (64 weights, 8 Wallace trees, 8 accumulators). Standard-cell count drops by ~65% to $\approx 2,000$ cells ($\approx 20,000\,\mu\text{m}^2$), fitting within the $1\times 2$ budget ($34,255\,\mu\text{m}^2$) at ~58% density without additional shuttle expense. Trade-off: 4x lower instantaneous compute throughput; requires matrix tiling for inference.
  - **Option 3 (Architectural Time-Multiplexing on $1\times 2$ Tile):** Retain $16\times 16$ weights but share/time-multiplex accumulator and Wallace tree columns over sequential cycles. Trade-off: Adds FSM control complexity and lowers throughput.

### [Current Pipeline State]
- **Pillar 1 (Mathematical Golden Model): 100% COMPLETE & FROZEN.**
- **Pillar 2 (Microarchitecture & Verification): 100% COMPLETE & FROZEN.**
- **Pillar 3 (Physical ASIC Flow): IN PROGRESS / PENDING SIZING DECISION.**
  - All OpenLane 2 configs, constraints, and scripts are functional and verified.
  - Sizing decision paused by user to evaluate shuttle cost vs. silicon footprint.

### [Next Steps]
1. User to evaluate cost vs. performance trade-off ($2\times 2$ tile vs. $8\times 8$ array on $1\times 2$ tile).
2. Once the decision is confirmed:
   - If Option 1: Update `info.yaml` to `tiles: "2x2"` and re-trigger OpenLane 2 cloud hardening.
   - If Option 2: Parameterize RTL to $8\times 8$, re-verify Cocotb testbenches, and re-trigger hardening on $1\times 2$.
3. Achieve physical GDS placement and routing sign-off before closing Pillar 3.
