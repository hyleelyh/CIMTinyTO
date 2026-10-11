# ============================================================================
# Synopsys Design Constraints (SDC) for Terasic DE10-Lite
# Project: CIMTinyTO Tactile Evaluation Console
# Target: Intel MAX 10 10M50DAF484C7G
# ============================================================================

# 1. Primary 50 MHz Master Clock (20.0 ns period)
create_clock -name MAX10_CLK1_50 -period 20.000 [get_ports {MAX10_CLK1_50}]

# 2. Derive Clock Uncertainty
derive_clock_uncertainty

# 3. Asynchronous Inputs (Pushbuttons & Slide Switches)
# Mechanical human inputs are asynchronous and debounced/synchronized via 2-stage synchronizers
set_false_path -from [get_ports {KEY[*]}]
set_false_path -from [get_ports {SW[*]}]

# 4. Asynchronous Outputs (LEDs & 7-Segment Displays)
# Human visual display outputs do not require high-speed setup/hold timing closure
set_false_path -to [get_ports {LEDR[*]}]
set_false_path -to [get_ports {HEX0[*]}]
set_false_path -to [get_ports {HEX1[*]}]
set_false_path -to [get_ports {HEX2[*]}]
set_false_path -to [get_ports {HEX3[*]}]
set_false_path -to [get_ports {HEX4[*]}]
set_false_path -to [get_ports {HEX5[*]}]
