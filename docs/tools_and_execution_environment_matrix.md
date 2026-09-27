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

1. **Front-End & Verification (Pillars 1, 2):**
   - 100% Native Host OS (`.venv`, `verilator`, `cocotb`, `iverilog`, `gtkwave`).
   - Mathematical modeling and bit-exact functional verification run in milliseconds.
2. **Physical ASIC Flow (Pillar 3):**
   - **Tiny Tapeout Official Cloud CI / OpenLane 2 / OpenROAD.**
   - Automated synthesis, floorplanning, placement, CTS, routing, Magic DRC (0 errors), and Netgen LVS (0 errors).
3. **Timing & Gate-Level Sign-Off (Pillars 4, 5):**
   - Multi-corner STA timing closure across 9 PVT corners (Pillar 4).
   - Gate-Level Simulation (GLS) with foundry PDK cells and VCD dynamic power profiling (Pillar 5).
4. **Pre-Silicon Emulation & Bring-Up (Pillars 6, 7):**
   - High-speed FPGA hardware-in-the-loop emulation on PYNQ-Z2 and DE10-Lite (Pillar 6).
   - Physical carrier board post-silicon validation and bench characterization (Pillar 7).

---

## 3. Comprehensive Tool & Environment Matrix Across All 7 Pillars

| Pillar | Milestone | Environment | Antigravity (Automated Actions) | You (Manual Reproduction & Learning) |
|---|---|---|---|---|
| **Pillar 1** *(Completed)* | **System & Mathematical Modeling (Gate 0)** | **Native Host OS:** Local Python Virtual Environment (`.venv`) | • Implements `model/sim_scim.py`<br>• Sweeps LFSR periods & seed decorrelation<br>• Verifies $1/\sqrt{N}$ convergence & SNR<br>• Generates `model/test_vectors_gate0.json`<br>• Executes parser self-tests | • In Antigravity IDE: Audits Python algorithm<br>• Terminal: Runs `.venv/bin/python model/sim_scim.py`<br>• Observes full-period collapse ($48\text{ dB}$ SNR) & $61.7\%$ power savings<br>• Inspects test vector JSON schema |
| **Pillar 2** *(Completed)* | **Microarchitecture, Parameterized RTL & Verification** | **Native Host OS:** Verilog (IEEE 1364-2001) + `verilator` + Cocotb / `iverilog` | • Implements synthesizable Verilog in `src/`<br>• Sizes registers, 4:2 compressor trees, and ICG clock gating<br>• Hardens against Silicon Holes #1–#11<br>• Runs automated regressions via `make test_all` | • In Antigravity IDE: Reviews state machine FSMs<br>• Verifies zero inferred latches<br>• Audits Tiny Tapeout pinout mapping (`tt_um_*`)<br>• Traces cycle-by-cycle clock edges & compressor outputs |
| **Pillar 3** *(Completed)* | **Physical ASIC Flow (PnR, DRC, LVS)** | **OpenLane 2 / OpenROAD** + **Native Local KLayout (Inspection)** | • Configures floorplan, power rings, and pin placements<br>• Drives push-button synthesis, CTS, and detailed routing<br>• Signs off Magic DRC (0 errors) & Netgen LVS (0 errors)<br>• Hardens to $2 \times 2$ macro (~7,051 cells, 80.99% density) | • GUI: Launches **Native KLayout 0.30.9**<br>• Inspects standard-cell placement density<br>• Observes power routing (VDD/VSS rails on met4/met5)<br>• Visualizes 3D metal stack |
| **Pillar 4** *(Completed)* | **Static Timing Analysis & Power Sign-Off (STA)** | **OpenSTA / OpenROAD** + Local Audit (`scripts/sta_power_audit.py`) | • Evaluates 9 sign-off PVT/RC corners (TT, SS, FF @ -40°C to +100°C)<br>• Audits SDC interface constraints & clock uncertainty<br>• Verifies zero hold violations across all corners ($+0.110\text{ ns}$ worst-case)<br>• Profiles static core power ($2.798\text{ mW}$) and PDN rail IR drop | • Reviews STA timing tables in Antigravity IDE<br>• Confirms positive hold margin across all corners<br>• Traces critical paths (Wallace tree XOR chain to accumulator DFF)<br>• Audits SDC interface assumptions |
| **Pillar 5** *(Completed)* | **Gate-Level Simulation (GLS) & Dynamic Power** | **Cocotb + Icarus Verilog + Sky130 PDK** + `scripts/gls_power_audit.py` | • Simulates 7,051-cell post-route netlist with foundry library cells<br>• Validates 10/10 Gate 0 golden vectors with 100% bit-exact parity<br>• Verifies pad quiescence (Hole #8, 0 pad transitions during compute)<br>• Correlates VCD toggle activity with SPEF parasitics for dynamic power ($0.418\text{ mW}$) | • Terminal: Runs `make test_gls`<br>• GUI: Opens `test/tb.vcd` in **GTKWave**<br>• Traces physical clock tree delay and `FallingEdge` launch margin<br>• Reviews workload energy-per-MAC ($50.73\text{ pJ/MAC}$) |
| **Pillar 6** *(Next)* | **Pre-Silicon Emulation (FPGA Testbench)** | **FPGA Platforms:** PYNQ-Z2 (Zynq-7020) & DE10-Lite (MAX 10) | • Synthesizes FPGA bitstreams for Zynq-7020 and MAX 10<br>• Builds MMIO AXI wrapper and PMOD interface<br>• Generates interactive Jupyter Notebook regressions at 50–100 MHz<br>• Implements DE10-Lite 7-segment hex accumulator display | • Connects PYNQ-Z2 via PMOD / Ethernet<br>• Runs interactive Jupyter Notebook on PYNQ ARM Linux<br>• Tests tactile switches and monitors hex display on DE10-Lite<br>• Validates hardware-in-the-loop inference |
| **Pillar 7** | **Post-Silicon Bring-Up & Board Characterization** | **Physical Lab Bench:** RP2040 Carrier + Korad KA3005P + Oscilloscope | • Prepares MicroPython/C carrier test firmware<br>• Automates UART/USB regression test suite<br>• Characterizes frequency scaling, voltage sag, and thermal margins | • Hardware: Powers RP2040 carrier via current-limited Korad supply ($120\text{ mA}$)<br>• Hooks oscilloscope to clock, busy, and output pins<br>• Validates live Micro-ResNet inference on real silicon! |

---

## 4. Hardware Requirements: Do You Need a Dedicated GPU for KLayout?

**No, an integrated GPU (Intel UHD / Iris Xe / AMD Radeon Vega) is more than enough!**

* **Why?**
  - Our Tiny Tapeout $2\times 2$ macro contains $\approx 7,051$ standard cells ($\sim 70,000$ transistors).
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
