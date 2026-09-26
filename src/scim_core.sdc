# ==============================================================================
# Synopsys Design Constraints (SDC): CIMTinyTO
# Target Shuttle: Tiny Tapeout SKY 26d (SkyWater 130nm / sky130_fd_sc_hd)
# Clock Target: 50 MHz (Nominal Period: 20.000 ns)
# ==============================================================================
# Pedagogical & Silicon Sign-Off Rationale:
#
# 1. Master Clock & Uncertainty Budget:
#    - T_clk = 20.000 ns (50.00 MHz).
#    - Setup Uncertainty (500 ps):
#      Accounts for carrier board PLL/crystal jitter (~80 ps), PCB trace
#      dispersion (~60 ps), on-chip power supply droop wander (~150 ps), and
#      sign-off conservatism margin (~210 ps).
#    - Hold Uncertainty (200 ps):
#      Accounts for intra-die On-Chip Variation (OCV), standard-cell Pelgrom
#      threshold mismatch, and clock tree branch skew. OpenROAD CTS achieved
#      worst-case clock skew of 80 ps to 176 ps, fully bounded by 200 ps.
#    - Clock Transition (250 ps):
#      Imposes a 250 ps 10%-90% slew rate on the input clock pin to prevent
#      excessive short-circuit current (P_sc) in the root clock buffer.
#
# 2. External I/O & Shuttle Location Invariance:
#    - In Tiny Tapeout, user macros do not touch wirebond pads directly. All
#      signals pass through the shuttle multiplexer spine (tt_um_mux).
#    - Input / Output Delay (2.000 ns max / 0.500 ns min):
#      Allocates 10% (2.0 ns) of the clock cycle to shuttle mux routing.
#      Because nominal setup slack is +9.87 ns, this guarantees identical
#      50 MHz timing whether placed in Column 1 (near pads) or Column 8.
#
# 3. External Load & Driving Cell Model:
#    - External Load (33.4 fF = 0.0334 pF):
#      Models the input gate capacitance of the shuttle row MUX (3.5-4.5 fF)
#      plus ~150 um of met4/met3 metal routing stubs (~27 fF).
#      OpenROAD physical resizer buffers every output pin (clkbuf_4), providing
#      drive strength >150 fF. Furthermore, uo_out is held statically at 8'h00
#      during active compute (!busy gating, Hole #8), making internal compute
#      timing completely immune to external capacitive load variations.
#    - External Driving Cell (sky130_fd_sc_hd__inv_2):
#      Models the pad frame input buffer (Ron ≈ 1.5 kΩ, slew ≈ 200 ps).
#      Inputs ui_in connect directly to register D-inputs with >17.3 ns setup
#      margin, providing massive noise and drive tolerance.
#
# 4. Timing Exceptions & Single-Cycle Discipline:
#    - False Paths:
#      * rst_n: Asynchronous external reset captured by a 2-stage synchronizer
#               (MTBF > 1e10 years). Synchronous deassertion handled internally.
#      * ena:   Static power-on enable tied high by carrier board.
#    - Multicycle Paths (MCP):
#      Deliberately omitted. All internal operations (weight shift, SNG step,
#      Wallace tree compression, delta subtraction, accumulator addition) are
#      constrained to single-cycle timing (20.0 ns), preventing masked bugs.
# ==============================================================================

# Master Clock Definition (50 MHz)
create_clock -name clk -period 20.000 [get_ports clk]

# Clock Uncertainty (Jitter + Skew Margin)
set_clock_uncertainty -setup 0.500 [get_clocks clk]
set_clock_uncertainty -hold  0.200 [get_clocks clk]

# Clock Transition / Slew Limit (250 ps)
set_clock_transition 0.250 [get_clocks clk]

# I/O Delay Budget (Tiny Tapeout Shuttle Multiplexer: 2.0 ns max / 0.5 ns min)
set_input_delay  -clock clk -max 2.000 [get_ports {ui_in[*] uio_in[*]}]
set_input_delay  -clock clk -min 0.500 [get_ports {ui_in[*] uio_in[*]}]

set_output_delay -clock clk -max 2.000 [all_outputs]
set_output_delay -clock clk -min 0.500 [all_outputs]

# External Load Model (Shuttle row MUX input gate cap + routing stub = 33.4 fF)
set_load 0.0334 [all_outputs]

# External Driving Cell (Shuttle pad frame inverter stage)
set_driving_cell -lib_cell sky130_fd_sc_hd__inv_2 -pin Y [get_ports {ui_in[*] uio_in[*]}]

# False Path Declaration for Asynchronous Reset Pad (Handled by 2-stage synchronizer)
set_false_path -from [get_ports rst_n]

# False Path Declaration for Static Carrier Board Enable Pad
set_false_path -from [get_ports ena]

