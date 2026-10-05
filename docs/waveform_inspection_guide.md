# Silicon Waveform Inspection Guide — Pillar 5 GLS Forensics

This guide provides a comprehensive pedagogical reference for inspecting the gate-level simulation waveforms generated from the hardened Tiny Tapeout `ttsky26d` standard-cell macro (`tt_um_scim_core` on SkyWater 130nm).

---

## 1. Waveform Inventory

All waveform files are located in `test/`:

| Waveform File | File Size | Core Silicon Concept Under Inspection |
| :--- | :---: | :--- |
| **`test/waves_golden_vectors.vcd`** / **`.fst`** | $1.3\text{ MB}$ | **SNG Bernoulli Streams, Wallace Tree Compression & Pad Quiescence** |
| **`test/waves_dft_loopback.vcd`** / **`.fst`** | $355\text{ KB}$ | **Design-for-Test (DFT), Scan Chains & Silicon Defect Screening** |
| **`test/waves_saturation.vcd`** / **`.fst`** | $420\text{ KB}$ | **Arithmetic Saturation, Clamping & Sticky Alarm Registers** |
| **`test/waves_overclock_200mhz.vcd`** / **`.fst`** | $325\text{ KB}$ | **Logic Depth, Propagation Delay & 200 MHz Overclocking Margin** |
| **`test/tb.vcd`** / **`.fst`** | $5.9\text{ MB}$ | **Full System Lifecycle, Zero-Reset Inferences & Protocol Interlocks** |

*Note: High-speed `.fst` symlinks are provided alongside each `.vcd` for instantaneous scrubbing in GTKWave and the VS Code / Cursor **Surfer** extension.*

---

## 2. Viewing Instructions

### GTKWave (Host CLI)
```bash
# Open golden model test vector trace:
gtkwave test/waves_golden_vectors.vcd &

# Open complete 11-test regression trace:
gtkwave test/tb.vcd &
```

*GTKWave Tips:*
- **Ctrl + Scroll**: Zoom smoothly in and out.
- **Alt + F**: Fit the entire simulation timeline to window width.
- **Insert / Drag-and-Drop**: Add signals from the module tree (`tb -> user_project`).
- **Right-Click Signal -> Data Format**: Choose `Decimal`, `Signed Decimal`, or `Analog (Step)`.

---

## 3. Detailed Inspection Breakdown by Waveform

### A. `waves_golden_vectors.vcd` — Core Computing Engine & Pad Quiescence

#### The Silicon "Why"
In mixed-signal or digital compute-in-memory (CIM), the core challenge is calculating $16 \times 16 = 256$ multiply-accumulate (MAC) operations in parallel without exceeding the Tiny Tapeout power ($<5\text{ mW}$) and area budget.
* Instead of 256 multi-bit digital multipliers (which would require $\sim 40,000$ transistors), our macro serializes 8-bit activations into **stochastic Bernoulli bitstreams** over $N=256$ clock cycles.
* Multiplication reduces to a single 2-input AND gate per PE ($\Delta = a_i \cdot w_i$).
* Column summation is performed by a combinational **Wallace tree compressor** that reduces 16 parallel PE bits to a 5-bit column delta in under $2\text{ ns}$.

```
                 CYCLE-BY-CYCLE TIMING DIAGRAM (GOLDEN INFERENCE)

Clock (50MHz)   _|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|
                 |     |     |                       |                       |
ctrl_strobe     ____|‾|_____________________________________________________________  (uio_in[7])
ui_in[7:0]      ====[0x80/0x90]=====================================================  (Start + Mode)
                 |     |     |                       |                       |
busy (uio_out[0])___________|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|________  (256 cycles)
done (uio_out[1])___________________________________________________________|‾|_____  (Cycle 257)
                 |     |     |                       |                       |
uo_out[7:0]     ============[     STATIC 8'h00 (Hole #8 QUIESCENCE)     ]====[Data0][Data1]...
                             ^                                               ^
                       SNGs toggling,                                   Readout Mux
                       Gates switching,                                 active after
                       PADS SILENT                                      busy drops
```

#### Signal Probes to Add (GLS Physical Netlist)
1. **System & Handshake:** `tb.clk`, `tb.rst_n`, `tb.uio_in[7]` (`ctrl_strobe`), `tb.uio_out[0]` (`busy`), `tb.uio_out[1]` (`done`)
2. **External Data Pads:** `tb.ui_in[7:0]` (Inputs), `tb.uo_out[7:0]` (Readout Bus)
3. **Internal Physical Registers:** 
   - `tb.user_project.\cycle_cnt[0]` .. `\cycle_cnt[7]` (The 256-cycle counter flip-flops)
   - `tb.user_project.acc_clr`, `tb.user_project.acc_en` (Accumulator control)
   - `tb.user_project.\acc_val[0][0]` .. `tb.user_project.\acc_val[0][12]` (Column 0 Accumulator 13-bit flip-flops)

> [!NOTE]
> **Silicon Reality: Why `col_delta` is Not Present in Gate-Level Waveforms**
> In behavioral RTL Verilog, `col_delta[0][4:0]` is a named combinational wire connecting the Wallace tree to the accumulator. However, in **Gate-Level Simulation (GLS)**, we simulate the post-synthesis, post-route physical netlist ([`gds/tt_um_scim_core.v`](file:///home/juliusli/Documents/AntiG/CIMTinyTO/gds/tt_um_scim_core.v)). During standard-cell synthesis and technology mapping, Yosys and OpenLane flatten internal submodule boundaries and merge intermediate combinational wires directly into multi-stage standard-cell gates (`a21oi`, `fa`, `ha`). Because `col_delta` has no flip-flop register holding it, it is absorbed into anonymous physical interconnects (`_00xxx_` or gate pins). 
> 
> To observe Column 0 accumulating in GLS, probe the actual physical D-flip-flops: select `\acc_val[0][0]` through `\acc_val[0][12]` under `tb.user_project`, right-click -> **Combine Down** in GTKWave to form a 13-bit bus, and set format to **Signed Decimal** or **Analog (Step)**!

#### What to Look For
1. **The 256-Cycle Accumulation Run (Observe $T \approx 0$ to $12\,\mu\text{s}$):**
   * Watch `uio_out[0]` (`busy`) assert `HIGH`. For exactly 256 consecutive clock cycles, `cycle_cnt` increments from 0 to 255.
   * As the 13-bit accumulator bus `acc_val[0]` is clocked on every rising edge of `clk`, you will see it ramp monotonically up to its golden value (e.g. `255` on the identity matrix test vector). In GTKWave, right-click the combined bus -> **Toggle Trace Type -> Analog (Step)** to see the continuous accumulation stair-step!
2. **Hole #8 Pad Quiescence Verification:**
   * While `busy` is `HIGH`, observe `uo_out[7:0]`. It is held strictly flat at `8'h00` despite intense internal switching.
   * **Silicon Reality:** Board traces and PCB pins have capacitive loads of $10\text{–}15\text{ pF}$, whereas internal standard-cell wires are $\sim 5\text{–}10\text{ fF}$ ($1,500\times$ difference). Toggling 8 output pads on every cycle would burn $\approx 5.5\text{ mW}$ of dynamic pad power and create $L \cdot di/dt$ ground bounce on package bond wires. Gating the pads during compute completely prevents ground bounce.
3. **Two-Phase Readout After `done`:**
   * After cycle 256, `busy` drops to `0`, `done` pulses for 1 cycle, and the external controller sweeps `addr` from `0` to `15` and `byte_sel` between `0` and `1`.
   * `uo_out[7:0]` transitions from `8'h00` to stream out the low byte and high byte for each of the 16 columns.

---

### B. `waves_dft_loopback.vcd` — Design-for-Test (DFT) Scan Chains

#### The Silicon "Why"
When an ASIC returns from manufacturing, dust particles or lithographic defects can cause open circuits or bridging shorts. 
* To test 256 internal weight flip-flops without requiring hundreds of I/O pins, we built a **serial scan chain** connecting all 256 weight DFFs into a continuous shift register.
* Shifting a known pseudorandom bitstream into `w_din` and observing it emerge from `w_dout` 256 cycles later verifies 100% of the weight flip-flops on Day 1 of physical bring-up.

```
                  DFT SCAN CHAIN LOOPBACK (256-CYCLE PIPELINE DELAY)

clk          _|‾|_|‾|_|‾|_|‾|_|‾|_|   ...   _|‾|_|‾|_|‾|_|‾|_|‾|_|   ...   _|‾|_|‾|_
w_shift_en   ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾   ...   ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾   ...   _________  (uio_in[5])
w_din        __XXXX_D0_D1_D2_D3___   ...   ______________________   ...   _________  (uio_in[4])
                                            |<- 256 Clock Cycles ->|
w_dout       _____________________   ...   __XXXX_D0_D1_D2_D3____   ...   _________  (uio_out[2])
(Output Pad)                                ^ First shifted bit
                                              emerges exactly at Cycle 256!
```

#### Signal Probes to Add
1. `tb.clk`
2. `tb.uio_in[5]` (`w_shift_en`)
3. `tb.uio_in[4]` (`w_din`)
4. `tb.uio_out[2]` (`w_dout`)
5. `tb.user_project.weight_matrix[0]`, `tb.user_project.weight_matrix[255]`

#### What to Look For
1. **Exact 256-Cycle Latency Delay Line:**
   * Zoom into the moment `uio_in[5]` (`w_shift_en`) goes `HIGH`.
   * Place marker A at the rising clock edge of the first input bit on `uio_in[4]`.
   * Place marker B where `uio_out[2]` (`w_dout`) transitions to the same value.
   * The delta between markers measures **exactly $256 \times 20\text{ ns} = 5.12\,\mu\text{s}$**.
2. **Physical Continuity:**
   * Bits cascade sequentially across all 32 placement rows from `weight_matrix[255]` down to `weight_matrix[0]`, proving zero hold-time violations or clock skew race conditions between adjacent cells.

---

### C. `waves_saturation.vcd` — Arithmetic Clamping & Sticky Alarms

#### The Silicon "Why"
In two's-complement arithmetic, $+4095$ is `0_1111_1111_1111`. Adding `+1` causes wrap-around to `1_0000_0000_0000` (which is **$-4096$**!). In edge neural networks, an accumulator wrapping from max positive to max negative causes catastrophic misclassifications.
* Our **2-Gate Sign-Bit Saturation Unit** detects overflow using sign bit divergence (`~sum_ext[13] & sum_ext[12]`) without slow 14-bit magnitude comparators.
* It clamps the accumulator at strictly $+4095$ and asserts a sticky alarm pad `any_overflow` (`uio_out[3]`).

```
                    SATURATION & STICKY OVERFLOW ALARM BEHAVIOR

clk               _|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|
                   |                       |                       |
acc_val[c]        --[+4093]-[+4094]-[+4095]-[ CLAMPED AT +4095 ]-------------------  (NO WRAP TO -4096)
                   |                       |                       |
sat_flags[c]      ________________________|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾  (Column overflow)
                   |                       |                       |
any_overflow      ________________________|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾  (uio_out[3] Pad)
(Sticky Alarm)                             ^ Latches HIGH on overflow
                                           ^ Remains STICKY even through 32-byte readout!
```

#### Signal Probes to Add
1. `tb.uio_out[3]` (`any_overflow`)
2. `tb.user_project.sat_flags[15:0]`
3. `tb.user_project.acc_val[0][12:0]` (Signed Decimal format)

#### What to Look For
1. **The +4095 Ceiling:**
   * In this test, all 16 rows inject `+1` on all 256 cycles ($16 \times 256 = +4096$).
   * `acc_val[0]` climbs to $+4095$ and freezes strictly at $+4095$ without wrap-around.
2. **Sticky Alarm Latching:**
   * At the moment of saturation, `uio_out[3]` (`any_overflow`) asserts `HIGH`.
   * It remains latched `HIGH` (sticky) throughout the entire 32-byte readout phase, giving the host processor an instant single-pin check to confirm overflow.

---

### D. `waves_overclock_200mhz.vcd` — High-Speed Silicon Timing Margin

#### The Silicon "Why"
Tiny Tapeout projects typically run at $10\text{–}50\text{ MHz}$. Our architecture utilizes a shallow carry-save Wallace tree compressor with only 6 logic levels ($\approx 1.8\text{ ns}$ combinational delay), allowing clock frequencies well beyond nominal.
* In this test, clock period is compressed from $20.0\text{ ns}$ ($50\text{ MHz}$) to **$5.0\text{ ns}$ ($200.0\text{ MHz}$)**.

```
                    50 MHz NOMINAL vs 200 MHz OVERCLOCKING

50 MHz (T=20ns)   _|‾‾‾‾‾‾‾‾‾‾|_|‾‾‾‾‾‾‾‾‾‾|_|‾‾‾‾‾‾‾‾‾‾|_|‾‾‾‾‾‾‾‾‾‾|_|‾‾‾‾‾‾‾‾‾‾|_|
                  |<- 20 ns ->|

200 MHz (T=5ns)   _|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|‾|_|
                  |5ns|
```

#### Signal Probes to Add
1. `tb.clk`
2. `tb.uio_out[0]` (`busy`)
3. `tb.user_project.col_delta[0][4:0]`
4. `tb.user_project.acc_val[0][12:0]`

#### What to Look For
1. **Clock Period:**
   * Delta between adjacent rising edges of `tb.clk` is **$5.000\text{ ns}$**.
2. **Compute Duration:**
   * `uio_out[0]` (`busy`) duration collapses from $5.12\,\mu\text{s}$ down to **$1.28\,\mu\text{s}$**!
3. **Mathematical Equivalence:**
   * Final accumulator outputs match the 50 MHz run bit-for-bit, proving wide setup timing margins on physical standard-cell gates.

---

### E. `tb.vcd` — Full System Lifecycle & Zero-Reset Inferences

#### The Silicon "Why"
Pulsing external chip reset (`rst_n`) between inference cycles wipes weight memory, requiring a 256-cycle serial reload. The core must transition seamlessly through back-to-back inferences without global reset.

```
                      BACK-TO-BACK INFERENCES WITHOUT RESET

State         ... [FSM_DONE] -> [FSM_CLEAR] -> [FSM_COMPUTE] -> [FSM_DONE] ...
                                    |
acc_clr       ______________________|‾|___________________________________  (Internal auto-flush)
                                    |
Weight Memory ======================[ PRESERVED BIT-EXACT ]===============  (No reload needed!)
```

#### Signal Probes to Add
1. `tb.user_project.state[1:0]` (`00`=IDLE, `01`=CLEAR, `10`=COMPUTE, `11`=DONE)
2. `tb.user_project.acc_clr`
3. `tb.user_project.weight_matrix[0]`
4. `tb.uio_out[1]` (`done`)

#### What to Look For
1. **Test Case 6 (Back-to-Back Inferences at $T \approx 320\,\mu\text{s}$):**
   * `rst_n` remains `1` continuously.
   * On receiving `ctrl_strobe` with `start_req=1`, the FSM steps from `FSM_DONE` (`2'b11`) into `FSM_CLEAR` (`2'b01`) for **exactly one clock cycle**.
   * `acc_clr` pulses `HIGH` for that single cycle, clearing all 16 accumulators while preserving `weight_matrix` intact.
   * The FSM enters `FSM_COMPUTE` and executes the next inference immediately.
