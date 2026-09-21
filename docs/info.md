# CIMTinyTO: Stochastic & Digital Compute-in-Memory Accelerator

## 1. Overview & Architectural Innovation

**CIMTinyTO** is an open-source, standard-cell **Stochastic Compute-in-Memory (SCIM)** and **Digital Compute-in-Memory (DCIM)** accelerator macro designed for the **SkyWater 130nm** (`sky130_fd_sc_hd`) process on **Tiny Tapeout** ($1\times 2$ tile footprint).

Standard analog/mixed-signal CIM macros rely on custom analog SRAM bitcells, sensitive analog sense amplifiers, and power-hungry Flash/SAR ADCs—elements that are prone to PVT variation and violate standard digital ASIC flow rules. 

**CIMTinyTO** eliminates all analog components by combining:
1. **Stochastic Computing (SC):** Multi-bit integer multiplications are replaced by single-gate logical operations (AND for unipolar, XNOR for bipolar, and masked AND for hybrid activations).
2. **Standard-Cell DFF Memory Fabric:** 256 weight flip-flops configured as a serial shift register with full Design-for-Testability (DFT) loopback (`w_dout`).
3. **Unified Column Delta Reduction:** Conventional bipolar CIM requires two separate Wallace trees per column to sum positive and negative pulses ($16 \times 2 = 32$ trees), exceeding the Tiny Tapeout area budget. CIMTinyTO solves this by mathematically proving:
   $$\Delta_{\text{col}} = 2 \cdot P_{\text{col}} - A$$
   where $P_{\text{col}}$ is the column pulse count and $A = \sum_{i=0}^{15} a_i$ is the total active activation count, computed **once** by a single shared activation tree and broadcast to all 16 columns. This cuts macro tree count from 32 down to 17, saving $\approx 855$ standard cells!

---

## 2. Operating Modes

The accelerator natively supports three operating modes configured via `ui_in[1:0]` during a `ctrl_strobe` pulse:

| Mode | Name | PE Operation | Mathematics | Applications |
|---|---|---|---|---|
| `2'b00` | **Mode 0: Unipolar** | Single `AND` gate | $W \in \{0, 1\}$, $X \in [0, 1]$ | Binary networks, boolean pattern matching |
| `2'b01` | **Mode 1: Bipolar** | Single `XNOR` gate | $W \in \{-1, +1\}$, $X \in [-1, +1]$ | Binarized Neural Networks (BNN), XNOR-Nets |
| `2'b10` | **Mode 2: Hybrid ReLU** | Masked `AND` gate | $W \in \{-1, +1\}$, $X \in [0, 1]$ | Quantized CNNs (Micro-ResNet, MobileNet) |
| `2'b11` | *Reserved* | Clamped to 0 | Safety interlock (Hole #10 defense) | Suppresses invalid mode transitions |

---

## 3. Hardware Pinout Mapping

### Dedicated Inputs (`ui_in[7:0]`)
* When idle or during compute: `ui_in[7:0]` feeds 8-bit activation bytes and configuration commands.
* During readback (`busy == 0`): `ui_in[4:0]` selects which accumulator channel (0 to 15) and byte (Low `[7:0]` or High `[12:8]`) is multiplexed onto `uo_out[7:0]`.

### Dedicated Outputs (`uo_out[7:0]`)
* **Pad Quiescence Hardening (Hole #8):** Driven to `8'h00` during the 256-cycle compute phase to eliminate $\approx 108\text{ mW}$ of dynamic pad switching power and protect against ground bounce ($L \frac{di}{dt}$).
* In readback mode (`busy == 0`): Emits the selected 8-bit accumulator slice.

### Bidirectional I/Os (`uio[7:0]`)
Configured as `uio_oe = 8'b0000_1111` (upper nibble input, lower nibble output):

| Pin | Direction | Signal | Description |
|---|---|---|---|
| `uio[0]` | Output | `busy` | High while the 256-cycle stochastic compute phase is active. |
| `uio[1]` | Output | `done` | 1-cycle active-high completion strobe at end of compute. |
| `uio[2]` | Output | `w_dout` | Serial weight loopback for non-destructive shift verification (DFT). |
| `uio[3]` | Output | `overflow` | Latched saturation flag if any 13-bit accumulator saturated ($\pm 4095$). |
| `uio[4]` | Input | `w_din` | Serial weight data bit input. |
| `uio[5]` | Input | `w_shift_en` | Weight shift enable (interlocked: ignored when `busy == 1`). |
| `uio[6]` | Input | `wr_act` | Activation register write strobe (auto-increments channel 0..15). |
| `uio[7]` | Input | `ctrl_strobe` | Command strobe to latch operating mode and trigger compute. |

---

## 4. Operational & Programming Protocol

1. **Reset Initialization:**
   Assert `rst_n = 0` for $\ge 3$ clock cycles to clear the 2-stage synchronizer, reset LFSRs to their stride-15 seeds, and zero the accumulators.

2. **Weight Matrix Programming (256 Cycles):**
   * Assert `w_shift_en = 1`.
   * For 256 consecutive clock cycles, clock in the $16 \times 16$ weight bits via `w_din`.
   * *Verification:* Observe `w_dout` on `uio[2]` to verify shift-register chain continuity.

3. **Activation Loading (16 Writes):**
   * Place an 8-bit activation byte on `ui_in[7:0]` and pulse `wr_act = 1` for 1 cycle.
   * Repeat 16 times. An internal counter automatically increments channel address $0 \rightarrow 15$.

4. **Compute Triggering (1 Cycle):**
   * Set `ui_in[1:0]` to the desired mode (`00`, `01`, or `10`).
   * Set `ui_in[2] = 1` (`START_COMPUTE` command).
   * Pulse `ctrl_strobe = 1` for 1 cycle.
   * The core asserts `busy = 1` and executes for exactly 256 clock cycles ($N = 256$).

5. **Accumulator Readback:**
   * After 256 cycles, `busy` drops to 0 and `done` pulses high for 1 cycle.
   * Set `ui_in[3:0] = col_idx` (0 to 15).
   * Set `ui_in[4] = 0` to read low byte (`uo_out[7:0] = acc[7:0]`).
   * Set `ui_in[4] = 1` to read sign-extended high byte (`uo_out[7:0] = {{3{acc[12]}}, acc[12:8]}`).

---

## 5. Physical Implementation & Sign-Off Specs

* **Foundry & Node:** SkyWater 130nm (`sky130A`)
* **Standard Cell Library:** `sky130_fd_sc_hd` (High Density, 7-track, $2.72\,\mu\text{m}$ height)
* **Tile Footprint:** Tiny Tapeout $1\times 2$ Tile ($\approx 161\,\mu\text{m} \times 226\,\mu\text{m}$, gross area $\approx 36,386\,\mu\text{m}^2$)
* **Core Placement Density:** Target $\mathbf{58.8\%}$ (leaving $41.2\%$ whitespace for routing channels and buffer insertion)
* **Clock Frequency:** Target **$50\text{ MHz}$** ($T_{\text{clk}} = 20.0\,\text{ns}$)
* **Total Inference Latency:** $256 \times 20\,\text{ns} = \mathbf{5.12\,\mu\text{s}}$ per $16\times 16$ Matrix-Vector Multiply ($\mathbf{100,000,000\text{ MACs/sec}}$ throughput)
* **Sign-Off Criteria:** 0 Magic DRC errors, 0 Netgen LVS mismatches, Hold Slack $T_{\text{slack, hold}} \ge 0.10\,\text{ns}$
