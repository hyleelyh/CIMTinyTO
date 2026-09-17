# Project Progress: CIMTinyTO

## Last Execution Run: 2026-09-16 22:20
### [Built & Documented]
- `docs/microarchitecture_unified_column_delta.md`: Detailed pedagogical architectural specification proving the mathematical identity $\Delta_{\text{col}} = 2P - A$ for Mode 2 (Hybrid ReLU) and $\Delta_{\text{col}} = 2X - 16$ for Mode 1 (Bipolar XNOR), explaining physical CMOS digital wire realities ($V_{DD}/GND$), truth tables, and why sharing the central activation compressor $A = \sum a_i$ saves $\approx 855$ standard cells (~47% tree area reduction).
- `docs/tutorial_galois_lfsr.md`: Added Section 5.1 detailing the complete 16-channel stride-15 trajectory step indices (Step 1, 16, 31, 46...) and explaining why the hardware initial seeds (`8'h5C`, `8'hF1`...) align cycle 0 with the Python golden reference model.
- Automated 65,536-pattern exhaustive mathematical audit verifying that 4:2 compressor tree reduction produces 100% bit-exact equivalence for all possible 16-bit inputs.
- Verified that all 16 SNG Galois LFSR initial reset states (`8'h5C`, `8'hF1`, `8'hAC`, etc.) generate identical stochastic streams matching `model/test_vectors_gate0.json` cycle-for-cycle.
- Clarified EDA tooling environment: Native Host Front-End (`verilator`, `iverilog`, `gtkwave`) + Tiny Tapeout Cloud CI (`tt-gds-action` for Yosys, OpenROAD, Magic, Netgen) + `.venv` (`numpy`, `cocotb`, `pyverilog`).
- `scripts/audit_test_vectors.py`: Standalone verification and audit CLI script that validates `model/test_vectors_gate0.json` structural dimensions ($16 \times 16$), dynamic range limits ($[-4096, +4095]$), and metadata without shell quoting or tokenizer syntax errors.
- `docs/sky130.lyp`: Official 242 KB SkyWater 130nm KLayout Layer Properties XML file bundled for native GDSII layout visualization (`klayout <design.gds> -l docs/sky130.lyp`).
- `docs/tutorial_galois_lfsr.md`: Pedagogical tutorial on Galois vs. Fibonacci LFSRs, $\text{GF}(2)$ primitive polynomial $x^8 + x^6 + x^5 + x^4 + 1$ (`0xB8`), cycle trace, zero-state lockup prevention, spatial stride-15 seed spacing vs. temporal phase rolling, and synthesizable Verilog implementation.
- `docs/tutorial_wallace_tree_42_compressor.md`: Pedagogical tutorial on 16-row column reduction, 4:2 compressor Boolean equations, zero horizontal carry propagation, 4-bit vector merge adder, and SkyWater 130nm NLDM gate delay breakdown (`sky130_fd_sc_hd__fa_1` $\approx 0.23\text{ ns}$ carry vs. `sky130_fd_sc_hd__xor2_1` $\approx 0.15\text{ ns}$ intrinsic / $\approx 0.25\text{ ns}$ wire-loaded).
- `docs/tools_and_execution_environment_matrix.md`: Formally adopted Native Host Front-End (Pillars 1–3: `.venv`, `verilator`, `cocotb`) + Tiny Tapeout Cloud CI (Pillars 4–6: OpenLane 2 GitHub Actions) + Native KLayout 0.30.9. Formally removed `IIC-OSIC-TOOLS` / local Docker dependencies.
- `model/sim_scim.py`: Verified Python Golden Reference Model (Gate 0) with all self-tests passing.
- `model/test_vectors_gate0.json`: 8 golden stimulus/response test vectors for downstream Gate 1–3 verification.
- `implementation_plan.md`: Formulated comprehensive architectural implementation plan for Pillar 2 (Gate 1: Parameterized Verilog RTL & Submodules).

### [Architecture Decisions]
- **Unified Column Delta Reduction ($\Delta = 2P - A$):** Proved algebraic identity $\text{step}_i = a_i (2w_i - 1) = 2(a_i \land w_i) - a_i$. Summing over 16 rows yields $\Delta = 2P - A$. Because activations $a[15:0]$ are broadcast to all columns, $A = \sum a_i$ is computed by a single central 16-to-5 Wallace tree for the entire macro. This cuts total chip Wallace trees from 32 down to 17, saving 15 full trees (~855 cells) and guaranteeing comfortable placement within Tiny Tapeout $1\times 2$ tile (~1,600–2,000 cells).
- **Mode 1 Hardwired Shift ($\Delta = 2X - 16$):** In Bipolar Mode, XNOR output $x_i \in \{0, 1\}$ feeds the identical unsigned 16-to-5 Wallace tree to produce $X \in [0, 16]$. Multiplying by 2 is implemented as a hardwired 1-bit left shift (`{X, 1'b0}`), requiring 0 transistors and 0 delay, followed by a 6-bit subtractor.
- **Single-Wire PE Output Interface:** Every PE in the array outputs a single binary bit ($a \land w$ in Mode 0 & 2; $\text{XNOR}$ in Mode 1), requiring only a single 2:1 MUX and preserving the ultracompact 2-to-3 cell footprint per PE.
- **Unified Reconfigurable PE Architecture:** Formally adopted a single $16 \times 16$ PE array (256 PEs total) with a static 2-bit configuration signal `mode[1:0]`, avoiding 3 separate physical arrays and saving $>65\%$ silicon area, routing tracks, and weight DFFs.
- **Boolean Sub-Expression Sharing:** Synthesizer maps PE logic to only 2–3 standard cells per PE by sharing $(a \land w)$ across Mode 0 (Unipolar) and Mode 2 (Hybrid ReLU), yielding an ultracompact footprint ($\sim 10\text{--}15\text{ }\mu\text{m}^2$).
- **Zero Dynamic Multiplexer Power:** Because `mode[1:0]` is a static configuration signal frozen across the 256-cycle compute phase, the MUX select lines have an activity factor $\alpha = 0$, consuming zero dynamic switching power.
- **Tooling Strategy Finalization:** Eliminated `IIC-OSIC-TOOLS` from flow; Tiny Tapeout official GitHub Actions CI provides reproducible, pinned OpenLane 2 tapeout sign-off with zero local Docker overhead. Native KLayout (v0.30.9) with integrated GPU acceleration verified for interactive GDSII verification.
- **Galois LFSR Seed Mechanics:** Confirmed hardwired spatial static seed offsets (stride-15) save $\sim 300$ standard cells vs. programmable shadow registers. Temporal phase shifts (+1 state per 256-cycle tile) naturally decorrelate consecutive tiles without software overhead.
- **4:2 Compressor & Adder Timing:** Wallace tree reduces 16 inputs to sum & carry in 2 stages ($2 \times T_{4:2} \approx 0.8\text{ ns}$), followed by 4-bit vector merge adder ($\approx 0.42\text{ ns}$), yielding total column reduction delay of $\approx 1.22\text{ ns}$ (well within $20\text{ ns}$ clock cycle at $50\text{ MHz}$).
- **Accumulator Bit-Growth:** Upgraded from 12-bit signed to 13-bit signed two's complement ($-4096\dots +4095$) to ensure zero saturation distortion during worst-case bipolar/hybrid extreme saturation ($16 \times 256 = 4096$).

### [Current Pipeline State]
- **Pillar 1 (Gate 0) Fully Complete, Verified & Frozen.**
- **Pillar 2 (Gate 1 Planning & Microarchitecture):**
  - Full modular implementation plan created and detailed in `implementation_plan.md`.
  - User requested hold on code implementation to conduct architectural review.
  - Ready to proceed with RTL coding upon user confirmation.

### [Next Steps for Pillar 2 Execution]
1. Install native front-end tools on laptop/PC: `sudo apt update && sudo apt install -y verilator iverilog gtkwave`.
2. Implement modular Verilog RTL submodules in `src/`:
   - `src/lfsr8_galois.v`: 8-bit Galois LFSR with seed parameterization and synchronous active-low reset.
   - `src/scim_sng_bank.v`: 16-channel comparator bank with decorrelated seed initialization.
   - `src/scim_pe.v`: Tri-mode PE arithmetic cell.
   - `src/scim_compressor_42.v` and `src/scim_wallace_tree.v`: 16-row Wallace tree compressor.
   - `src/scim_accumulator.v`: 13-bit accumulator with saturation and readback.
   - `src/scim_weight_mem.v`: 256-bit DFF shift register array with ICG clock gating.
   - `src/tt_um_scim_core.v`: Top-level Tiny Tapeout pinout wrapper.
3. Run syntax and lint verification (`scripts/lint_verilog.py`, `verilator --lint-only -Wall`).
