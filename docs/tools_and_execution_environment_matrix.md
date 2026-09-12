# Tools & Execution Environment Matrix: Antigravity (AI) & Engineer (You)

This document defines the exact tools, execution environments, and division of labor between **Antigravity (AI Automated Engine)** and **You (Human Chip Lead & Verifier)** across all 7 Pillars of the CIMTinyTO ASIC creation lifecycle.

---

## 1. Pedagogical Pairing & Verification Philosophy

In professional IC design teams, complex tasks are split between the **Implementation Engine** (writing code, generating netlists, running overnight simulations) and the **Chip Lead / Verification Engineer** (auditing architecture, reviewing timing reports, inspecting waveforms, and testing silicon). 

In this project:
* **Antigravity** serves as your high-speed ASIC implementation engine.
* **You** inspect the code in the Antigravity IDE, manually reproduce simulations, inspect waveforms in GTKWave, audit layout in KLayout, and physically bring up the chip on the bench.

---

## 2. Comprehensive Tool & Environment Matrix

| Pillar | Milestone | Environment | Antigravity (Automated Actions) | You (Manual Reproduction & Learning) |
|---|---|---|---|---|
| **Pillar 1** *(Current)* | **System & Mathematical Modeling (Gate 0)** | Local Python Virtual Environment (`.venv`), no Docker | • Implements `model/sim_scim.py`<br>• Sweeps LFSR periods & seed decorrelation<br>• Verifies $1/\sqrt{N}$ convergence & SNR<br>• Generates `model/test_vectors_gate0.json`<br>• Executes parser self-tests | • In Antigravity IDE: Audits Python algorithm<br>• Terminal: Runs `.venv/bin/python model/sim_scim.py`<br>• Observes full-period collapse ($48\text{ dB}$ SNR) & $61.7\%$ power savings<br>• Inspects test vector JSON schema |
| **Pillar 2** | **Microarchitecture & Parameterized RTL** | Native Verilog & Local Linters (`verilator`) | • Implements synthesizable Verilog in `src/`<br>• Sizes registers, 4:2 compressor trees, and ICG clock gating<br>• Runs `verilator --lint-only -Wall`<br>• Enforces synchronous active-low resets | • In Antigravity IDE: Reviews state machine FSMs<br>• Verifies zero inferred latches<br>• Audits Tiny Tapeout pinout mapping (`tt_um_*`)<br>• Analyzes datapath vs control logic trade-offs |
| **Pillar 3** | **Verification & Design for Testability (DFT)** | Local Python (`cocotb`, `pytest`) + Icarus Verilog (`iverilog`) | • Implements Cocotb testbenches in `test/`<br>• Ingests `test_vectors_gate0.json`<br>• Runs automated regression suites via `make`<br>• Injects corner cases (saturation, zero, checkerboard)<br>• Tests MISO shift loopback | • Terminal: Runs `make -C test`<br>• GUI: Opens `dump.vcd` in **GTKWave** or **Surfer**<br>• Traces cycle-by-cycle clock edges, compressor tree outputs, and accumulator increments<br>• Confirms 100% bit-exact match against Gate 0 |
| **Pillar 4** | **Logic Synthesis & Technology Mapping (Gate 2)** | OpenLane / Yosys (`sky130_fd_sc_hd` standard cells) | • Synthesizes RTL to gate-level netlist<br>• Maps to standard cells (NAND, XNOR, DFF, ICG)<br>• Runs `scripts/parse_yosys_stat.py`<br>• Enforces $<30$-line hygiene report<br>• Audits 256 weight DFF preservation | • In Antigravity IDE: Audits cell count table<br>• Confirms no weight registers were pruned<br>• Evaluates gate count vs Tiny Tapeout $1\times 2$ tile area (~1,600–2,000 cells)<br>• Learns standard cell drive strengths (`_1`, `_2`) |
| **Pillar 5** | **Static Timing Analysis (STA)** | OpenSTA / OpenROAD (inside OpenLane container) | • Applies timing constraints (`sdc`) at $25\text{–}50\text{ MHz}$<br>• Analyzes Clock Tree Synthesis (CTS) skew<br>• Runs `scripts/parse_openlane_reports.py`<br>• Evaluates WNS / TNS setup & hold slacks | • Reviews STA timing tables in Antigravity IDE<br>• **Hard Silicon Check:** Confirms $T_{\text{slack, hold}} \ge 0.00\text{ ns}$<br>• Traces critical timing paths (Wallace tree XOR chain to accumulator DFF setup time)<br>• Learns PVT corner margins (slow/fast) |
| **Pillar 6** | **Physical Design & Sign-Off (PnR, DRC, LVS)** | OpenLane 2 / OpenROAD (`docker` / `IICDocker`), Magic, Netgen, KLayout | • Configures `config.yaml` floorplan & power rings<br>• Drives macro placement, CTS, and detailed routing<br>• Inserts antenna diodes<br>• Runs Magic DRC, Netgen LVS, and GDSII generation | • GUI: Launches **KLayout** to view final GDSII layout<br>• Inspects standard-cell placement density ($\approx 58.8\%$ target)<br>• Observes power routing (VDD/VSS rails on met4/met5)<br>• Audits DRC = 0 and LVS = 0 sign-off reports |
| **Pillar 7** | **Silicon Bring-Up & Hardware Characterization** | Physical Lab Bench: RP2040 Carrier + PYNQ-Z2 FPGA via PMOD | • Generates MicroPython/C carrier test firmware<br>• Generates PYNQ-Z2 Vivado overlay bitstream & Python driver (`pynq.Overlay`)<br>• Prepares automated UART/USB test scripts | • Hardware: Plugs USB-C into RP2040 carrier board<br>• Connects 3.3V PMOD cable between PYNQ-Z2 and ASIC<br>• Runs Jupyter Notebook on PYNQ ARM Linux<br>• Logic Analyzer: Hooks PulseView/Sigrok to `uo_out`<br>• Validates live Micro-ResNet classification on silicon! |

---

## 3. Hands-On Verification Commands for You

### To reproduce Pillar 1 on your PC or Laptop:
```bash
# 1. Activate the local virtual environment
source .venv/bin/activate

# 2. Run the automated parser self-tests (<30 lines output)
python3 scripts/parse_yosys_stat.py --test
python3 scripts/parse_openlane_reports.py --test

# 3. Run the complete Gate 0 Golden Model & generate test vectors
python3 model/sim_scim.py
```

### Key Things to Inspect in Antigravity IDE:
1. Open `model/sim_scim.py`:
   - Line 37: `LFSR8` Galois polynomial (`0xB8`) and zero-seed lockup guardrail.
   - Line 88: `SNGArray` stride-15 seed spacing.
   - Line 163: `ProcessingElement` tri-mode arithmetic and Hybrid ReLU zero-switching hold.
   - Line 253: `Accumulator13Bit` dynamic range calculation ($16 \times 256 = 4096$).
2. Open `model/test_vectors_gate0.json`:
   - Inspect the 8 test vectors, including the quantized Micro-ResNet layer with $60\%$ ReLU sparsity.
