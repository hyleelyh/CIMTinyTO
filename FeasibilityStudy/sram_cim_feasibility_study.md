# SRAM Compute-in-Memory (CIM) & Stochastic CIM: Feasibility & Verification Study

## 1. Executive Summary & Feasibility Overview

This document synthesizes the architectural, verification, and tooling feasibility of designing, synthesizing, and validating a standard-cell **Digital Compute-in-Memory (DCIM)** or **Stochastic Compute-in-Memory (SCIM)** accelerator targeted for low-cost educational/shuttle tapeouts (e.g., Tiny Tapeout / SkyWater 130nm / IHP SG13G2) utilizing an AI-assisted open-source EDA flow.

### Key Feasibility Takeaways
* **Design Complexity (Low to Moderate):** Standard-cell DCIM and SCIM bypass analog bitcell design, customized DRC/LVS rules, sensitive sense amplifiers, and ADC/DAC peripherals.
* **Open-Source Tooling Overhead (Zero License Cost):** The entire RTL-to-GDSII and verification chain is fully supported by open-source tools (`iverilog`, `cocotb`, `GTKWave`, `Yosys`, `OpenROAD`/`OpenLane 2`, `Magic`, `Netgen`, `KLayout`).
* **Hardware & Board-Level Bring-Up Barrier (Minimal):** Validation requires only a micro-controller-driven carrier board (e.g., RP2040/RP2350 over USB) and a basic USB logic analyzer to execute cycle-accurate and statistical test vectors.
* **Primary Physical Constraint:** Standard cell density vs. array size. A single Tiny Tapeout tile (~$160 \times 100\ \mu\text{m}$) accommodates roughly 800–1,200 standard cells. Target initial prototypes to $8\times 8$ or $16\times 16$ 1-bit/stochastic PEs (or scale across $1\times 2$ / $2\times 2$ multi-tile allocations).

---

## 2. Architecture Comparison: Analog CIM vs. Digital CIM vs. Stochastic CIM

| Dimension | Mixed-Signal / Analog CIM | Fully Digital CIM (DCIM) | Stochastic CIM (SCIM) |
|---|---|---|---|
| **Computation Mechanism** | Charge sharing / current accumulation on bitlines | Synthesized logic gates (XOR, AND, Adder trees) | Bitstream probability multiplication (single AND/XNOR) |
| **Storage Element** | Custom 6T/8T/10T SRAM bitcells | Standard D-Flip-Flops (DFFs) / Latches | Register banks / DFF arrays |
| **Energy Efficiency** | Ultra-high (>50 TOPS/W) | High (10–30 TOPS/W) | High (Ultra-low active switching energy) |
| **Deterministic Accuracy** | Sensitive to $V_{th}$ mismatch, noise, PVT, IR drop | 100% deterministic & bit-exact | Statistical convergence (Error scales with $1/\sqrt{N}$) |
| **Peripheral Overhead** | Dominant (Flash / SAR ADCs require huge area) | Minimal (Standard digital multiplexers & registers) | Minimal (Shared LFSRs/SNGs + Counter accumulators) |
| **OpenLane/OpenROAD Fit** | Difficult (Requires custom analog macro integration) | 100% Native Standard Cell Flow | 100% Native Standard Cell Flow |
| **Tiny Tapeout Suitability** | Low (Pin & macro layout constraints) | High ($8\times 8$ to $16\times 16$ array) | Extremely High (Minimal gate count per multiplier) |

---

## 3. End-to-End Verification Flow

The design flow utilizes identical test vectors spanning from software simulation to physical silicon bring-up:

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

### Pre-Silicon vs. Post-Silicon Risk Mitigation

| Stage | Primary Risk | Mitigation Strategy |
|---|---|---|
| **Pre-Silicon** | Asynchronous clock domain race conditions | Enforce a single synchronous clock domain with enable strobes. |
| **Pre-Silicon** | OpenLane clock tree or hold-time violations | Add clock margin during synthesis; inspect OpenSTA hold slack reports. |
| **Pre-Silicon** | Netlist register pruning by Yosys | Verify output connectivity and inspect synthesis cell count summaries. |
| **Post-Silicon** | Lack of internal state observability | Route status flags (`busy`, `done`, `overflow`) and debug taps to dedicated output pins. |
| **Post-Silicon** | Weight loading corruption during shifting | Implement a deterministic SPI/shift loopback readback mode prior to compute execution. |

---

## 4. AI-Assisted Workflow vs. Human Inspection Requirements

While AI functions as a high-speed ASIC pair-programmer, human engineering oversight is necessary at each stage.

```
[System Model] ──► [Synthesizable RTL] ──► [Cocotb Sim] ──► [OpenLane/GDSII] ──► [Silicon Bring-Up]
 (PyTorch/NumPy)       (Verilog HDL)        (Icarus/Verilator)    (GitHub CI/Actions)   (RP2040 / Python)
       │                     │                     │                      │                    │
   AI Writes             AI Writes             AI Writes              AI Debugs            AI Writes
   Algorithmic           Module Code &         Testbenches &          Reports &            Bring-Up &
   Baseline              I/O Adapters          Edge Vectors           Timing Logs          Driver Scripts
```

### Required Human Engineering Knowledge by Stage

#### 1. Specification & Architecture Review
* **Fixed-Point Arithmetic & Dynamic Range:** Understanding two's complement vs. sign-magnitude math, overflow behavior, and bit-growth ($W_{\text{acc}} \ge W_{\text{mult}} + \lceil \log_2(\text{Rows}) \rceil$).
* **I/O Multiplexing:** Budgeting limited ASIC pins (Tiny Tapeout: 8 inputs, 8 outputs, 8 bidir) using shift registers or SPI protocols.
* **Synchronous Clock Discipline:** Eliminating internally generated, divided, or asynchronous clocks.

#### 2. RTL & Microarchitecture Inspection
* **Latch Prevention:** Eliminating missing `default` branches or incomplete `if-else` cascades in combinational `always @(*)` blocks.
* **FSM Robustness:** Ensuring explicit `default` recovery states to prevent lockups on glitch states.
* **DFT & Observability:** Providing internal array readback capabilities before triggering execution.

#### 3. Pre-Silicon Verification (Cocotb & Simulation)
* **Corner-Case Coverage:** Testing zero matrices, maximum saturation values, alternating bit patterns (`0xAA`/`0x55`), and back-to-back operations.
* **GLS & 'X' Propagation Debugging:** Diagnosing 4-state simulation unknowns caused by uninitialized flip-flops or missing reset lines.
* **Golden Model Alignment:** Enforcing exact bit-level truncation and saturation parity between Python and RTL.

#### 4. Physical Synthesis & Place-and-Route (OpenLane / OpenROAD)
* **Synthesis Netlist Auditing:** Verifying that Yosys did not optimize away memory cells due to undriven/dangling nets.
* **Static Timing Analysis (STA):** Distinguishing setup violations (fixable by lowering clock frequency) from **hold violations** (fatal; must be zero prior to tapeout).
* **Physical Checks:** Ensuring zero DRC errors, zero LVS mismatches, and safe antenna diode insertion.

#### 5. Post-Silicon Bring-Up & Board Validation
* **Digital Test Equipment Operation:** Configuring logic analyzer triggering on chip-select, strobe, and clock pins.
* **Signal Integrity & Electrical Basics:** Managing pull-up/pull-down resistors, capacitance loading, and I/O level compatibility ($3.3\text{V}$ vs. $1.8\text{V}$).
* **Systematic Bring-Up Sequence:** Isolating power $\rightarrow$ clock $\rightarrow$ reset $\rightarrow$ register readback $\rightarrow$ compute validation.

---

## 5. Complete Open-Source Toolstack Mapping

| Phase | Purpose | Open-Source Tool | Proprietary / Commercial Equivalent |
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

## 6. Board-Level Validation Protocol for Stochastic CIM (SCIM)

Testing a Stochastic CIM ASIC at the board level requires validating both deterministic digital I/O and statistical output convergence:

1. **Step 1: Sanity & Loopback**
   * Confirm power supply rails ($3.3\text{V}$ I/O, $1.8\text{V}$ Core) and release reset.
   * Write test patterns via SPI into weight registers and read back to verify 100% data retention.
2. **Step 2: Deterministic Boundary Testing**
   * Stream all-0 ($P=0.0$) and all-1 ($P=1.0$) bitstreams. Confirm accumulator registers output boundary limits with zero variance.
3. **Step 3: Single-Gate Stochastic Multiplier Check**
   * Drive known probability inputs (e.g., $P_A = 0.5, P_B = 0.5$). Verify output converges to $P_{\text{out}} \approx 0.25$ over large bitstream runs.
4. **Step 4: Precision vs. Length ($N$) Scaling Analysis**
   * Sweep bitstream lengths ($N = 64, 256, 1024, 4096$ cycles). Confirm standard deviation of error drops along theoretical $1/\sqrt{N}$ curve.
5. **Step 5: Full Matrix-Vector Multiplication (MVM)**
   * Stream full activation vectors against pre-loaded weight matrices across 1,000+ random trials. Compare physical silicon output against the Python model to verify results stay within $\pm 3\sigma$ binomial error bounds.
6. **Step 6: Frequency & Voltage Shmoo Plotting**
   * Sweep clock frequency ($1\text{–}50\text{ MHz}$) and core voltage ($1.5\text{V} \text{–} 1.9\text{V}$) to map operational stability bounds.

---

## 7. Pre-Tapeout & Sign-Off Inspection Checklist

### Phase 1: RTL Code Inspection
- [ ] **Single Clock Domain:** All sequential logic uses `posedge clk` with synchronous enable gating.
- [ ] **Reset Discipline:** Consistent active-low `if (!rst_n)` across all modules; all control registers reset cleanly.
- [ ] **Zero Inferred Latches:** All combinational blocks assign all outputs across all branches with explicit `default` clauses.
- [ ] **FSM Recovery:** State machines include `default: state <= IDLE;` to recover safely from illegal states.
- [ ] **Accumulator Bit-Width:** Accumulators sized with bit-growth margins ($W_{\text{acc}} \ge W_{\text{mult}} + \lceil \log_2(\text{Rows}) \rceil$).
- [ ] **Memory Observability:** Readback path implemented to verify weight loading prior to computation.

### Phase 2: Cocotb Pre-Silicon Verification
- [ ] **Bit-Accurate Golden Model:** Python model strictly replicates hardware fixed-point truncation and rounding.
- [ ] **Corner Cases Verified:** All-zero, max-value, alternating (`0x55`/`0xAA`), and back-to-back transaction tests pass.
- [ ] **Reset Recovery Test:** Mid-operation reset assertion validates clean state recovery.
- [ ] **Gate-Level Simulation (GLS):** Post-synthesis and post-PnR netlists simulate with zero unknown `X` propagation.

### Phase 3: OpenLane / OpenROAD Sign-Off Logs
- [ ] **Synthesis Log Check (`synthesis.log`):** Cell count matches expected logic; no memory registers pruned by Yosys.
- [ ] **Static Timing (`OpenSTA`):** Setup slack $\ge 0$; **Hold slack $\ge 0$ with positive margin**.
- [ ] **Placement Density:** Core utilization budgeted between 40%–55% to prevent routing congestion.
- [ ] **Physical Verification:** Magic DRC count = 0, Netgen LVS mismatches = 0, and antenna diode checks clear.
