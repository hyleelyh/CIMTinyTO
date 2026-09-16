# Project Progress: CIMTinyTO

## Last Execution Run: 2026-09-15 21:12
### [Built & Documented]
- `scripts/audit_test_vectors.py`: Standalone verification and audit CLI script that validates `model/test_vectors_gate0.json` structural dimensions ($16 \times 16$), dynamic range limits ($[-4096, +4095]$), and metadata without shell quoting or tokenizer syntax errors.
- `docs/sky130.lyp`: Official 242 KB SkyWater 130nm KLayout Layer Properties XML file bundled for native GDSII layout visualization (`klayout <design.gds> -l docs/sky130.lyp`).
- `docs/tutorial_galois_lfsr.md`: Pedagogical tutorial on Galois vs. Fibonacci LFSRs, $\text{GF}(2)$ primitive polynomial $x^8 + x^6 + x^5 + x^4 + 1$ (`0xB8`), cycle trace, zero-state lockup prevention, spatial stride-15 seed spacing vs. temporal phase rolling, and synthesizable Verilog implementation.
- `docs/tutorial_wallace_tree_42_compressor.md`: Pedagogical tutorial on 16-row column reduction, 4:2 compressor Boolean equations, zero horizontal carry propagation, 4-bit vector merge adder, and SkyWater 130nm NLDM gate delay breakdown (`sky130_fd_sc_hd__fa_1` $\approx 0.23\text{ ns}$ carry vs. `sky130_fd_sc_hd__xor2_1` $\approx 0.15\text{ ns}$ intrinsic / $\approx 0.25\text{ ns}$ wire-loaded).
- `docs/tools_and_execution_environment_matrix.md`: Formally adopted Native Host Front-End (Pillars 1–3: `.venv`, `verilator`, `cocotb`) + Tiny Tapeout Cloud CI (Pillars 4–6: OpenLane 2 GitHub Actions) + Native KLayout 0.30.9. Formally removed `IIC-OSIC-TOOLS` / local Docker dependencies.
- `model/sim_scim.py`: Verified Python Golden Reference Model (Gate 0) with all self-tests passing.
- `model/test_vectors_gate0.json`: 8 golden stimulus/response test vectors for downstream Gate 1–3 verification.
- **Microarchitectural Foundations & Theoretical Formalization:**
  - **End-to-End Data Precision Lifecycle:** Fully formalized FPGA $\leftrightarrow$ ASIC data transformation across ResNet image recognition (unfolded `uint8` $0\dots 255$ with scale $S = 1/255 \to$ 1-bit temporal Bernoulli stream $\to$ 2-bit tri-state step $\{-1, 0, +1\} \to$ 5-bit spatial Wallace delta $0\dots 16 \to$ 13-bit signed accumulator $-4096\dots +4095 \to$ 16-bit serialized readback $\to$ 32-bit BRAM multi-block partial sum accumulation $\to$ re-quantized `uint8`).
  - **2D Hybrid Spatial-Temporal Commutation:** Mathematically proved the Fubini summation swap $\sum_i \sum_t = \sum_t \sum_i$, where the 16-to-5 Wallace tree is 100% spatial ($<1.25\text{ ns}$ combinational column reduction) and the accumulator is 100% temporal (256 sequential clock cycles).
  - **LFSR Stream Determinism & Randomness:** Formulated the mathematical proof demonstrating that the Galois LFSR comparator output for $A=180$ is 100% deterministic (Hamiltonian cycle visits every integer $1\dots 255$ exactly once, guaranteeing identically 180 ones over 256 cycles with 0% variance).
  - **The Correlation / Squaring Problem ($A \times A \ne A^2$):** Analyzed the Boolean idempotency trap ($x \land x = x$) and proved that stride-15 spatial phase separation ensures $|r_{ij}| \le 0.0259 \ll 0.05$, preventing squaring distortion and guaranteeing true multiplication linearity across all 16 channels.
  - **Monte Carlo Precision Scaling vs. Full-Period Collapse:** Formulated the Central Limit Theorem error scaling ($\text{RMSE} \propto 1/\sqrt{N}$) across intermediate truncations ($N=16, 32, 64, 128$) and validated full-period collapse at $N=256$ ($\text{RMSE} = 0.00057$, $\text{SNR} = 48.03\text{ dB}$).
  - **Golden Model-Driven Verification Flow:** Established the universal test vector cascade (`model/test_vectors_gate0.json`) linking Python math $\to$ Cocotb RTL $\to$ Gate-Level Netlist $\to$ Physical Silicon, with coverage targeting reset integrity, cross-talk, dynamic range ceiling ($\pm 4080$), sign extension, switching noise (`0xAA55`), and mission-mode inference.
  - **Dynamic Power & Sparsity Benchmarking (`sparsity_pct`):** Formalized the physical mapping of test vector `sparsity_pct` to CMOS dynamic power $P = \alpha C V^2 f$, establishing the post-silicon current benchmark ($\sim 2.5\text{ mA}$ at $95.66\%$ sparsity vs. $\sim 10\text{ mA}$ at $0\%$ sparsity).

### [Architecture Decisions]
- **Unified Reconfigurable PE Architecture:** Formally adopted a single $16 \times 16$ PE array (256 PEs total) with a static 2-bit configuration signal `mode[1:0]`, avoiding 3 separate physical arrays and saving $>65\%$ silicon area, routing tracks, and weight DFFs.
- **Boolean Sub-Expression Sharing:** Synthesizer maps PE logic to only 2–3 standard cells per PE by sharing $(a \land w)$ across Mode 0 (Unipolar) and Mode 2 (Hybrid ReLU), yielding an ultracompact footprint ($\sim 10\text{--}15\text{ }\mu\text{m}^2$).
- **Zero Dynamic Multiplexer Power:** Because `mode[1:0]` is a static configuration signal frozen across the 256-cycle compute phase, the MUX select lines have an activity factor $\alpha = 0$, consuming zero dynamic switching power.
- **Tooling Strategy Finalization:** Eliminated `IIC-OSIC-TOOLS` from flow; Tiny Tapeout official GitHub Actions CI provides reproducible, pinned OpenLane 2 tapeout sign-off with zero local Docker overhead. Native KLayout (v0.30.9) with integrated GPU acceleration verified for interactive GDSII verification.
- **Galois LFSR Seed Mechanics:** Confirmed hardwired spatial static seed offsets (stride-15) save $\sim 300$ standard cells vs. programmable shadow registers. Temporal phase shifts (+1 state per 256-cycle tile) naturally decorrelate consecutive tiles without software overhead.
- **4:2 Compressor & Adder Timing:** Wallace tree reduces 16 inputs to sum & carry in 2 stages ($2 \times T_{4:2} \approx 0.8\text{ ns}$), followed by 4-bit vector merge adder ($\approx 0.42\text{ ns}$), yielding total column reduction delay of $\approx 1.22\text{ ns}$ (well within $20\text{ ns}$ clock cycle at $50\text{ MHz}$).
- **Accumulator Bit-Growth:** Upgraded from 12-bit signed to 13-bit signed two's complement ($-4096\dots +4095$) to ensure zero saturation distortion during worst-case bipolar/hybrid extreme saturation ($16 \times 256 = 4096$).

### [Current Pipeline State]
- **Pillar 1 (Gate 0) Fully Complete, Verified & Frozen:**
  - EDA hygiene scripts (`scripts/parse_yosys_stat.py`, `scripts/parse_openlane_reports.py`, `scripts/audit_test_vectors.py`) functional and passing self-tests.
  - Python Golden Reference Model (`model/sim_scim.py`) functional and passing all 4 verification suites.
  - Golden stimulus/response vectors exported in `model/test_vectors_gate0.json` and audited with 100% pass rate.
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
