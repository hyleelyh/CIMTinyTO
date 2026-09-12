# Tools & Execution Environment Matrix: Antigravity (AI) & Engineer (You)

This document defines the exact tools, execution environments, containerization strategy, and division of labor between **Antigravity (AI Automated Engine)** and **You (Human Chip Lead & Verifier)** across all 7 Pillars of the CIMTinyTO ASIC creation lifecycle.

---

## 1. Pedagogical Pairing & Verification Philosophy

In professional IC design teams, complex tasks are split between the **Implementation Engine** (writing code, generating netlists, running overnight simulations) and the **Chip Lead / Verification Engineer** (auditing architecture, reviewing timing reports, inspecting waveforms, and testing silicon). 

In this project:
* **Antigravity** serves as your high-speed ASIC implementation engine.
* **You** inspect the code in the Antigravity IDE, manually reproduce simulations, inspect waveforms in GTKWave, audit layout in KLayout, and physically bring up the chip on the bench.

---

## 2. Comprehensive Tool & Environment Matrix Across All 7 Pillars

| Pillar | Milestone | Environment & Containerization | Antigravity (Automated Actions) | You (Manual Reproduction & Learning) |
|---|---|---|---|---|
| **Pillar 1** *(Completed)* | **System & Mathematical Modeling (Gate 0)** | **Native Host OS:** Local Python Virtual Environment (`.venv`), No Docker required | • Implements `model/sim_scim.py`<br>• Sweeps LFSR periods & seed decorrelation<br>• Verifies $1/\sqrt{N}$ convergence & SNR<br>• Generates `model/test_vectors_gate0.json`<br>• Executes parser self-tests | • In Antigravity IDE: Audits Python algorithm<br>• Terminal: Runs `.venv/bin/python model/sim_scim.py`<br>• Observes full-period collapse ($48\text{ dB}$ SNR) & $61.7\%$ power savings<br>• Inspects test vector JSON schema |
| **Pillar 2** *(Next)* | **Microarchitecture & Parameterized RTL** | **Native Host OS:** Verilog (IEEE 1364-2001) + `verilator` linter | • Implements synthesizable Verilog in `src/`<br>• Sizes registers, 4:2 compressor trees, and ICG clock gating<br>• Runs `verilator --lint-only -Wall`<br>• Enforces synchronous active-low resets | • In Antigravity IDE: Reviews state machine FSMs<br>• Verifies zero inferred latches<br>• Audits Tiny Tapeout pinout mapping (`tt_um_*`)<br>• Analyzes datapath vs control logic trade-offs |
| **Pillar 3** | **Verification & Design for Testability (DFT)** | **Native Host or Container:** Python (`cocotb`, `pytest`) + Icarus Verilog (`iverilog`) | • Implements Cocotb testbenches in `test/`<br>• Ingests `test_vectors_gate0.json`<br>• Runs automated regression suites via `make`<br>• Injects corner cases (saturation, zero, checkerboard)<br>• Tests MISO shift loopback | • Terminal: Runs `make -C test`<br>• GUI: Opens `dump.vcd` in **GTKWave** or **Surfer**<br>• Traces cycle-by-cycle clock edges, compressor tree outputs, and accumulator increments<br>• Confirms 100% bit-exact match against Gate 0 |
| **Pillar 4** | **Logic Synthesis & Technology Mapping (Gate 2)** | **Docker Container Required:** OpenLane 2 / Yosys (`efabless/openlane` or `IIC-OSIC-TOOLS`) | • Synthesizes RTL to gate-level netlist using `sky130_fd_sc_hd`<br>• Maps to standard cells (NAND, XNOR, DFF, ICG)<br>• Runs `scripts/parse_yosys_stat.py`<br>• Enforces $<30$-line hygiene report<br>• Audits 256 weight DFF preservation | • In Antigravity IDE: Audits cell count table<br>• Confirms no weight registers were pruned<br>• Evaluates gate count vs Tiny Tapeout $1\times 2$ tile area (~1,600–2,000 cells)<br>• Learns standard cell drive strengths (`_1`, `_2`) |
| **Pillar 5** | **Static Timing Analysis (STA)** | **Docker Container Required:** OpenSTA / OpenROAD container | • Applies timing constraints (`sdc`) at $25\text{–}50\text{ MHz}$<br>• Analyzes Clock Tree Synthesis (CTS) skew<br>• Runs `scripts/parse_openlane_reports.py`<br>• Evaluates WNS / TNS setup & hold slacks | • Reviews STA timing tables in Antigravity IDE<br>• **Hard Silicon Check:** Confirms $T_{\text{slack, hold}} \ge 0.00\text{ ns}$<br>• Traces critical timing paths (Wallace tree XOR chain to accumulator DFF setup time)<br>• Learns PVT corner margins (slow/fast) |
| **Pillar 6** | **Physical Design & Sign-Off (PnR, DRC, LVS)** | **Docker Container Required:** OpenLane 2 / OpenROAD container (`docker` / `IICDocker`), Magic, Netgen, KLayout | • Configures `config.yaml` floorplan & power rings<br>• Drives macro placement, CTS, and detailed routing<br>• Inserts antenna diodes<br>• Runs Magic DRC, Netgen LVS, and GDSII generation | • GUI: Launches **KLayout** to view final GDSII layout<br>• Inspects standard-cell placement density ($\approx 58.8\%$ target)<br>• Observes power routing (VDD/VSS rails on met4/met5)<br>• Audits DRC = 0 and LVS = 0 sign-off reports |
| **Pillar 7** | **Silicon Bring-Up & Hardware Characterization** | **Physical Lab Bench:** RP2040 Carrier + PYNQ-Z2 FPGA via PMOD | • Generates MicroPython/C carrier test firmware<br>• Generates PYNQ-Z2 Vivado overlay bitstream & Python driver (`pynq.Overlay`)<br>• Prepares automated UART/USB test scripts | • Hardware: Plugs USB-C into RP2040 carrier board<br>• Connects 3.3V PMOD cable between PYNQ-Z2 and ASIC<br>• Runs Jupyter Notebook on PYNQ ARM Linux<br>• Logic Analyzer: Hooks PulseView/Sigrok to `uo_out`<br>• Validates live Micro-ResNet classification on silicon! |

---

## 3. Why Docker is Mandatory for OpenLane & OpenROAD (Pillars 4, 5, 6)

### The Silicon Realities of EDA Toolchains:
1. **PDK & Dependency Hell:**
   OpenLane 2 is not a single binary; it is an orchestration layer integrating:
   - **Yosys** (RTL synthesis) & **ABC** (logic optimization)
   - **OpenROAD** (floorplan, placement, CTS, global & detailed routing)
   - **OpenSTA** (Static Timing Analysis)
   - **Magic** (Design Rule Checking - DRC, parasitic extraction)
   - **Netgen** (Layout vs. Schematic - LVS)
   - **KLayout** (GDSII streaming & DRC)
   - **SkyWater 130nm PDK** (`sky130A` standard cells, LEF, DEF, Liberty `.lib` timing models, tech files)
   Attempting to compile these natively on Ubuntu requires 15+ interdependent C++ toolchains (boost, tcl/tk, eigen, lemon, bison, flex) with strict version pinning. Any system `apt upgrade` can break the entire flow.

2. **Guaranteed Reproducibility:**
   Running OpenLane inside a Docker container freezes every tool binary, library version, and PDK file down to the exact git commit. A layout synthesized on your PC, your laptop, or GitHub Actions CI will be **100% bit-exact and DRC-identical**.

---

## 4. How We Will Execute Docker in This Project

When we reach **Pillar 4 (Logic Synthesis)**, **Pillar 5 (STA)**, and **Pillar 6 (PnR & Physical Sign-off)**, we have **three seamless execution paths**:

```
                              ┌────────────────────────────────────────────────────────┐
                              │           RTL Sources (src/) + Config (config.yaml)    │
                              └──────────────────────────┬─────────────────────────────┘
                                                         │
                        ┌────────────────────────────────┼───────────────────────────────┐
                        ▼                                ▼                               ▼
            [Option A: Local OpenLane]       [Option B: Local IICDocker]     [Option C: GitHub Actions CI]
            efabless/openlane:v...           /home/juliusli/openhw/IICDocker   Tiny Tapeout Cloud Runner
            Runs via local Docker engine     Pre-installed open-source EDA    Push to GitHub -> Automated
            Automated via scripts            Interactive desktop & shell      Zero local install needed
```

### Option A: Standard OpenLane 2 Docker Container (Recommended for Local CLI)
Mounts the project directory into the official OpenLane container:
```bash
docker run --rm \
  -v $(pwd):/work \
  -v $PDK_ROOT:/pdk \
  -e PDK_ROOT=/pdk \
  -w /work \
  efabless/openlane:latest \
  flow.tcl -design .
```

### Option B: Pre-Installed IIC-OSIC-TOOLS (`/home/juliusli/openhw/IICDocker`)
You already have Johannes Kepler University's all-in-one IC design environment locally:
```bash
cd /home/juliusli/openhw/IICDocker/IIC-OSIC-TOOLS
./start_shell.sh -d ~/Documents/AntiG/CIMTinyTO
```
This gives you an interactive shell containing OpenLane, OpenROAD, Magic, Netgen, and KLayout pre-loaded with Sky130 PDK!

### Option C: Tiny Tapeout Cloud CI (Push-Button Remote Docker)
Tiny Tapeout provides an automated GitHub Actions workflow (`tt-gds-action`) that spins up the OpenLane Docker container in the cloud on every Git push, runs synthesis, PnR, DRC/LVS, and uploads the final GDSII artifact.

---

## 5. Prerequisites to Enable Local Docker on Your Machine

Currently on your Ubuntu workstation, the Docker service is not installed/running. Before we start Pillar 4, we will execute:
```bash
# Install Docker engine
sudo apt update && sudo apt install -y docker.io

# Enable Docker service and grant user permission without sudo
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker availability
docker run --rm hello-world
```

---

## 6. Hands-On Verification Commands for You (Pillar 1 Reproduction)

```bash
# 1. Activate the local virtual environment (Native Python, no Docker)
source .venv/bin/activate

# 2. Run the automated parser self-tests (<30 lines output)
python3 scripts/parse_yosys_stat.py --test
python3 scripts/parse_openlane_reports.py --test

# 3. Run the complete Gate 0 Golden Model & generate test vectors
python3 model/sim_scim.py
```
