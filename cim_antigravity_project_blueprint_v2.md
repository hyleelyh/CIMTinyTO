# Stochastic & Digital Compute-in-Memory (CIM): Feasibility, Architecture & Verification Blueprint

## 1. Project Overview & Feasibility Summary

This document establishes the architectural, verification, and tooling blueprint for designing, synthesizing, and validating a standard-cell **Stochastic Compute-in-Memory (SCIM)** and **Digital Compute-in-Memory (DCIM)** prototype targeted for open-source shuttle tapeouts (e.g., Tiny Tapeout on SkyWater 130nm / IHP SG13G2) utilizing an AI-assisted open EDA flow.

### Executive Evaluation Findings
* **Implementation Feasibility (High):** Standard-cell DCIM and SCIM bypass custom analog bitcells, complex custom DRC/LVS boundary rules, sensitive sense amplifiers, and ADCs/DACs.
* **SCIM Advantage on Tiny Tapeout:** Stochastic computing replaces multi-bit multipliers with single AND/XNOR gates, enabling a significantly larger Matrix-Vector Multiplication (MVM) array within the tight 800–1,200 standard-cell limit of a single tile (~$160 \times 100\ \mu\text{m}$).
* **Zero-Cost Toolchain:** The entire flow is supported by open-source tools (`iverilog`, `cocotb`, `GTKWave`, `Yosys`, `OpenROAD`/`OpenLane 2`, `Magic`, `Netgen`, `KLayout`).
* **Multi-Tier Testing Infrastructure:** The silicon can be validated on Day 1 using the pre-assembled Tiny Tapeout RP2040/RP2350 carrier board over USB, and further characterized at high wire speeds ($50\text{–}100+\text{ MHz}$) using a **PYNQ-Z2 FPGA** connected via 3.3V PMOD headers.

---

## 2. Environment Setup: GitHub MCP Server on Linux

To enable Antigravity 2.0 / MCP-compatible AI agents to pull code, commit RTL revisions, manage branches, and push to your Tiny Tapeout GitHub repository across multiple Linux laptops, configure the **GitHub Model Context Protocol (MCP)** server first.

### Step-by-Step Setup
1. **Generate a GitHub Personal Access Token (PAT):**
   * Go to **GitHub Settings $\rightarrow$ Developer Settings $\rightarrow$ Personal Access Tokens (Classic or Fine-Grained)**.
   * Grant scopes: `repo` (Full control of private repositories) and `workflow` (if triggering GitHub Actions hardening CI).
2. **Install Node.js & GitHub MCP Server:**
   ```bash
   # Ensure Node.js (v18+) and npm are installed
   sudo apt update && sudo apt install -y nodejs npm
   
   # Verify npm / npx availability
   npx -y @modelcontextprotocol/server-github --version
   ```
3. **Configure MCP Server in Antigravity / Client Configuration:**
   Add the server entry to your MCP configuration JSON (`mcp_config.json` or Antigravity MCP settings):
   ```json
   {
     "mcpServers": {
       "github": {
         "command": "npx",
         "args": [
           "-y",
           "@modelcontextprotocol/server-github"
         ],
         "env": {
           "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_yourActualGitHubPersonalAccessTokenHere"
         }
       }
     }
   }
   ```
4. **Agent Capabilities Unlocked:**
   * Direct repository cloning, tree reading, and branch management.
   * Automated commit and push for Verilog modules, Cocotb testbenches, and OpenLane configurations.
   * Live inspection of GitHub Actions CI logs for automated DRC/LVS and synthesis sign-off.

---

## 3. Architecture Comparison: Analog CIM vs. Digital CIM vs. Stochastic CIM

| Dimension | Mixed-Signal / Analog CIM | Fully Digital CIM (DCIM) | Stochastic CIM (SCIM) |
|---|---|---|---|
| **Computation Mechanism** | Charge sharing / current accumulation on bitlines | Synthesized logic gates (XOR, AND, Adder trees) | Bitstream probability multiplication (single AND/XNOR) |
| **Storage Element** | Custom 6T/8T/10T SRAM bitcells | Standard D-Flip-Flops (DFFs) / Latches | Register banks / DFF arrays |
| **Energy Efficiency** | Ultra-high (>50 TOPS/W) | High (10–30 TOPS/W) | High (Ultra-low switching energy) |
| **Deterministic Accuracy** | Sensitive to $V_{th}$ mismatch, noise, PVT, IR drop | 100% deterministic & bit-exact | Statistical convergence (Error scales with $1/\sqrt{N}$) |
| **Peripheral Overhead** | Dominant (Flash / SAR ADCs require huge area) | Minimal (Standard digital multiplexers & registers) | Minimal (Shared LFSRs/SNGs + Counter accumulators) |
| **OpenLane/OpenROAD Fit** | Difficult (Requires custom analog macro integration) | 100% Native Standard Cell Flow | 100% Native Standard Cell Flow |
| **Tiny Tapeout Suitability** | Low (Pin & macro layout constraints) | High ($8\times 8$ to $16\times 16$ array) | **Extremely High** (Minimal gate footprint per PE) |

---

## 4. End-to-End Verification Pipeline

```
[PyTorch / NumPy Golden Model]
           │
           ▼
[Pre-Silicon: Cocotb + Icarus / Verilator] ──► Passes Functional RTL Verification
           │
           ▼
[OpenLane Synthesis & PnR Flow]
           │
           ▼
[Pre-Silicon: Gate-Level Simulation (GLS) + SDF] ──► Passes Physical & Timing Sign-off
           │
           ▼
[Tapeout & Fabrication Shuttle]
           │
           ▼
[Post-Silicon: Carrier Board (RP2040) / PYNQ-Z2] ──► Re-runs Python Vectors on Real Silicon
```

### Risk Matrix & Human Inspection Checkpoints

| Stage | Critical Risk Points | Human Inspection / Mitigation |
|---|---|---|
| **RTL Design** | Inferred latches, combinational loops, unhandled FSM states | Ensure all `if-else` / `case` blocks have explicit default assignments; enforce single synchronous clock domain (`posedge clk`). |
| **Pre-Silicon Sim** | Missing corner cases, incorrect fixed-point truncation | Test zero matrices, max saturation, alternating bit patterns (`0x55`/`0xAA`); match bit-exact truncation in NumPy model. |
| **Gate-Level Sim (GLS)** | 'X' (unknown state) propagation | Verify all control registers have reset lines; check power-up states. |
| **Physical Sign-Off** | Pruned flip-flops, negative hold slack, DRC/LVS errors | Verify cell counts in `synthesis.log`; confirm $T_{\text{slack, hold}} \ge 0$ in OpenSTA; achieve 0 DRC / 0 LVS errors. |
| **Post-Silicon** | Pin floating, lack of internal visibility, clock jitter | Implement SPI readback path; include observability MUX for status flags (`busy`, `done`, `overflow`). |

---

## 5. Design for Testability (DFT) Strategy

* **Dual-Mode Verification (Deterministic Test Mode vs. Stochastic Mode):**
  * *Deterministic Mode:* Bypasses the Stochastic Number Generator (SNG) to feed static bits into the array, verifying wiring, registers, and accumulators deterministically on Day 1.
  * *Stochastic Mode:* Engages internal LFSRs / Sobol sequences for statistical Matrix-Vector Multiplication (MVM).
* **SPI Readback Loopback:** Reuses the input weight shift registers as a circular shift loop to verify weight retention over MISO with zero extra dedicated pins.
* **On-Chip Logic/Memory BIST:** Uses a lightweight LFSR pattern generator and Multiple-Input Signature Register (MISR) to run autonomous self-tests at full clock speed.

---

## 6. Board-Level Hardware & Bring-Up Infrastructure

### Tier 1: Tiny Tapeout Demo Carrier Board (RP2040/RP2350)
* **Out-of-the-box Bring-Up:** Fully pre-assembled PCB with onboard RP2040/RP2350 microcontroller, $3.3\text{V} / 1.8\text{V}$ regulators, clock generators, DIP switches, and USB-C port.
* **Programmable I/O (PIO):** Generates jitter-free master clocks and custom serial frame strobes, streaming bitstreams into `ui_in` and capturing `uo_out` at wire speed via DMA without CPU interrupts.

### Tier 2: PYNQ-Z2 FPGA Testbench (Advanced Characterization)
* **High-Speed Hardware SNG Generator:** Implements multi-channel stochastic bitstream generators in FPGA programmable logic (PL) to feed the ASIC at $50\text{–}100+\text{ MHz}$.
* **Jupyter Notebook Integration:** Controls test runs via Python (`pynq.Overlay`) on the dual-core ARM Cortex-A9 processor, logging millions of output cycles into DDR3 RAM to plot variance and Signal-to-Noise Ratio (SNR) curves directly.
* **Interface:** Direct 3.3V LVCMOS PMOD-to-PMOD connection between PYNQ-Z2 and Tiny Tapeout carrier board with a common ground.

```
[PYNQ-Z2 Board]                                     [Tiny Tapeout Carrier]
┌───────────────────────────────┐                  ┌──────────────────────┐
│  Processing System (ARM Linux)│                  │                      │
│   • Jupyter Notebook / Python │                  │                      │
│   • NumPy / Matplotlib        │                  │                      │
│               │ (AXI Bus)     │                  │                      │
│  Programmable Logic (FPGA)    │                  │                      │
│   • High-Speed SNG Engine     │                  │                      │
│   • Hardware Counter / FIFO   │                  │                      │
│               │               │   Ribbon Cable   │                      │
│        [PMOD A / B Headers]   ├─────────────────►│ [PMOD / IO Headers]  │
│        (3.3V Logic Level)     │                  │   • ui_in[7:0]       │
│                               │◄─────────────────┤   • uo_out[7:0]      │
│                               │                  │   • CLK, RST_N       │
└───────────────────────────────┘                  └──────────────────────┘
```

---

## 7. Open-Source Toolchain Mapping

| Phase | Function | Open-Source Tool | Commercial Equivalent |
|---|---|---|---|
| **Modeling** | Quantization & Golden Reference | **Python** (`NumPy`, `PyTorch`) | MATLAB / Simulink |
| **RTL & Lint** | HDL coding & syntax linting | **Verilator** (lint), **VS Code** | Synopsys SpyGlass |
| **Verification**| Behavioral & Gate-Level Simulation | **Cocotb**, **Icarus Verilog**, **Verilator** | Synopsys VCS, Cadence Xcelium |
| **Waveforms** | Signal inspection & X-tracing | **GTKWave**, **Surfer** | Synopsys Verdi |
| **Synthesis** | Logic synthesis & netlist mapping | **Yosys** + **ABC** | Synopsys Design Compiler |
| **Place & Route**| Floorplan, CTS, placement, routing | **OpenROAD** / **OpenLane 2** | Cadence Innovus |
| **Timing** | Multi-corner Static Timing Analysis | **OpenSTA** | Synopsys PrimeTime |
| **Physical Sign-Off**| DRC & LVS physical verification | **Magic**, **Netgen**, **KLayout** | Siemens Calibre DRC/LVS |
| **Silicon Driver** | Carrier firmware & logic capture | **MicroPython**, **PulseView** / **Sigrok** | Saleae Logic Software |

---

## 8. Verified Literature & References

### Digital Compute-in-Memory (DCIM)
* **Comprehensive Review:**
  * *A Review of SRAM-Based Compute-in-Memory Circuits (K. Yoshioka et al., JJAP/SSDM):*  
    [Japanese Journal of Applied Physics (DOI: 10.35848/1347-4065/ad93e0)](https://doi.org/10.35848/1347-4065/ad93e0) | [ResearchGate Publication Record](https://www.researchgate.net/publication/385918862_A_review_of_SRAM-based_compute-in-memory_circuits)
  * *Digital In-Memory Computing to Accelerate Deep Learning Inference on the Edge (S. Perri et al., IEEE IPDPS/RAW):*  
    [ResearchGate Full-Text Preprint](https://www.researchgate.net/publication/379484756_Digital_In-Memory_Computing_to_Accelerate_Deep_Learning_Inference_on_the_Edge_Invited_Paper) | [DBLP Index Record](https://dblp.org/rec/conf/ipps/PerriSSCF24.html)
* **Architectures & Compilers:**
  * *An SRAM-Based Digital Compute-in-Memory Macro with Dual-Bit Input Data Sparsification and Restructuring (IEEE ISCAS):*  
    [IEEE Xplore PDF Access](https://ieeexplore.ieee.org/iel8/11043142/11042930/11043567.pdf) | [Semantic Scholar Record](https://www.semanticscholar.org/paper/An-SRAM-Based-Digital-Compute-in-Memory-Macro-with-Chen-Ma/4300b3f4ec493938556fd38e29e393a5bbb95b67)
  * *An Open-Source SRAM-Based Approximate CiM Compiler (OpenACM on OpenROAD):*  
    [arXiv:2601.11292 [cs.AR]](https://arxiv.org/abs/2601.11292)

### Stochastic Computing & Stochastic CIM (SCIM)
* **Surveys & Mathematical Foundations:**
  * *Survey of Stochastic Computing (A. Alaghi & J. P. Hayes, ACM TECS):*  
    [ACM Digital Library (DOI: 10.1145/2461256.2461273)](https://doi.org/10.1145/2461256.2461273) | [Semantic Scholar Record](https://www.semanticscholar.org/paper/Survey-of-Stochastic-Computing-Alaghi-Hayes/f4704233499ddb9676550f0ddb6e16999e8bf2d5)
  * *Digital In-Memory Stochastic Computing Architecture for Vector-Matrix Multiplication (Frontiers in Nanotechnology):*  
    [Frontiers Open Access Article (DOI: 10.3389/fnano.2023.1147396)](https://doi.org/10.3389/fnano.2023.1147396)
* **Classical Foundations:**
  * *Stochastic Computing: Advances in Information Systems Science (B. R. Gaines, Springer):*  
    [Springer Link Chapter (DOI: 10.1007/978-1-4899-5841-9_2)](https://doi.org/10.1007/978-1-4899-5841-9_2)

### Open-Source Repositories & Docs
* **Verification Tools:** [Cocotb Documentation](https://docs.cocotb.org/) | [Icarus Verilog GitHub](https://github.com/steveicarus/iverilog) | [Verilator](https://www.verilator.org/)
* **Physical ASIC Flow:** [OpenLane 2 Documentation](https://openlane.readthedocs.io/) | [OpenROAD Project](https://theopenroadproject.org/) | [KLayout](https://www.klayout.de/) | [OpenRAM Compiler](https://openram.org/)
* **Shuttle & PDK Access:** [Tiny Tapeout](https://tinytapeout.com/) | [Tiny Tapeout Docs](https://docs.tinytapeout.com/) | [Tiny Tapeout GitHub](https://github.com/TinyTapeout) | [IHP Open PDK](https://github.com/IHP-GmbH/IHP-Open-PDK)

---

## 9. Antigravity 2.0 Workspace Setup Roadmap

1. **Step 0 — GitHub MCP Server Configuration:** Set up the Node.js GitHub MCP server on your Linux machines with your GitHub PAT so agents can pull, branch, and push changes automatically.
2. **Step 1 — Mathematical Modeling (`sim_scim.py`):** Model unipolar/bipolar SNG generators (LFSR vs. Sobol sequences), XNOR/AND multipliers, and accumulator counters in Python to determine optimal bitstream lengths ($N=64, 256, 1024$).
3. **Step 2 — Parameterized Verilog RTL:** Implement the core SCIM PE array, SPI shift/readback register, and the Tiny Tapeout pinout wrapper (`tt_um_*`).
4. **Step 3 — Cocotb Simulation Harness:** Build a Cocotb testbench using Icarus Verilog that runs regression batches against the Python golden model.
5. **Step 4 — Tiny Tapeout CI Hardening:** Push to GitHub with `config.yaml` to run OpenLane 2 / OpenROAD synthesis, PnR, STA, and DRC/LVS checks.
6. **Step 5 — PYNQ / Carrier Bring-up Scripting:** Prepare the MicroPython test routines and PYNQ-Z2 Vivado overlay IP for hardware bring-up upon silicon arrival.
