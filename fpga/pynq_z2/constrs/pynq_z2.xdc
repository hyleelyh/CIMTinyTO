# ============================================================================
# Constraints: pynq_z2.xdc
# Project: CIMTinyTO PYNQ-Z2 (Zynq-7020) Pre-Silicon Emulation (Pillar 6)
# Target Device: AMD Xilinx XC7Z020CLG400-1
# ============================================================================
# Pedagogical & Silicon Rationale:
#
# 1. PMOD A (Header JA):
#    Routes uo_out[7:0] (live accumulator readback byte) to external pins.
#    Permits bench logic analyzers (DSLogic Plus, Saleae) to observe accumulator
#    data transitions and multiplexer settling times in real time.
#
# 2. PMOD B (Header JB):
#    Routes 8 core control and status signals:
#    - JB1 (Y14): core_clk (50 MHz free-running or software stepped)
#    - JB2 (W14): core_rst_n (synchronous active-low reset)
#    - JB3 (P18): busy (compute phase in progress)
#    - JB4 (P19): done (256-cycle accumulation complete)
#    - JB5 (V16): w_dout (serial weight DFT loopback test)
#    - JB6 (W16): any_overflow (sticky saturation alarm)
#    - JB7 (V12): ctrl_strobe (command write strobe)
#    - JB8 (W13): wr_act (activation register write strobe)
#
# 3. Electrical & Timing Safety:
#    - All pins operate at safe +3.3V LVCMOS (LVCMOS33).
#    - Snooping pins are declared as false paths to decouple debug routing
#      from critical internal 50 MHz AXI4-Lite timing closure.
# ============================================================================

# ----------------------------------------------------------------------------
# PMOD A (Header JA) - uo_out[7:0] Live Accumulator Byte Snooping
# ----------------------------------------------------------------------------
set_property -dict { PACKAGE_PIN Y18  IOSTANDARD LVCMOS33 } [get_ports { pmod_a[0] }]; # JA1
set_property -dict { PACKAGE_PIN Y19  IOSTANDARD LVCMOS33 } [get_ports { pmod_a[1] }]; # JA2
set_property -dict { PACKAGE_PIN Y16  IOSTANDARD LVCMOS33 } [get_ports { pmod_a[2] }]; # JA3
set_property -dict { PACKAGE_PIN Y17  IOSTANDARD LVCMOS33 } [get_ports { pmod_a[3] }]; # JA4
set_property -dict { PACKAGE_PIN U18  IOSTANDARD LVCMOS33 } [get_ports { pmod_a[4] }]; # JA7
set_property -dict { PACKAGE_PIN U19  IOSTANDARD LVCMOS33 } [get_ports { pmod_a[5] }]; # JA8
set_property -dict { PACKAGE_PIN W18  IOSTANDARD LVCMOS33 } [get_ports { pmod_a[6] }]; # JA9
set_property -dict { PACKAGE_PIN W19  IOSTANDARD LVCMOS33 } [get_ports { pmod_a[7] }]; # JA10

# ----------------------------------------------------------------------------
# PMOD B (Header JB) - Core Control & Status Snooping
# ----------------------------------------------------------------------------
set_property -dict { PACKAGE_PIN Y14  IOSTANDARD LVCMOS33 } [get_ports { pmod_b[0] }]; # JB1  - core_clk
set_property -dict { PACKAGE_PIN W14  IOSTANDARD LVCMOS33 } [get_ports { pmod_b[1] }]; # JB2  - core_rst_n
set_property -dict { PACKAGE_PIN P18  IOSTANDARD LVCMOS33 } [get_ports { pmod_b[2] }]; # JB3  - busy
set_property -dict { PACKAGE_PIN P19  IOSTANDARD LVCMOS33 } [get_ports { pmod_b[3] }]; # JB4  - done
set_property -dict { PACKAGE_PIN V16  IOSTANDARD LVCMOS33 } [get_ports { pmod_b[4] }]; # JB7  - w_dout
set_property -dict { PACKAGE_PIN W16  IOSTANDARD LVCMOS33 } [get_ports { pmod_b[5] }]; # JB8  - any_overflow
set_property -dict { PACKAGE_PIN V12  IOSTANDARD LVCMOS33 } [get_ports { pmod_b[6] }]; # JB9  - ctrl_strobe
set_property -dict { PACKAGE_PIN W13  IOSTANDARD LVCMOS33 } [get_ports { pmod_b[7] }]; # JB10 - wr_act

# ----------------------------------------------------------------------------
# Timing Exceptions: Snooping Outputs are False Paths
# ----------------------------------------------------------------------------
set_false_path -to [get_ports {pmod_a[*]}]
set_false_path -to [get_ports {pmod_b[*]}]
