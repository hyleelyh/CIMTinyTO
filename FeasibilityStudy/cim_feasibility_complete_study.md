# SRAM Compute-in-Memory (CIM) & Stochastic CIM: Feasibility, Architecture & Verification Study

## 1. Executive Summary & Feasibility Overview

This report evaluates the architectural, verification, and tooling feasibility of designing, synthesizing, and validating a standard-cell **Digital Compute-in-Memory (DCIM)** or **Stochastic Compute-in-Memory (SCIM)** macro targeted for low-cost shuttle tapeouts (e.g., Tiny Tapeout on SkyWater 130nm / IHP SG13G2) utilizing an open-source, AI-assisted EDA workflow.

### Core Feasibility Takeaways
* **Design Complexity (Low to Moderate):** Standard-cell DCIM and SCIM avoid custom analog bitcells, complex DRC/LVS boundary rules, sensitive sense amplifiers, and power-hungry ADCs/DACs.
* **Open-Source Toolchain (Zero License Cost):** The entire RTL-to-GDSII and verification chain runs on open-source tools (`iverilog`, `cocotb`, `GTKWave`, `Yosys`, `OpenROAD`/`OpenLane 2`, `Magic`, `Netgen`, `KLayout`).
* **Hardware & Board-Level Bring-Up Barrier (Minimal):** Physical testing uses an integrated, pre-assembled carrier board with an onboard microcontroller (RP2040 / RP2350) driving test vectors over USB.
* **Primary Physical Constraint:** Standard cell density vs. array size. A single Tiny Tapeout tile (~$160 \times 100\ \mu\text{m}$) fits roughly 800–1,200 standard cells. Target initial prototypes to $8\times 8$ or $16\times 16$ 1-bit/stochastic PEs (or allocate a $1\times 2$ / $2\times 2$ multi-tile footprint).

---

## 2. Architecture Comparison: Analog vs. Digital vs. Stochastic CIM

| Dimension | Mixed-Signal / Analog CIM | Fully Digital CIM (DCIM) | Stochastic CIM (SCIM) |
|---|---|---|---|
| **Computation Mechanism** | Charge sharing / current accumulation on bitlines | Synthesized logic gates (XOR, AND, Adder trees) | Bitstream probability multiplication (single AND/XNOR) |
| **Storage Element** | Custom 6T/8T/10T SRAM bitcells | Standard D-Flip-Flops (DFFs) / Latches | Register banks / DFF arrays |
| **Energy Efficiency** | Ultra-high (>50 TOPS/W) | High (10–30 TOPS/W) | High (Ultra-low switching energy) |
| **Deterministic Accuracy** | Sensitive to $V_{th}$ mismatch, noise, PVT, IR drop | 100% deterministic & bit-exact | Statistical convergence (Error scales with $1/\sqrt{N}$) |
| **Peripheral Overhead** | Dominant (Flash / SAR ADCs require huge area) | Minimal (Standard digital multiplexers & registers) | Minimal (Shared LFSRs/SNGs + Counter accumulators) |
| **OpenLane/OpenROAD Fit** | Difficult (Requires custom analog macro integration) | 100% Native Standard Cell Flow | 100% Native Standard Cell Flow |
| **Tiny Tapeout Suitability** | Low (Pin & macro layout constraints) | High ($8\times 8$ to $16\times 16$ array) | Extremely High (Minimal gate count per multiplier) |

---

## 3. End-to-End Verification Architecture

The design flow uses identical test vectors across every phase—from software models to physical silicon bring-up:

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
[Post-Silicon: Carrier Board + RP2040 MCU] ──► Re-runs Python Vectors on Real Silicon
```

### Risk Matrix & Mitigation Strategies

| Stage | Primary Risk | Mitigation Strategy |
|---|---|---|
| **Pre-Silicon** | Asynchronous clock domain race conditions | Enforce a single synchronous clock domain with enable strobes. |
| **Pre-Silicon** | OpenLane clock tree or hold-time violations | Add clock margin during synthesis; inspect OpenSTA hold slack reports. |
| **Pre-Silicon** | Netlist register pruning by Yosys | Verify output connectivity and inspect synthesis cell count summaries. |
| **Post-Silicon** | Lack of internal state observability | Route status flags (`busy`, `done`, `overflow`) and debug taps to dedicated output pins. |
| **Post-Silicon** | Weight loading corruption during shifting | Implement a deterministic SPI/shift loopback readback mode prior to compute execution. |

---

## 4. AI-Assisted Workflow vs. Human Inspection Requirements

```
[System Model] ──► [Synthesizable RTL] ──► [Cocotb Sim] ──► [OpenLane/GDSII] ──► [Silicon Bring-Up]
 (PyTorch/NumPy)       (Verilog HDL)        (Icarus/Verilator)    (GitHub CI/Actions)   (RP2040 / Python)
       │                     │                     │                      │                    │
   AI Writes             AI Writes             AI Writes              AI Debugs            AI Writes
   Algorithmic           Module Code &         Testbenches &          Reports &            Bring-Up &
   Baseline              I/O Adapters          Edge Vectors           Timing Logs          Driver Scripts
```

### Human Knowledge Requirements by Phase

1. **Specification & Architecture Review:**
   * Understand fixed-point quantization, two's complement arithmetic, and accumulator bit-growth ($W_{\text{acc}} \ge W_{\text{mult}} + \lceil \log_2(\text{Rows}) \rceil$).
   * Multiplex limited ASIC pins (Tiny Tapeout: 8 in, 8 out, 8 bidir) using SPI/shift-chains.
   * Maintain synchronous clock discipline without glitchy clock gates or mixed clock domains.
2. **RTL & Microarchitecture Inspection:**
   * Prevent inferred latches by completing all `if-else` branches and `default` cases in combinational blocks.
   * Ensure FSM state machines contain safe default recoveries against illegal glitch states.
   * Provide memory loopback / readback capabilities for weight write verification.
3. **Pre-Silicon Verification (Cocotb & Sim):**
   * Check corner cases: zero matrices, maximum positive/negative saturation values, alternating bit patterns (`0xAA`/`0x55`), and back-to-back operations.
   * Debug 4-state Gate-Level Simulation (`0, 1, X, Z`) to eliminate 'X' propagation from uninitialized registers.
   * Verify bit-for-bit equivalence between Python models and RTL arithmetic.
4. **Physical Implementation (OpenLane / OpenROAD):**
   * Audit Yosys netlist logs to ensure memory flip-flops are not pruned.
   * Ensure **hold slack is strictly positive** across all PVT corners.
   * Achieve 100% clean sign-off (Zero DRC errors, zero LVS mismatches, cleared antenna rules).
5. **Post-Silicon Bring-Up & Board Validation:**
   * Set up logic analyzers and scope triggers for SPI chip-select and strobe lines.
   * Follow a structured bring-up sequence: Power rails $\rightarrow$ Clock $\rightarrow$ Reset release $\rightarrow$ Register readback $\rightarrow$ Single-step compute $\rightarrow$ Full-speed inference batches.

---

## 5. Design for Testability (DFT) Strategies for CIM

| DFT Technique | Implementation Mechanism | Area / Pin Overhead | Diagnostic Capability |
|---|---|---|---|
| **Shadow / Readback Loopback** | Daisy-chains weight DFFs into a circular shift register | Minimal (~0% if reusing SPI shift registers) / **0 extra pins** | **Data Integrity Check:** Verifies weight write/retention before computation. |
| **Logic Observability MUXing** | Small MUX routing internal taps to spare `uo_out` pins | Negligible (<20 gates) / **0 extra pins** | **Real-Time Tracing:** Exposes intermediate adder sums, carry-outs, or FSM states to logic analyzers. |
| **Memory / Logic BIST** | On-chip LFSR pattern generator + MISR signature compressor | Low (~50–100 gates) / **0 dedicated pins** | **Go/No-Go Testing:** Validates array math at full rated frequency ($50\text{ MHz}$) independent of MCU USB bandwidth. |
| **Full Internal Scan Chain** | Replaces standard DFFs with Scan-DFFs (`dff_scan`) | Medium (~15–25% area increase) / **2 pins** (`scan_en`, `scan_io`) | **Silicon Debug:** Provides 100% internal register controllability and observability. |

---

## 6. Board-Level Hardware & Bring-Up Architecture

The Tiny Tapeout Demo Carrier Board provides an integrated hardware test environment:

```
[Host Computer (Python Script / NumPy)]
                  │
                  │ (USB Serial CDC Link)
                  ▼
[Tiny Tapeout Demo Carrier Board] ── (Pre-assembled PCB)
   ├── RP2040 / RP2350 Microcontroller (Runs MicroPython or C-SDK Firmware)
   │        │
   │        │ (Pre-routed PCB traces drive CLK, RST, & SPI / Bitstreams)
   │        ▼
   └── Daughterboard Socket (Houses the Custom Fabricated ASIC)
```

* **Microcontroller Role (RP2040 / RP2350):** Features hardware **Programmable I/O (PIO)** state machines to generate jitter-free clocks, custom serial frame strobes, and real-time stochastic bitstream generation/sampling without CPU overhead.
* **DCIM vs. SCIM Bring-Up Difficulty:** **Digital CIM is significantly easier to verify on day one** because output results are 100% deterministic integers, allowing immediate cycle-by-cycle and single-step clock tracing.

---

## 7. Open-Source Toolstack Mapping

| Phase | Purpose | Open-Source Tool | Commercial Equivalent |
|---|---|---|---|
| **Modeling** | Algorithmic golden model & quantization | **Python** (`NumPy`, `PyTorch`) | MATLAB / Simulink |
| **RTL Design & Lint** | HDL development & linting | **Verilator** (lint), **VS Code** | Synopsys SpyGlass, Cadence Verif |
| **Verification** | Behavioral testbench & simulation | **Cocotb**, **Icarus Verilog** (`iverilog`), **Verilator** | Synopsys VCS, Cadence Xcelium |
| **Waveform Debug** | Signal inspection & X-tracing | **GTKWave**, **Surfer** | Synopsys Verdi |
| **Synthesis** | RTL-to-gate mapping & optimization | **Yosys** + **ABC** | Synopsys Design Compiler, Cadence Genus |
| **Place-and-Route** | Floorplan, placement, CTS, & routing | **OpenROAD** / **OpenLane 2** | Cadence Innovus, Synopsys ICC2 |
| **Timing Analysis** | Multi-corner Static Timing Analysis | **OpenSTA** | Synopsys PrimeTime, Cadence Tempus |
| **Physical Sign-Off** | DRC and LVS physical verification | **Magic** (DRC), **Netgen** (LVS), **KLayout** | Siemens Calibre DRC/LVS |
| **Layout Viewing** | GDSII visual inspection | **KLayout** | Cadence Virtuoso |
| **Silicon Firmware** | Microcontroller driver & stimulus | **MicroPython**, **GCC ARM Embedded** | Keil MDK, IAR Workbench |
| **Protocol Analysis**| Logic capture & SPI decoding | **PulseView** / **Sigrok** | Saleae Logic, Keysight Logic Analyzers |
| **Host Automation** | Automated USB test runner | **Python** (`pySerial`, `cocotb-test`) | LabVIEW, NI TestStand |

---

## 8. Verified Literature & References

### Digital Compute-in-Memory (DCIM)
* **Comprehensive Review:**
  * *A Review of SRAM-Based Compute-in-Memory Circuits (K. Yoshioka et al., JJAP/SSDM):*  
    [Japanese Journal of Applied Physics (DOI: 10.35848/1347-4065/ad93e0)](https://doi.org/10.35848/1347-4065/ad93e0) | [ResearchGate Publication Record](https://www.researchgate.net/publication/385918862_A_review_of_SRAM-based_compute-in-memory_circuits)
  * *Digital In-Memory Computing to Accelerate Deep Learning Inference on the Edge (S. Perri et al., IEEE IPDPS/RAW):*  
    [ResearchGate Full-Text Preprint](https://www.researchgate.net/publication/379484756_Digital_In-Memory_Computing_to_Accelerate_Deep_Learning_Inference_on_the_Edge_Invited_Paper) | [DBLP Index Record](https://dblp.org/rec/conf/ipps/PerriSSCF24.html)
* **Architecture & Compilers:**
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

### Official Open-Source Repositories & Docs
* **Verification:** [Cocotb Documentation](https://docs.cocotb.org/) | [Icarus Verilog GitHub](https://github.com/steveicarus/iverilog) | [Verilator](https://www.verilator.org/)
* **Physical ASIC Flow:** [OpenLane 2 Documentation](https://openlane.readthedocs.io/) | [OpenROAD Project](https://theopenroadproject.org/) | [KLayout](https://www.klayout.de/) | [OpenRAM Compiler](https://openram.org/)
* **Shuttle & Silicon Access:** [Tiny Tapeout](https://tinytapeout.com/) | [Tiny Tapeout Docs](https://docs.tinytapeout.com/) | [Tiny Tapeout GitHub](https://github.com/TinyTapeout) | [IHP Open PDK](https://github.com/IHP-GmbH/IHP-Open-PDK)
