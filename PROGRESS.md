# Project Progress: CIMTinyTO

## Last Execution Run: 2026-09-21 21:05
### [Built & Verified]
- `docs/physical_sizing_and_tradeoff_analysis.md`: Comprehensive architectural note detailing block-by-block standard-cell area audit, $16\times 16$ vs. $8\times 8$ non-linear scaling laws, DRAM-like banking analysis, and end-to-end Micro-ResNet inference throughput.
- Previous baseline verified: Verilator lint clean (0 warnings), Cocotb 3/3 test suites bit-exact pass (100%), parser self-tests clean.

### [Architecture Decisions & Physical Sizing Deep-Dive]
- **Standard-Cell Expansion Breakdown:**
  - Forensic analysis of OpenROAD Global Placement overflow (`63,548 µm²` vs `34,255 µm²` core capacity on $1\times 2$ tile):
    1. **Accumulators ($\approx 19,200\,\mu\text{m}^2$):** 16 parallel 14-bit adders, 32 signed magnitude comparators (`sum > +4095`, `sum < -4096`), and 13-bit saturation clamping MUXes.
    2. **Wallace Trees ($\approx 15,000\,\mu\text{m}^2$):** 17 trees containing 153 discrete 4:2 compressor slices decomposed into discrete XOR2/NAND/inverter standard cells.
    3. **Weight Memory DFFs ($\approx 4,800\,\mu\text{m}^2$):** Standard-cell D-flip-flops are 24–28 transistors ($\approx 15\,\mu\text{m}^2$), $10\times$ larger than custom 6T SRAM bitcells ($\approx 1.5\,\mu\text{m}^2$).
    4. **Physical Overhead ($\approx 12,500\,\mu\text{m}^2$):** 618 DRC-mandated well taps (`tapvpwrvgnd_1` every $14\,\mu\text{m}$) plus CTS and HFN buffers.
- **Asymmetric Scaling Laws ($16\times 16 \rightarrow 8\times 8$):**
  - Standard-cell CIM consists of 2D matrix components ($O(N^2)$, drops by $75\%$), 1D row/column peripherals ($O(N)$, drops by only $50\%$), and 0D infrastructure ($O(1)$, constant).
  - Downscaled $8\times 8$ standard-cell area is $\approx 20,800\,\mu\text{m}^2$ ($3.05\times$ reduction, NOT $4\times$).
  - **Tile Sizing Consequence:** $8\times 8$ cannot fit in a $1\times 1$ tile ($160\%$ utilization), but achieves ideal density ($\approx 60.7\%$) in a $1\times 2$ tile.
- **DRAM Banking / Time-Multiplexing Analysis (Option 3):**
  - Partitioning columns into Bank A/B and sharing 8 Wallace trees/adders reduces area to $\approx 49,500\,\mu\text{m}^2$.
  - On a $1\times 2$ tile, density remains $\approx 144.5\%$, still failing placement `[GPL-0301]`. Standard-cell flip-flops dominate area.
- **Inference Speed & Workload Feasibility:**
  - Full ResNet-18 ($224 \times 224$ ImageNet, $1.8\text{ GMACs}$) is bandwidth-constrained by Tiny Tapeout's 8-bit I/O bus ($\approx 45\text{ s}$ on $16\times 16$, $\approx 3\text{ min}$ on $8\times 8$).
  - Micro-ResNet ($3\text{ MMACs}$, binary weights):
    - **$16\times 16$ Core ($2\times 2$ Tile):** $\approx 80\text{ ms}$ total latency $\implies$ **$\approx 12.5\text{ FPS}$ (Real-Time Video Rate)**.
    - **$8\times 8$ Core ($1\times 2$ Tile):** $\approx 370\text{ ms}$ total latency ($4$ tiling passes) $\implies$ **$\approx 2.7\text{ FPS}$ (Interactive Edge Rate)**.

### [Current Pipeline State]
- **Pillar 1 (Mathematical Golden Model): 100% COMPLETE & FROZEN.**
- **Pillar 2 (Microarchitecture & Verification): 100% COMPLETE & FROZEN.**
- **Pillar 3 (Physical ASIC Flow): IN PROGRESS / PENDING SIZING DECISION.**
  - Physical configuration, SDC constraints, and GitHub Actions CI pipelines complete.
  - Sizing decision paused for user reflection: Option 1 ($16\times 16$ on $2\times 2$ tile, $12.5\text{ FPS}$) vs. Option 2 ($8\times 8$ on $1\times 2$ tile, $2.7\text{ FPS}$).

### [Next Steps]
1. User to evaluate performance vs. shuttle budget goals.
2. If Option 1 ($16\times 16$ on $2\times 2$ tile): Update `info.yaml` to `tiles: "2x2"` and re-trigger OpenLane 2 cloud hardening on GitHub Actions.
3. If Option 2 ($8\times 8$ on $1\times 2$ tile): Parameterize RTL submodules down to $8\times 8$, update Cocotb testbenches, and re-trigger hardening on $1\times 2$.
4. Achieve physical GDS placement and routing sign-off before closing Pillar 3.
