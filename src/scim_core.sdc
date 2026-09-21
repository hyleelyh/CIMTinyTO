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
# External PCB trace delay budget: 4.0 ns max (20% of period), 1.0 ns min
set_input_delay  -clock clk -max 4.000 [remove_from_collection [all_inputs] [get_ports clk]]
set_input_delay  -clock clk -min 1.000 [remove_from_collection [all_inputs] [get_ports clk]]

set_output_delay -clock clk -max 4.000 [all_outputs]
set_output_delay -clock clk -min 1.000 [all_outputs]

# External Load Model
# 25 pF models Tiny Tapeout carrier board pad capacitance + PCB trace load
set_load 25.000 [all_outputs]

# External Driving Cell
# sky130_fd_sc_hd__inv_2 models the drive strength of external I/O pad buffers
set_driving_cell -lib_cell sky130_fd_sc_hd__inv_2 [remove_from_collection [all_inputs] [get_ports clk]]

# False Path Declaration for Asynchronous Reset Pad
# External rst_n is asynchronously asserted and captured by internal 2-stage synchronizer (rst_sync_0)
set_false_path -from [get_ports rst_n]

# False Path Declaration for Static Enable Pad
set_false_path -from [get_ports ena]
