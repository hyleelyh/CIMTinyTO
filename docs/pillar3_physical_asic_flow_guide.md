# Pillar 3: Physical ASIC Flow & Silicon Hardening Guide

**Document:** `docs/pillar3_physical_asic_flow_guide.md`  
**Audience:** Chip Lead & Semiconductor Engineer  
**Project:** CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)  
**Target Process:** SkyWater 130nm (`sky130A` / `sky130_fd_sc_hd`) on Tiny Tapeout ($1\times 2$ Tile)

---

## 1. Executive Overview: From Verilog Code to Physical Silicon

In front-end design (Pillars 1 and 2), Verilog describes behavior in zero-delay mathematical abstraction. In physical ASIC design (Pillar 3), we transform that behavioral description into geometric polygons of diffusion, polysilicon, contacts, and metal wires fabricated on a physical silicon wafer.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        Physical ASIC Implementation Flow                               │
└────────────────────────────────────────────────────────────────────────────────────────┘
  [1. Synthesis]        Verilog RTL  ──►  Logic Gate Netlist (Yosys)
                             │
  [2. Floorplan]        Die Dimensions & Power Grid (VDD/VSS Straps)
                             │
  [3. Placement]        Standard Cell Positioning & Legalization (RePlace)
                             │
  [4. HFN Buffering]    Reset & High-Fanout Buffer Insertion
                             │
  [5. CTS]              Balanced Clock Distribution Tree (TritonCTS)
                             │
  [6. Routing]          Interconnect Wiring across Metal 1..4 (TritonRoute)
                             │
  [7. Sign-Off]         DRC (Magic) + LVS (Netgen) + STA (OpenSTA)  ──►  GDSII Silicon Mask
```

---

## 2. Step 1: Logic Synthesis & Technology Mapping (Yosys)

### What Happens in Silicon
Synthesis converts RTL `always` blocks, additions, and multiplexers into a Directed Acyclic Graph (DAG) of boolean equations, then maps those equations to standard cells from the `sky130_fd_sc_hd` library.

```
                  Behavioral Verilog:
                  wire [4:0] p_col;
                  assign delta = (mode == 2'b00) ? p_col : (2 * p_col - 16);
                                       │
                                       ▼ (Yosys Tech Mapping)
                  Physical Standard Cells:
                  sky130_fd_sc_hd__mux2_1  (Multiplexer)
                  sky130_fd_sc_hd__xnor2_1 (XNOR Multiplier)
                  sky130_fd_sc_hd__dfxtp_1 (D-Flip-Flop)
```

### Standard Cell Anatomy (`sky130_fd_sc_hd`)
* **Height:** Fixed at $2.72\,\mu\text{m}$ (7 routing tracks high).
* **Width:** Variable in integer multiples of the site pitch ($0.46\,\mu\text{m}$).
* **Drive Strengths (`_1`, `_2`, `_4`):**
  The drive strength indicates transistor gate width ($W$).
  $$I_{\text{ds}} \propto \frac{W}{L} (V_{\text{gs}} - V_{\text{th}})^2$$
  - `_1` (Weak): Smallest area, high output resistance ($R_{\text{on}}$). Used for local, low-capacitance nets.
  - `_2` / `_4` (Strong): Wider transistors, lower $R_{\text{on}}$. Drives longer interconnect wires and high fanout loads rapidly.

### Trap & Silicon Guardrail: Unintentional Latches
If an `always @(*)` combinational block leaves any condition unspecified, synthesis infers a **level-sensitive transparent latch** (`dlxtp`). 
* In simulation, latches may appear to work.
* On physical silicon, latches are transparent whenever the enable is high, creating race conditions, severe hold violations across PVT corners, and huge static leakage.
* **Our Guardrail:** `scripts/parse_yosys_stat.py` audits every cell in the netlist. Any inferred latch immediately fails the build with exit code 1.

---

## 3. Step 2: Floorplanning & Power Distribution Network (PDN)

### Die Footprint & Density Calculation
Tiny Tapeout uses a standardized grid of tiles:
* **$1\times 1$ Tile:** $\approx 161\,\mu\text{m} \times 112\,\mu\text{m}$ ($\approx 18,000\,\mu\text{m}^2$). Usable core area $\approx 11,000\,\mu\text{m}^2$.
* **$1\times 2$ Tile (Our Choice):** $\approx 161\,\mu\text{m} \times 226\,\mu\text{m}$ ($\approx 36,386\,\mu\text{m}^2$). Usable core area $\approx 25,000\,\mu\text{m}^2$.

Our macro requires $\approx 21,400\,\mu\text{m}^2$ of standard-cell silicon area:
$$\text{Core Placement Density} = \frac{\text{Cell Area}}{\text{Usable Core Area}} = \frac{14,700\,\mu\text{m}^2}{25,000\,\mu\text{m}^2} \approx \mathbf{58.8\%}$$

> [!NOTE]
> **Why not 80% or 90% density?**
> A density $> 65\%$ leaves too few routing channels. When 16 columns of 16-to-5 Wallace trees route towards the accumulator bank, metal congestion causes routing DRC violations (shorts and minimum-spacing violations). A $58.8\%$ density leaves $41.2\%$ whitespace for routing channels and timing buffers.

### Power Distribution Network & $IR$ Drop
Dynamic power draw creates transient supply noise:
$$V_{\text{drop}} = I_{\text{peak}} \cdot R_{\text{grid}}$$
If $V_{\text{drop}}$ exceeds $10\%$ ($180\,\text{mV}$ on a $1.8\,\text{V}$ rail), standard-cell propagation delays increase drastically, causing setup violations.
* **Metal Grid:** `met4` carries thick vertical power straps, while `met1` forms continuous horizontal power rails abutting every standard cell row.
* **Decap Cells:** We configure OpenLane to sprinkle decoupling capacitors (`sky130_fd_sc_hd__decap_*`) throughout empty whitespace. These act as local charge reservoirs to suppress $L \frac{di}{dt}$ noise during clock edges.

---

## 4. Step 3: High-Fanout Net (HFN) Buffering & Reset Trees

### The Physics of High Fanout
Every transistor gate adds input capacitance ($C_{\text{in}} \approx 2\text{–}5\,\text{fF}$).
When a single driver feeds hundreds of gates:
$$C_{\text{total}} = \sum C_{\text{in}} + C_{\text{wire}}$$
The transition slew rate degrades proportionally:
$$t_{\text{slew}} \approx 2.2 \cdot R_{\text{driver}} \cdot C_{\text{total}}$$
Without buffering, a net driving 761 flip-flops exhibits a slew $> 8\,\text{ns}$! During this slow transition, standard cells draw high short-circuit power ($I_{\text{sc}}$), and clock/reset skew can cause hold-time races.

```
  UNBUFFERED (VULNERABLE):
  rst_sync ──┬──► DFF 0 (Load: 761 DFFs, Slew > 8ns, High Skew!)
             ├──► DFF 1
             └──► ... (761 loads)

  CLONED 4-DOMAIN (OUR SILICON HARDENING):
  rst_sync_ctrl   ──► Control FSM & Act Regs (153 DFFs)  [Slew < 0.8ns]
  rst_sync_weight ──► Weight Shift Memory    (256 DFFs)  [Slew < 0.9ns]
  rst_sync_sng    ──► LFSR SNG Bank          (128 DFFs)  [Slew < 0.7ns]
  rst_sync_acc    ──► Accumulator Bank       (224 DFFs)  [Slew < 0.8ns]
```

By adding `(* keep = "true" *)` in RTL (Hole #9 defense), we ensure Yosys preserves the 4 independent reset driver trees, capping maximum fanout at $\le 256$ DFFs per domain.

---

## 5. Step 4: Clock Tree Synthesis (TritonCTS)

### Setup vs. Hold Timing Physics

```
          Launch Clock (T_clk,launch)             Capture Clock (T_clk,capture)
                     │                                         │
                     ▼                                         ▼
               ┌───────────┐                             ┌───────────┐
               │ Launch    │                             │ Capture   │
    Data In ──►│ Flop      │──────[ Combinational ]─────►│ Flop      ├──► Data Out
               │ (DFF 1)   │       Logic (Wallace Tree)  │ (DFF 2)   │
               └───────────┘                             └───────────┘
```

#### 1. Setup Time Margin (Max Delay Path)
Data launched by DFF 1 must arrive at DFF 2 before the next clock edge:
$$T_{\text{clk}} + \Delta T_{\text{skew}} \ge T_{\text{c-q}} + T_{\text{comb, max}} + T_{\text{setup}} + T_{\text{margin}}$$
* **If setup fails:** You can fix it post-silicon by **reducing clock frequency** ($T_{\text{clk}} \uparrow$).

#### 2. Hold Time Margin (Min Delay Path — FATAL SILICON RISK)
Data launched by DFF 1 on the current edge must NOT race through and overwrite DFF 2 before DFF 2 has finished capturing its previous value:
$$T_{\text{c-q}} + T_{\text{comb, min}} \ge T_{\text{hold}} + \Delta T_{\text{skew}} + T_{\text{margin}}$$
* **CRITICAL SILICON REALITY:** Notice that $T_{\text{clk}}$ does NOT appear in the hold equation!
* **If hold fails on silicon, the chip is dead.** Running the clock at $1\text{ Hz}$ or even stopping the clock will not save it, because the race happens within picoseconds of the clock edge.

### How OpenROAD Closes Hold Slack
In `src/config.json`, we specify:
* `PL_RESIZER_HOLD_SLACK_MARGIN: 0.1` ($100\,\text{ps}$)
* `GLB_RESIZER_HOLD_SLACK_MARGIN: 0.05` ($50\,\text{ps}$)
OpenROAD intentionally inserts pairs of delay buffers (`sky130_fd_sc_hd__dlymetal6s2s_1` or inverter pairs) on fast short paths (like serial weight shift registers) to ensure $T_{\text{slack, hold}} \ge +0.10\,\text{ns}$ across all process corners.

---

## 6. Step 5: Detailed Routing & The Antenna Effect (TritonRoute)

### Routing Stack in Tiny Tapeout
* **`li1` (Local Interconnect):** Connects internal standard-cell transistors (polysilicon and diffusion).
* **`met1` & `met2`:** Standard cell pin connections and horizontal/vertical intra-macro wiring.
* **`met3` & `met4`:** Long-distance bus lines (broadcast activations, accumulator readback).
* **`met5`:** Reserved for top-level shuttle multiplexer and power grid (restricted via `RT_MAX_LAYER: "met4"`).

### The Antenna Effect & Diode Protection
During fabrication, metal layers are etched using **reactive ion etching (RIE) / plasma etching**. 
* A long exposed metal wire acts like an antenna, collecting ions and accumulating static charge.
* If that metal line connects to a MOSFET gate with no discharge path to the substrate, the electrostatic voltage can exceed the gate oxide breakdown field ($E_{\text{ox}} > 10\text{ MV/cm}$), destroying the $2\,\text{nm}$ $\text{SiO}_2$ dielectric!
* **Antenna Ratio Rule:** $\frac{A_{\text{metal}}}{A_{\text{gate}}} \le 400$.
* **Our Protection:** We enable `RUN_ANTENNA_CHECKER: true` and specify `DIODE_CELL: "sky130_fd_sc_hd__diode_2"`. If any long wire exceeds the ratio, OpenROAD automatically inserts a reverse-biased PN junction diode connecting the gate to $V_{\text{SS}}$, clamping the plasma voltage safely to $< 0.7\,\text{V}$.

---

## 7. Step 6: Physical Sign-Off (DRC & LVS)

Before mask tooling, three independent audits guarantee silicon yield:

### 1. Magic DRC (Design Rule Checking)
Verifies physical geometrical rules required by the SkyWater foundry:
* Minimum metal spacing (prevents electrical shorts).
* Minimum wire width (prevents electromigration voids).
* Minimum via enclosure (guarantees interlayer contact reliability).
* **Target:** **0 DRC errors**.

### 2. Netgen LVS (Layout vs. Schematic)
Extracts a transistor netlist directly from the physical GDS polygons and performs graph isomorphism against the synthesized Verilog gate-level netlist:
* Verifies that every single wire, transistor, and port matches bit-for-bit.
* Detects any open circuits or accidental bridging.
* **Target:** **0 LVS errors (Circuits match uniquely)**.

### 3. Static Timing Analysis (OpenSTA)
Evaluates setup and hold slacks across multiple PVT corners:
* **Worst Negative Slack (WNS):** Must be $\ge 0.00\,\text{ns}$ at $50\text{ MHz}$.
* **Worst Hold Slack (WHS):** Must be $\ge +0.10\,\text{ns}$.
