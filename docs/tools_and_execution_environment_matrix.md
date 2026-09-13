# Tools & Execution Environment Matrix: Antigravity (AI) & Engineer (You)

This document defines the exact tools, execution environments, and division of labor between **Antigravity (AI Automated Engine)** and **You (Human Chip Lead & Verifier)** across all 7 Pillars of the CIMTinyTO ASIC creation lifecycle.

---

## 1. Pedagogical Pairing & Verification Philosophy

In professional IC design teams, complex tasks are split between the **Implementation Engine** (writing code, generating netlists, running overnight simulations) and the **Chip Lead / Verification Engineer** (auditing architecture, reviewing timing reports, inspecting waveforms, and testing silicon). 

In this project:
* **Antigravity** serves as your high-speed ASIC implementation engine.
* **You** inspect the code in the Antigravity IDE, manually reproduce simulations, inspect waveforms in GTKWave, audit layout in native KLayout, and physically bring up the chip on the bench.

---

## 2. Streamlined Architecture: 100% Native + Tiny Tapeout Cloud CI

We adopt a clean, friction-free toolchain that completely eliminates local Docker version conflicts and heavy 20 GB disk downloads:

1. **Front-End & Verification (Pillars 1, 2, 3):**
   - 100% Native Host OS (`.venv`, `verilator`, `cocotb`, `iverilog`, `gtkwave`).
   - Runs in milliseconds on both your PC and Laptop.
2. **Physical Synthesis, STA, & PnR Sign-off (Pillars 4, 5, 6):**
   - **Tiny Tapeout Official Cloud CI (`tt-gds-action` on GitHub Actions).**
   - Authoritative source of truth for DRC (0 errors), LVS (0 errors), positive hold slack, and final GDSII generation.
   - Pinned to the exact shuttle multiplexer rules.
3. **Silicon Layout Inspection (Pillar 6):**
   - **Native Local KLayout (v0.30.9).**
   - Opens the downloaded GDSII artifact smoothly using your PC/Laptop integrated graphics.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   CIMTinyTO Flow Architecture                          │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
               ┌────────────────────────────┴────────────────────────────┐
               ▼                                                         ▼
    [Pillars 1, 2, 3: Front-End]                              [Pillars 4, 5, 6: Physical]
   • Native Host Python (.venv)                              • Tiny Tapeout Official Cloud CI
   • Verilog RTL Editing & Lint                                (Automated PnR & GDSII Sign-Off)
   • Local Cocotb / iverilog Simulation                                  │
                                                                         ▼
                                                              [Layout Inspection]
                                                             • Native Local KLayout 0.30.9
                                                               (Smooth Integrated GPU Viewing)
```

---

## 3. Comprehensive Tool & Environment Matrix Across All 7 Pillars

| Pillar | Milestone | Environment | Antigravity (Automated Actions) | You (Manual Reproduction & Learning) |
|---|---|---|---|---|
| **Pillar 1** *(Completed)* | **System & Mathematical Modeling (Gate 0)** | **Native Host OS:** Local Python Virtual Environment (`.venv`) | • Implements `model/sim_scim.py`<br>• Sweeps LFSR periods & seed decorrelation<br>• Verifies $1/\sqrt{N}$ convergence & SNR<br>• Generates `model/test_vectors_gate0.json`<br>• Executes parser self-tests | • In Antigravity IDE: Audits Python algorithm<br>• Terminal: Runs `.venv/bin/python model/sim_scim.py`<br>• Observes full-period collapse ($48\text{ dB}$ SNR) & $61.7\%$ power savings<br>• Inspects test vector JSON schema |
| **Pillar 2** *(Next)* | **Microarchitecture & Parameterized RTL** | **Native Host OS:** Verilog (IEEE 1364-2001) + `verilator` linter | • Implements synthesizable Verilog in `src/`<br>• Sizes registers, 4:2 compressor trees, and ICG clock gating<br>• Runs `verilator --lint-only -Wall`<br>• Enforces synchronous active-low resets | • In Antigravity IDE: Reviews state machine FSMs<br>• Verifies zero inferred latches<br>• Audits Tiny Tapeout pinout mapping (`tt_um_*`)<br>• Analyzes datapath vs control logic trade-offs |
| **Pillar 3** | **Verification & Design for Testability (DFT)** | **Native Host:** Python (`cocotb`, `pytest`) + Icarus Verilog (`iverilog`) | • Implements Cocotb testbenches in `test/`<br>• Ingests `test_vectors_gate0.json`<br>• Runs automated regression suites via `make`<br>• Injects corner cases (saturation, zero, checkerboard)<br>• Tests MISO shift loopback | • Terminal: Runs `make -C test`<br>• GUI: Opens `dump.vcd` in **GTKWave** or **Surfer**<br>• Traces cycle-by-cycle clock edges, compressor tree outputs, and accumulator increments<br>• Confirms 100% bit-exact match against Gate 0 |
| **Pillar 4** | **Logic Synthesis & Technology Mapping (Gate 2)** | **Tiny Tapeout Cloud CI** + Local Hygiene Audit (`scripts/parse_yosys_stat.py`) | • Prepares `config.yaml` & cell mapping<br>• Triggers synthesis hardening CI on push<br>• Runs `scripts/parse_yosys_stat.py`<br>• Audits 256 weight DFF preservation (<30 lines) | • In Antigravity IDE: Audits cell count table<br>• Confirms no weight registers were pruned<br>• Evaluates gate count vs Tiny Tapeout $1\times 2$ tile area (~1,600–2,000 cells)<br>• Learns standard cell drive strengths (`_1`, `_2`) |
| **Pillar 5** | **Static Timing Analysis (STA)** | **Tiny Tapeout Cloud CI** (OpenSTA / OpenROAD) | • Applies timing constraints (`sdc`) at $25\text{–}50\text{ MHz}$<br>• Analyzes Clock Tree Synthesis (CTS) skew<br>• Runs `scripts/parse_openlane_reports.py`<br>• Evaluates WNS / TNS setup & hold slacks | • Reviews STA timing tables in Antigravity IDE<br>• **Hard Silicon Check:** Confirms $T_{\text{slack, hold}} \ge 0.00\text{ ns}$<br>• Traces critical timing paths (Wallace tree XOR chain to accumulator DFF setup time)<br>• Learns PVT corner margins (slow/fast) |
| **Pillar 6** | **Physical Design & Sign-Off (PnR, DRC, LVS)** | **Tiny Tapeout Cloud CI (PnR)** + **Native Local KLayout (Inspection)** | • Configures floorplan, power rings, and pin placements<br>• Drives automated PnR flow in CI<br>• Audits Magic DRC (0 errors) & Netgen LVS (0 errors)<br>• Downloads final tapeout GDSII | • GUI: Launches **Native KLayout 0.30.9**<br>• Inspects standard-cell placement density ($\approx 58.8\%$ target)<br>• Observes power routing (VDD/VSS rails on met4/met5)<br>• Visualizes 3D metal stack |
| **Pillar 7** | **Silicon Bring-Up & Hardware Characterization** | **Physical Lab Bench:** RP2040 Carrier + PYNQ-Z2 FPGA via PMOD | • Generates MicroPython/C carrier test firmware<br>• Generates PYNQ-Z2 Vivado overlay bitstream & Python driver (`pynq.Overlay`)<br>• Prepares automated UART/USB test scripts | • Hardware: Plugs USB-C into RP2040 carrier board<br>• Connects 3.3V PMOD cable between PYNQ-Z2 and ASIC<br>• Runs Jupyter Notebook on PYNQ ARM Linux<br>• Logic Analyzer: Hooks PulseView/Sigrok to `uo_out`<br>• Validates live Micro-ResNet classification on silicon! |

---

## 4. Hardware Requirements: Do You Need a Dedicated GPU for KLayout?

**No, an integrated GPU (Intel UHD / Iris Xe / AMD Radeon Vega) is more than enough!**

* **Why?**
  - Our Tiny Tapeout $1\times 2$ macro contains $\approx 1,600\text{–}2,000$ standard cells ($\sim 20,000$ transistors).
  - The final GDSII file is only **$5\text{–}15\text{ Megabytes}$**.
  - KLayout is written in highly optimized C++ with a 2D rendering pipeline capable of displaying 100,000,000+ polygons.
  - On both your PC and Laptop, standard integrated graphics will pan and zoom through our CIM macro at a smooth **60 FPS** with zero stutter. Dedicated GPUs are only required for multi-gigabyte full-die SoCs (e.g. billion-transistor processors).

---

## 5. Software Setup Guide for Your Machines

### A. Local KLayout Setup (PC & Laptop)
* On your **Ubuntu PC**: KLayout 0.30.9 is already installed in `/usr/bin/klayout`!
* On your **Ubuntu Laptop**:
  ```bash
  sudo apt update && sudo apt install -y klayout
  ```
* **Enabling SkyWater 130nm Colors in KLayout (Two Ways):**
  - **Method 1 (Instant CLI / Bundled):** We include the official 242 KB SkyWater 130nm layer properties file directly in [`docs/sky130.lyp`](file:///home/juliusli/Documents/AntiG/CIMTinyTO/docs/sky130.lyp). Simply launch:
    ```bash
    klayout <path_to_gds> -l docs/sky130.lyp
    ```
  - **Method 2 (GUI / Salt Package Manager):**
    1. Open KLayout (`klayout`).
    2. In the top menu, go to **Tools** $\rightarrow$ **Manage Packages** (Salt).
    3. Search for **`sky130`** and click **Install**.
    4. Done! All SkyWater 130nm layers (`li1`, `met1`..`met5`) will render with standard industry colors and labels automatically.

### B. Local Tiny Tapeout CLI (Python `.venv`)
```bash
cd ~/Documents/AntiG/CIMTinyTO
source .venv/bin/activate
pip install --upgrade tt-cli
```

---

## 6. Hands-On Verification Commands for You (Pillar 1 Reproduction)

Whenever you would like to run and inspect the Gate 0 model:
```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Run the automated parser self-tests (<30 lines output)
python3 scripts/parse_yosys_stat.py --test
python3 scripts/parse_openlane_reports.py --test

# 3. Run the complete Gate 0 Golden Model & generate test vectors
python3 model/sim_scim.py
```
