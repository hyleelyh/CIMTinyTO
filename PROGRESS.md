# Project Progress: CIMTinyTO

## Last Execution Run: 2026-09-13 20:30
### [Built & Documented]
- `docs/sky130.lyp`: Official 242 KB SkyWater 130nm KLayout Layer Properties XML file bundled for native GDSII layout visualization (`klayout <design.gds> -l docs/sky130.lyp`).
- `docs/tutorial_galois_lfsr.md`: Pedagogical tutorial on Galois vs. Fibonacci LFSRs, $\text{GF}(2)$ primitive polynomial ^8 + x^6 + x^5 + x^4 + 1$ (`0xB8`), cycle trace, zero-state lockup prevention, spatial stride-15 seed spacing vs. temporal phase rolling, and synthesizable Verilog implementation.
- `docs/tutorial_wallace_tree_42_compressor.md`: Pedagogical tutorial on 16-row column reduction, 4:2 compressor Boolean equations, zero horizontal carry propagation, 4-bit vector merge adder, and SkyWater 130nm NLDM gate delay breakdown (`sky130_fd_sc_hd__fa_1` 23\text{ ps}$ carry vs. `sky130_fd_sc_hd__xor2_1` bash.15\text{ ns}$ intrinsic / bash.25\text{ ns}$ wire-loaded).
- `docs/tools_and_execution_environment_matrix.md`: Formally adopted Native Host Front-End (Pillars 1–3: `.venv`, `verilator`, `cocotb`) + Tiny Tapeout Cloud CI (Pillars 4–6: OpenLane 2 GitHub Actions) + Native KLayout 0.30.9. Formally removed `IIC-OSIC-TOOLS` / local Docker dependencies.
- `model/sim_scim.py`: Verified Python Golden Model (Gate 0) with all self-tests passing.
- **Architectural Clarifications & Formal Models:**
  - **Data Type Transitions:** Host `uint8` 255$ $\to$ 1-bit temporal bitstream via 8-bit digital comparator $\to$ 1-bit PE logic gate (AND/XNOR) $\to$ 5-bit Wallace tree 16$ $\to$ 13-bit signed accumulator 4095$ $\to$ 16-bit signed integer host readback.
  - **Cycle Budgeting:** Exactly 256 compute cycles for full 8-bit precision (zero stochastic quantization noise); 32-cycle weight shift (once per layer); 16-cycle activation load; 32-cycle 13-bit accumulator readback.
  - **Large Tensor / Image Tiling:** Validated how arbitrary image dimensions (e.g. 24 \times 224$) and convolutional layers are tiled into 6 \times 16$ sub-blocks by the FPGA orchestrator with partial sums accumulated in FPGA Block RAM (BRAM).

### [Architecture Decisions]
- **Tooling Strategy Finalization:** Eliminated `IIC-OSIC-TOOLS` from flow; Tiny Tapeout official GitHub Actions CI provides reproducible, pinned OpenLane 2 tapeout sign-off with zero local Docker overhead. Native KLayout (v0.30.9) with integrated GPU acceleration verified for interactive GDSII verification.
- **Galois LFSR Seed Mechanics:** Confirmed hardwired spatial static seed offsets (stride-15) save $\sim 300$ standard cells vs. programmable shadow registers. Temporal phase shifts (+1 state per 256-cycle tile) naturally decorrelate consecutive tiles without software overhead.
- **4:2 Compressor & Adder Timing:** Wallace tree reduces 16 inputs to sum & carry in 2 stages ( \times T_{4:2} \approx 0.8\text{ ns}$), followed by 4-bit vector merge adder ($\approx 0.42\text{ ns}$), yielding total column reduction delay of $\approx 1.22\text{ ns}$ (well within 0\text{ ns}$ clock cycle at 0\text{ MHz}$).
- **Accumulator Bit-Growth:** Upgraded from 12-bit signed to 13-bit signed two's complement (4095$) to ensure zero saturation distortion during worst-case bipolar/hybrid extreme saturation (6 \times 256 = 4096$).

### [Current Pipeline State]
- **Pillar 1 (Gate 0) Fully Complete, Verified & Frozen:**
  - EDA hygiene scripts (`scripts/parse_yosys_stat.py`, `scripts/parse_openlane_reports.py`) functional and passing self-tests.
  - Python Golden Reference Model (`model/sim_scim.py`) functional and passing all 4 verification suites.
  - Golden stimulus/response vectors exported in `model/test_vectors_gate0.json`.
  - Architectural specifications, pedagogical tutorials, and layer properties in `docs/`.
- Ready to proceed to **Pillar 2: Parameterized Verilog RTL Implementation** (`src/`) in a clean new chat when user is ready.

### [Next Steps for Pillar 2 (New Chat)]
- Implement parameterized Verilog RTL submodules in `src/`:
  1. `src/lfsr8_galois.v`: 8-bit Galois LFSR with seed parameterization and synchronous active-low reset.
  2. `src/scim_sng_bank.v`: 16-channel comparator bank with decorrelated seed initialization.
  3. `src/scim_pe.v`: Tri-mode PE arithmetic cell.
  4. `src/scim_compressor_42.v` and `src/scim_wallace_tree.v`: 16-row Wallace tree compressor.
  5. `src/scim_accumulator.v`: 13-bit accumulator with saturation and readback.
  6. `src/scim_weight_mem.v`: 256-bit DFF shift register array with ICG clock gating.
  7. `src/tt_um_scim_core.v`: Top-level Tiny Tapeout pinout wrapper.
