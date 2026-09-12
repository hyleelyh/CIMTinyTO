# Tools & Execution Environment Matrix: Antigravity (AI) & Engineer (You)

This document defines the exact tools, execution environments, containerization strategy, and division of labor between **Antigravity (AI Automated Engine)** and **You (Human Chip Lead & Verifier)** across all 7 Pillars of the CIMTinyTO ASIC creation lifecycle.

---

## 1. Pedagogical Pairing & Verification Philosophy

In professional IC design teams, complex tasks are split between the **Implementation Engine** (writing code, generating netlists, running overnight simulations) and the **Chip Lead / Verification Engineer** (auditing architecture, reviewing timing reports, inspecting waveforms, and testing silicon). 

In this project:
* **Antigravity** serves as your high-speed ASIC implementation engine.
* **You** inspect the code in the Antigravity IDE, manually reproduce simulations, inspect waveforms in GTKWave, audit layout in KLayout, and physically bring up the chip on the bench.

---

## 2. Definitive Strategy: Two-Tier Flow (Option C + Option B)

To completely eliminate version conflicts between generic EDA packages and Tiny Tapeout shuttles:

1. **Option C (Tiny Tapeout Cloud CI) = Primary Synthesis, STA, & PnR Engine**
   - Runs the official, shuttle-pinned OpenLane 2 Docker container directly on GitHub Actions.
   - Authoritative source of truth for DRC, LVS, and GDSII generation.
   - Eliminates local PDK build issues and guarantees multi-project wafer compatibility.
2. **Option B (`IIC-OSIC-TOOLS`) = Interactive Layout & Visualization Workbench**
   - Used locally to launch **KLayout** and **Magic** via VNC/X11.
   - Inspects the GDSII silicon layout, metal layers (met1–met5), and cell placement density ($\approx 58.8\%$) produced by Tiny Tapeout.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   CIMTinyTO Flow Architecture                          │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
               ┌────────────────────────────┴────────────────────────────┐
               ▼                                                         ▼
    [Pillars 1, 2, 3: Front-End]                              [Pillars 4, 5, 6: Physical]
   • Native Host Python (.venv)                              • Tiny Tapeout Official Cloud CI
   • Verilog RTL Editing & Lint                                (Option C: PnR & GDSII Sign-Off)
   • Local Cocotb / iverilog Simulation                                  │
                                                                         ▼
                                                              [Layout Inspection]
                                                             • IIC-OSIC-TOOLS / KLayout
                                                               (Option B: Visual Inspection)
```

---

## 3. Comprehensive Tool & Environment Matrix Across All 7 Pillars

| Pillar | Milestone | Environment & Containerization | Antigravity (Automated Actions) | You (Manual Reproduction & Learning) |
|---|---|---|---|---|
| **Pillar 1** *(Completed)* | **System & Mathematical Modeling (Gate 0)** | **Native Host OS:** Local Python Virtual Environment (`.venv`), No Docker required | • Implements `model/sim_scim.py`<br>• Sweeps LFSR periods & seed decorrelation<br>• Verifies $1/\sqrt{N}$ convergence & SNR<br>• Generates `model/test_vectors_gate0.json`<br>• Executes parser self-tests | • In Antigravity IDE: Audits Python algorithm<br>• Terminal: Runs `.venv/bin/python model/sim_scim.py`<br>• Observes full-period collapse ($48\text{ dB}$ SNR) & $61.7\%$ power savings<br>• Inspects test vector JSON schema |
| **Pillar 2** *(Next)* | **Microarchitecture & Parameterized RTL** | **Native Host OS:** Verilog (IEEE 1364-2001) + `verilator` linter | • Implements synthesizable Verilog in `src/`<br>• Sizes registers, 4:2 compressor trees, and ICG clock gating<br>• Runs `verilator --lint-only -Wall`<br>• Enforces synchronous active-low resets | • In Antigravity IDE: Reviews state machine FSMs<br>• Verifies zero inferred latches<br>• Audits Tiny Tapeout pinout mapping (`tt_um_*`)<br>• Analyzes datapath vs control logic trade-offs |
| **Pillar 3** | **Verification & Design for Testability (DFT)** | **Native Host:** Python (`cocotb`, `pytest`) + Icarus Verilog (`iverilog`) | • Implements Cocotb testbenches in `test/`<br>• Ingests `test_vectors_gate0.json`<br>• Runs automated regression suites via `make`<br>• Injects corner cases (saturation, zero, checkerboard)<br>• Tests MISO shift loopback | • Terminal: Runs `make -C test`<br>• GUI: Opens `dump.vcd` in **GTKWave** or **Surfer**<br>• Traces cycle-by-cycle clock edges, compressor tree outputs, and accumulator increments<br>• Confirms 100% bit-exact match against Gate 0 |
| **Pillar 4** | **Logic Synthesis & Technology Mapping (Gate 2)** | **Option C (Cloud CI):** OpenLane 2 via GitHub Actions + Local Yosys (`scripts/parse_yosys_stat.py`) | • Prepares `config.yaml` & standard-cell mapping<br>• Triggers synthesis hardening CI<br>• Runs `scripts/parse_yosys_stat.py`<br>• Audits 256 weight DFF preservation (<30 lines) | • In Antigravity IDE: Audits cell count table<br>• Confirms no weight registers were pruned<br>• Evaluates gate count vs Tiny Tapeout $1\times 2$ tile area (~1,600–2,000 cells)<br>• Learns standard cell drive strengths (`_1`, `_2`) |
| **Pillar 5** | **Static Timing Analysis (STA)** | **Option C (Cloud CI):** OpenSTA / OpenROAD container | • Applies timing constraints (`sdc`) at $25\text{–}50\text{ MHz}$<br>• Analyzes Clock Tree Synthesis (CTS) skew<br>• Runs `scripts/parse_openlane_reports.py`<br>• Evaluates WNS / TNS setup & hold slacks | • Reviews STA timing tables in Antigravity IDE<br>• **Hard Silicon Check:** Confirms $T_{\text{slack, hold}} \ge 0.00\text{ ns}$<br>• Traces critical timing paths (Wallace tree XOR chain to accumulator DFF setup time)<br>• Learns PVT corner margins (slow/fast) |
| **Pillar 6** | **Physical Design & Sign-Off (PnR, DRC, LVS)** | **Option C (Cloud CI) for PnR** + **Option B (IIC-OSIC-TOOLS) for KLayout** | • Configures floorplan, power rings, and pin placements<br>• Drives automated PnR flow in CI<br>• Audits Magic DRC (0 errors) & Netgen LVS (0 errors)<br>• Generates final tapeout GDSII | • GUI: Launches **KLayout via IIC-OSIC-TOOLS**<br>• Inspects standard-cell placement density ($\approx 58.8\%$ target)<br>• Observes power routing (VDD/VSS rails on met4/met5)<br>• Visualizes 3D metal stack |
| **Pillar 7** | **Silicon Bring-Up & Hardware Characterization** | **Physical Lab Bench:** RP2040 Carrier + PYNQ-Z2 FPGA via PMOD | • Generates MicroPython/C carrier test firmware<br>• Generates PYNQ-Z2 Vivado overlay bitstream & Python driver (`pynq.Overlay`)<br>• Prepares automated UART/USB test scripts | • Hardware: Plugs USB-C into RP2040 carrier board<br>• Connects 3.3V PMOD cable between PYNQ-Z2 and ASIC<br>• Runs Jupyter Notebook on PYNQ ARM Linux<br>• Logic Analyzer: Hooks PulseView/Sigrok to `uo_out`<br>• Validates live Micro-ResNet classification on silicon! |

---

## 4. Complete Docker Installation & Setup Instructions

Below are the exact commands to prepare Docker, IIC-OSIC-TOOLS, and Tiny Tapeout tools on your Ubuntu system when you are ready.

### Part A: Host Docker Engine Installation
```bash
# 1. Update package lists and install Docker engine
sudo apt update && sudo apt install -y docker.io

# 2. Enable and start the Docker service
sudo systemctl enable --now docker

# 3. Add your current user to the docker group (avoids needing sudo)
sudo usermod -aG docker $USER

# 4. Apply group changes to current session
newgrp docker

# 5. Verify Docker works
docker run --rm hello-world
```

---

### Part B: IIC-OSIC-TOOLS Setup (For KLayout & GUI Inspection)
```bash
# 1. Navigate to your local IIC-OSIC-TOOLS directory
cd /home/juliusli/openhw/IICDocker/IIC-OSIC-TOOLS

# 2. Fast-forward the scripts to the latest release (2026.08)
git pull origin main

# 3. Pull the Docker image (~18 GB, includes Sky130 PDK and all GUI tools)
docker pull hpretl/iic-osic-tools:latest

# 4. Launch interactive KLayout layout viewer pointing to CIMTinyTO
./start_x.sh -d ~/Documents/AntiG/CIMTinyTO klayout
```

---

### Part C: Tiny Tapeout Official Toolchain Installation
Tiny Tapeout provides a dedicated Python CLI tool and GitHub Actions workflow:

```bash
# 1. Activate the CIMTinyTO virtual environment
cd ~/Documents/AntiG/CIMTinyTO
source .venv/bin/activate

# 2. Install the official Tiny Tapeout Python CLI
pip install --upgrade tt-cli

# 3. Verify tt CLI is working
tt --help
```

#### How Tiny Tapeout Runs Cloud Docker (Option C):
When we push code to GitHub:
1. `.github/workflows/gds.yaml` triggers on commit.
2. It pulls the exact container: `ghcr.io/tinytapeout/tt-gds-action:latest`.
3. It runs OpenLane 2 with the exact SkyWater 130nm PDK pinned for the shuttle.
4. It publishes the verified GDSII, DRC log, and 3D render as downloadable GitHub artifacts.

---

## 5. Hands-On Verification Commands for You (Pillar 1 Reproduction)

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
