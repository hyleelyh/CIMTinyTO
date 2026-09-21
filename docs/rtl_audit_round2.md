# RTL Audit & Silicon Vulnerability Report: "Poking Holes — Round 2"

**Document:** `docs/rtl_audit_round2.md`  
**Date:** 2026-09-21  
**Design Phase:** Pillar 2 (Gate 1: Verification Hardening & Silicon Reliability)  
**Target:** SkyWater 130nm / IHP SG13G2 (Tiny Tapeout)

---

## 1. Executive Summary: The "Round 2" Philosophy

In Round 1 (`docs/rtl_audit_and_poking_holes.md`), we hardened mathematical correctness (Hole #1 signed arithmetic, Hole #5 concatenation), basic reset synchronization (Hole #3), strobe bus arbitration (Hole #4), and verified Mode 1 coverage (Hole #2).

In **Round 2**, we shift focus from **algorithmic correctness** to **system-level silicon resilience**:
* What happens when the host microcontroller exhibits unexpected bus behavior or electrical noise?
* How does the physical I/O pad ring behave during active 50 MHz computation?
* What are the physical limits of high-fanout nets (HFN) in standard-cell CMOS placement?
* How do illegal or undefined control inputs behave?

We identified **5 new vulnerabilities and silicon traps** categorized by severity:

```plaintext
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     Summary of Poked Vulnerabilities — Round 2                         │
└────────────────────────────────────────────────────────────────────────────────────────┘
  [Hole #7: High]   Missing Weight Memory Shift Interlock during Active Compute
  [Hole #8: High]   Simultaneous Switching Outputs (SSO), Ground Bounce & Dynamic Pad Power
  [Hole #9: Medium] High-Fanout Reset Network (Fanout = 761 DFFs) & Slew Degradation
  [Hole #10: Med]   Incomplete FSM State Decoding & Illegal Mode (mode == 2'b11) Leakage
  [Hole #11: Cover] Absence of Constrained-Random Verification (CRV) Multi-Vector Stress
```

---

## 2. Detailed Vulnerability Analysis

### Hole #7 (High): Missing Weight Memory Shift Interlock during Compute

#### Location:
[`src/tt_um_scim_core.v:L68, L238-245`](file:///home/juliusli/Documents/AntiG/CIMTinyTO/src/tt_um_scim_core.v#L68)

```verilog
wire w_shift_en = uio_in[5]; // Serial weight shift enable

scim_weight_mem u_weight_mem (
    .clk(clk),
    .rst_n(core_rst_n),
    .w_shift_en(w_shift_en), // <--- Unprotected external pin!
    .w_din(w_din),
    .w_dout(w_dout),
    .weights_out(weight_matrix)
);
```

#### The Trap:
* In Section 2 of `tt_um_scim_core.v`, we meticulously protected `act_regs` and `addr` against mid-computation modification:
  ```verilog
  if (ctrl_strobe && !busy) ...
  else if (wr_act && !busy) ...
  ```
* **However, `w_shift_en` has NO `!busy` interlock!**
* If the host MCU (or electrical glitching on the board) pulses `uio_in[5]` while `busy == 1` (during `FSM_CLEAR` or `FSM_COMPUTE`), the 256-bit shift register advances.
* The entire spatial $16 \times 16$ weight matrix shifts by 1 bit mid-inference, completely scrambling trained neural network weights while the dot-product is actively accumulating!

#### Silicon Reality & Failure Mode:
On a physical testbench (RP2040 or FPGA), firmware bugs, SPI race conditions, or contact bounce on PMOD jumper pins can pulse `uio_in[5]`. The chip will silently produce garbage inference results with no hardware error flag asserted.

#### Recommended Defensive Fix:
Gate `w_shift_en` at the top level with `!busy`:
```verilog
wire safe_w_shift_en = w_shift_en && !busy;
```

---

### Hole #8 (High): Simultaneous Switching Outputs (SSO), Ground Bounce & Dynamic Pad Power

#### Location:
[`src/tt_um_scim_core.v:L346-353`](file:///home/juliusli/Documents/AntiG/CIMTinyTO/src/tt_um_scim_core.v#L346-L353)

```verilog
wire signed [12:0] selected_acc = acc_val[addr];
wire [7:0] acc_byte_low  = selected_acc[7:0];
wire [7:0] acc_byte_high = {{3{selected_acc[12]}}, selected_acc[12:8]};

assign uo_out = (byte_sel) ? acc_byte_high : acc_byte_low;
```

#### The Trap:
* `uo_out` is a combinational multiplexer connected directly to the output of accumulator `acc_val[addr]`.
* During `FSM_COMPUTE`, accumulator `acc_val[addr]` is actively updating on **every single clock cycle for 256 cycles**.
* Therefore, all 8 external output pads (`uo_out[7:0]`) are violently switching at 50 MHz throughout the entire compute phase!

#### Silicon Reality (The Physics of Ground Bounce & Pad Power):
1. **Dynamic Pad Power Dissipation:**
   * External I/O pads driving PCB traces, breadboard jumpers, and oscilloscope/analyzer probes have high load capacitance ($C_L \approx 20\text{--}30\,\text{pF}$).
   * In contrast, internal standard cells drive only $\approx 2\text{--}5\,\text{fF}$ ($>5000\times$ less!).
   * The dynamic power consumed by 8 pads toggling at 50 MHz is:
     $$P_{\text{pads}} = 8 \times C_L \times V_{DD}^2 \times f \approx 8 \times (25\,\text{pF}) \times (3.3\,\text{V})^2 \times (50\,\text{MHz}) \approx \mathbf{108\,\text{mW}}$$
   * The entire internal SCIM core consumes $< 10\,\text{mW}$. The unused live output pads burn **$10\times$ more energy than the computation itself**!
2. **Ground Bounce ($L \frac{di}{dt}$):**
   * When 8 output pads transition simultaneously from `1` to `0`, the instantaneous surge current rushing through the chip's bond wires and package ground pin ($L_{\text{package}} \approx 2\text{--}5\,\text{nH}$) causes a voltage spike:
     $$V_{\text{bounce}} = L \frac{di}{dt}$$
   * Ground bounce can induce false clock glitches on internal flip-flops and corrupt LFSR states!

#### Recommended Defensive Fix:
Gate `uo_out` so that the output pads remain completely static and quiet during active computation, updating only when `done == 1` (or register the outputs):
```verilog
assign uo_out = (done) ? ((byte_sel) ? acc_byte_high : acc_byte_low) : 8'h00;
```

---

### Hole #9 (Medium): High-Fanout Reset Network (`core_rst_n`) & Slew Degradation

#### Location:
[`src/tt_um_scim_core.v:L80-91`](file:///home/juliusli/Documents/AntiG/CIMTinyTO/src/tt_um_scim_core.v#L80-L91)

```verilog
reg rst_sync_0, rst_sync_1;
always @(posedge clk or negedge rst_n) begin ... end
wire core_rst_n = rst_sync_1;
```

#### The Trap:
* `rst_sync_1` is a single standard-cell flip-flop (`sky130_fd_sc_hd__dfrtp_1`).
* Its $Q$ output drives `core_rst_n` to every submodule across the macro:
  - 256 weight DFFs
  - 224 accumulator DFFs ($16 \times 14$)
  - 128 LFSR DFFs ($16 \times 8$)
  - 128 activation register DFFs ($16 \times 8$)
  - 25 FSM and control DFFs
  - **Total Fanout: 761 standard-cell flip-flops!**

#### Silicon Reality & Synthesis Trap:
* In Sky130 HD, a standard drive-1 DFF is rated for a load of $10\text{--}30\,\text{fF}$. Driving 761 gates ($C_L \approx 2.5\,\text{pF}$) will degrade signal transition time (slew) to $> 8\,\text{ns}$.
* If OpenLane's synthesis buffer insertion does not build an adequate buffer tree on `core_rst_n`, the slow transition will cause hold-time violations and clock-skewed reset deassertion across the die.

#### Recommended Defensive Fix & 3-Tier Dictations:

1. **Tier 1: RTL Register Cloning (Immediate Implementation):**
   Clone the 2nd synchronizer stage into 4 dedicated, domain-specific reset drivers, cutting maximum load from 761 down to $\le 256$ DFFs:
   ```verilog
   (* keep = "true" *) reg rst_sync_ctrl;   // Control/FSM & activations (~150 DFFs)
   (* keep = "true" *) reg rst_sync_weight; // Weight shift memory (256 DFFs)
   (* keep = "true" *) reg rst_sync_sng;    // SNG LFSR bank (128 DFFs)
   (* keep = "true" *) reg rst_sync_acc;    // Accumulator array (224 DFFs)
   ```
   *The `(* keep = "true" *)` attribute is mandatory to prevent Yosys from optimizing them back into a single high-fanout net.*

2. **Tier 2: SDC Timing Constraints (Pillar 3 Dictation):**
   In the physical constraints file `src/tt_um_scim_core.sdc`:
   ```tcl
   # Enforce maximum fanout per driver to guarantee sharp transition slew
   set_max_fanout 25 [current_design]
   set_max_transition 0.75 [current_design]
   set_max_fanout 20 [get_nets rst_*_n]
   ```

3. **Tier 3: OpenLane 2 / OpenROAD Flow Configuration (`config.yaml`):**
   ```yaml
   SYNTH_BUFFERING: 1
   SYNTH_MAX_FANOUT: 20
   SYNTH_STRATEGY: "AREA 0" # timing-driven synthesis with buffer insertion
   PL_RESIZER_BUFFER_INPUT_PORTS: 1
   PL_RESIZER_MAX_FANOUT: 25
   ```

---

### Hole #10 (Medium): Incomplete Mode Decoding & Illegal Mode (`mode == 2'b11`) Leakage

#### Location:
[`src/tt_um_scim_core.v:L314-315`](file:///home/juliusli/Documents/AntiG/CIMTinyTO/src/tt_um_scim_core.v#L314-L315)

```verilog
assign col_delta[col] = (mode == 2'b00) ? delta_mode0 :
                        (mode == 2'b01) ? delta_mode1_7b[5:0] : delta_mode2_7b[5:0];
```

#### The Trap:
* If the host writes `mode = 2'b11` (unsupported/reserved code):
  - In `scim_pe.v`, `default: pe_out = 1'b0;` forces all PE outputs to 0 ($P_{\text{col}} = 0$).
  - In `tt_um_scim_core.v`, the ternary `else` branch executes `delta_mode2_7b[5:0]`:
    $$\text{delta\_mode2} = 2(0) - A = -\mathbf{A}$$
  - The macro unexpectedly accumulates negative activation sums on every clock cycle instead of entering a safe quiescent state!

#### Recommended Defensive Fix:
Explicitly decode `2'b10` for Mode 2, and tie `default` / `2'b11` to `6'sd0`:
```verilog
assign col_delta[col] = (mode == 2'b00) ? delta_mode0 :
                        (mode == 2'b01) ? delta_mode1_7b[5:0] :
                        (mode == 2'b10) ? delta_mode2_7b[5:0] : 6'sd0;
```

---

### Hole #11 (Coverage): Absence of Constrained-Random Verification (CRV)

#### Location:
[`test/test_scim_core.py`](file:///home/juliusli/Documents/AntiG/CIMTinyTO/test/test_scim_core.py)

#### The Trap:
* Our test suite contains 10 hand-crafted deterministic vectors.
* Deterministic vectors only test hypotheses the designer consciously anticipated.
* They do not stress arbitrary weight patterns, random activation densities, or randomized interleaved control sequences.

#### Recommended Verification Fix:
Add an automated Constrained-Random Verification (CRV) suite in Cocotb executing **100 randomized trials** with pseudorandom seeds, verifying 100% bit-exact match against the Python golden model for every trial.

---

## 3. Summary of Round 2 Action Items

| Item | Severity | Impact Area | Proposed Fix |
|---|---|---|---|
| **Hole #7** | High | Silicon Integrity | Interlock `w_shift_en && !busy` |
| **Hole #8** | High | Power & Ground Bounce | Gate `uo_out` to 0 during compute (`done ? ... : 8'h00`) |
| **Hole #9** | Medium | Physical Timing / CTS | Add OpenLane HFN buffer tree constraints for `core_rst_n` |
| **Hole #10** | Medium | FSM / Robustness | Explicitly decode `mode == 2'b10` and clamp `2'b11` to 0 |
| **Hole #11** | Coverage | Verification Closure | Add 100-run Cocotb Constrained-Random Verification (CRV) test |
