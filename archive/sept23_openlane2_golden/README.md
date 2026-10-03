# Permanent Golden Archive: September 23, 2026 OpenLane 2 Sign-Off
## CIMTinyTO Architecture & Physical Sign-Off Milestone

---

### Archive Purpose & Scope
This directory contains the frozen, immutable physical tapeout artifacts and source code from the **September 23, 2026** milestone (Commit [1525ffd](https://github.com/hyleelyh/CIMTinyTO/commit/1525ffd) / [4ccc6d6](https://github.com/hyleelyh/CIMTinyTO/commit/4ccc6d6)).

It is permanently preserved in the repository for:
1. **Post-Tapeout Silicon Comparison:** Overlaying this original GDSII against the finalized shuttle tapeout GDSII in KLayout to analyze standard-cell placement topology, routing track congestion, and via density.
2. **PPA Benchmarking (Power, Performance, Area):** Benchmarking the original tri-mode 4:2 compressor tree + 14-bit comparator architecture against subsequent optimizations.
3. **Academic & Pedagogical Reference:** Documenting the evolution of open-source EDA tooling and microarchitectural hardening across the Tiny Tapeout shuttle generations (tt08 vs ttsky26d).

---

### Archived Assets Inventory

```
archive/sept23_openlane2_golden/
├── README.md               <- This metadata and provenance document
├── gds/
│   ├── tt_um_scim_core.gds <- Finalized 16.1 MB binary GDSII layout (0 DRC, 0 LVS)
│   ├── tt_um_scim_core.lef <- Macro abstract LEF (pin definitions & blockage bounds)
│   ├── tt_um_scim_core.v   <- Post-synthesis / post-route gate-level netlist (67,614 lines)
│   ├── metrics.csv         <- Complete OpenLane 2 sign-off metrics report
│   └── sky130.lyp          <- KLayout layer properties for SkyWater 130nm
├── src/
│   ├── tt_um_scim_core.v   <- Original top-level Verilog core
│   ├── scim_wallace_tree.v <- Original 16-to-5 Wallace reduction tree
│   ├── scim_compressor_42.v<- Original 4:2 compressor submodule
│   ├── scim_accumulator.v <- Original 13-bit accumulator with 14-bit comparators
│   ├── scim_pe.v           <- Original Tri-Mode PE (AND, XNOR, MUX)
│   ├── scim_weight_mem.v   <- Original 256-bit serial weight memory
│   ├── scim_sng_bank.v     <- Original 16-channel stochastic number generator bank
│   └── lfsr8_galois.v      <- Original 8-bit Galois LFSR with primitive polynomial
└── config/
    ├── config.json         <- Original OpenLane 2 configuration file
    └── scim_core.sdc       <- Original Synopsys Design Constraints (50 MHz)
```

---

### Key Sign-Off Metrics (Sept 23, 2026)

| Parameter | Value | Notes |
| :--- | :--- | :--- |
| **Git Commit Reference** | 1525ffd / 4ccc6d6 | Frozen in Git Tag v-sept23-openlane2-signoff |
| **EDA Toolchain** | OpenLane 2 (tt08 container) | OpenROAD physical engine |
| **Target PDK** | SkyWater 130nm (sky130_fd_sc_hd) | Nominal 1.8V core |
| **Macro Footprint** | Tiny Tapeout 2x2 Tile (~335.52 µm x 225.76 µm) | ~73,500 µm² gross core area |
| **Standard Cell Area** | 62,882.35 µm² | ~4,200 standard cells |
| **Placement Density** | 85.5% | Squeezed within 2x2 tile bounds |
| **Target Clock** | 50.0 MHz (T = 20.000 ns) | Positive setup slack > +9.87 ns |
| **Clock Uncertainty** | 500 ps setup, 200 ps hold | Robust across PVT corners |
| **Sign-Off Status** | 0 DRC Errors, 0 LVS Errors | 100% verified in Magic, Netgen, KLayout |

---

### How to Compare Against the New Shuttle GDS in KLayout

To perform a visual and geometrical comparison between this golden layout and the new shuttle layout:

1. Launch KLayout in overlay mode:
   ```bash
   klayout -s archive/sept23_openlane2_golden/gds/tt_um_scim_core.gds \
           -s gds/tt_um_scim_core.gds \
           -l archive/sept23_openlane2_golden/gds/sky130.lyp
   ```
2. In KLayout, toggle between the two layouts to inspect:
   * **Cell density:** The visible increase in whitespace (from 85.5% down to ~64.5%).
   * **Decap distribution:** The large arrays of sky130_fd_sc_hd__decap_* filling the whitespace rows.
   * **Metal routing tracks:** The dramatic reduction in met1 congestion and the clean Manhattan tracks on met2/met3.
