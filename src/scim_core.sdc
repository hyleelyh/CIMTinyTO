# ==============================================================================
# Synopsys Design Constraints (SDC): CIMTinyTO
# Target Shuttle: Tiny Tapeout SKY 26d (SkyWater 130nm)
# Clock Target: 50 MHz (Period: 20.0 ns)
# ==============================================================================

# Master Clock Definition (50 MHz)
create_clock -name clk -period 20.000 [get_ports clk]

# Clock Uncertainty (Jitter + Skew Margin)
# 500 ps setup uncertainty models PLL jitter and temperature drift
# 200 ps hold uncertainty guarantees silicon margin against race conditions
set_clock_uncertainty -setup 0.500 [get_clocks clk]
set_clock_uncertainty -hold  0.200 [get_clocks clk]

# Clock Transition / Slew Limit (250 ps)
set_clock_transition 0.250 [get_clocks clk]

# I/O Constraints
# In Tiny Tapeout, macro pins interface to on-chip multiplexer (~1.5 ns delay budget)
set_input_delay  -clock clk -max 2.000 [get_ports {ui_in[*] uio_in[*]}]
set_input_delay  -clock clk -min 0.500 [get_ports {ui_in[*] uio_in[*]}]

set_output_delay -clock clk -max 2.000 [all_outputs]
set_output_delay -clock clk -min 0.500 [all_outputs]

# External Load Model
# Tiny Tapeout internal mux input load is ~33.4 fF (0.0334 pF)
set_load 0.0334 [all_outputs]

# External Driving Cell
# sky130_fd_sc_hd__inv_2 models the drive strength of the Tiny Tapeout pad frame
set_driving_cell -lib_cell sky130_fd_sc_hd__inv_2 -pin Y [get_ports {ui_in[*] uio_in[*]}]

# False Path Declaration for Asynchronous Reset Pad
# External rst_n is asynchronously asserted and captured by internal 2-stage synchronizer (rst_sync_0)
set_false_path -from [get_ports rst_n]

# False Path Declaration for Static Enable Pad
set_false_path -from [get_ports ena]
