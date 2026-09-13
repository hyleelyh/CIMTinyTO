# Project Progress: CIMTinyTO

## Last Execution Run: 2026-09-12 22:17
### [Built]
- `docs/tutorial_galois_lfsr.md`: Pedagogical tutorial on Galois vs. Fibonacci LFSRs, $\text{GF}(2)$ primitive polynomial ^8 + x^6 + x^5 + x^4 + 1$ (`0xB8`), cycle-by-cycle state trace, zero-state lockup prevention, spatial stride-15 seed spacing vs. temporal phase rolling, and synthesizable Verilog implementation.
- `docs/tutorial_wallace_tree_42_compressor.md`: Pedagogical tutorial on 16-row column reduction, 4:2 compressor Boolean equations, zero horizontal carry propagation, 4-bit vector merge adder, and SkyWater 130nm NLDM gate delay breakdown (`sky130_fd_sc_hd__fa_1` 23\text{ ps}$ carry vs. `sky130_fd_sc_hd__xor2_1` bash.15\text{ ns}$ intrinsic / bash.25\text{ ns}$ wire-loaded).
- `docs/tools_and_execution_environment_matrix.md`: Formally adopted Native Host Front-End (Pillars 1–3: `.venv`, `verilator`, `cocotb`) + Tiny Tapeout Cloud CI (Pillars 4–6: OpenLane 2 GitHub Actions) + Native KLayout 0.30.9. Formally removed `IIC-OSIC-TOOLS` / local Docker dependencies.
- `docs/sky130.lyp`: Official 242 KB SkyWater 130nm KLayout Layer Properties XML file for native GDSII layout visualization.
- `model/sim_scim.py`: Clarified 12-bit dynamic range annotation for Mode 0 Unipolar AND.

### [Architecture Decisions]
- **Tooling Strategy Finalization:** Eliminated `IIC-OSIC-TOOLS` from flow; Tiny Tapeout official GitHub Actions CI provides reproducible, pinned OpenLane 2 tapeout sign-off with zero local Docker overhead. Native KLayout (v0.30.9) with integrated GPU acceleration verified for interactive GDSII verification.
- **Galois LFSR Seed Mechanics:** Confirmed hardwired spatial static seed offsets (stride-15) save $\sim 300$ standard cells vs. programmable shadow registers. Temporal phase shifts (+1 state per 256-cycle tile) naturally decorrelate consecutive tiles without software overhead.
- **4:2 Compressor & Adder Timing:** Wallace tree reduces 16 inputs to sum & carry in 2 stages ( \times T_{4:2} \approx 0.8\text{ ns}$), followed by 4-bit vector merge adder ($\approx 0.42\text{ ns}$), yielding total column reduction delay of $\approx 1.22\text{ ns}$ (well within 0\text{ ns}$ clock cycle at 0\text{ MHz}$).
- **Accumulator Bit-Growth:** Upgraded from 12-bit signed to 13-bit signed two's complement (4095$) to ensure zero saturation distortion during worst-case bipolar/hybrid extreme saturation (6 \times 256 = 4096$).

### [Current Pipeline State]
- **Pillar 1 (Gate 0) Fully Complete & Verified:**
  - EDA hygiene scripts (`scripts/parse_yosys_stat.py`, `scripts/parse_openlane_reports.py`) functional and passing self-tests.
  - Python Golden Reference Model (`model/sim_scim.py`) functional and passing all 4 verification suites.
  - Golden stimulus/response vectors exported in `model/test_vectors_gate0.json`.
  - Architectural tutorials & environment documentation finalized in `docs/`.
- Ready to proceed to **Pillar 2: Parameterized Verilog RTL Implementation** (`src/`) upon user approval.

### [Next Steps]
- Implement parameterized Verilog RTL submodules in `src/`:
  - `src/lfsr8_galois.v`: 8-bit Galois LFSR with seed parameterization and synchronous active-low reset.
  - `src/scim_sng_bank.v`: 16-channel comparator bank with decorrelated seed initialization.
  - `src/scim_pe.v`: Tri-mode PE arithmetic cell.
  - `src/scim_compressor_42.v` and `src/scim_wallace_tree.v`: 16-row Wallace tree compressor.
  - `src/scim_accumulator.v`: 13-bit accumulator with saturation and readback.
  - `src/scim_weight_mem.v`: 256-bit DFF shift register array with ICG clock gating.
  - `src/tt_um_scim_core.v`: Top-level Tiny Tapeout pinout wrapper.
