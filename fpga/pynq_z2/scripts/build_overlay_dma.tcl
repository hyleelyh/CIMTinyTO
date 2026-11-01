# ============================================================================
# Script: build_overlay_dma.tcl
# Project: CIMTinyTO PYNQ-Z2 (Zynq-7020) Pre-Silicon Emulation (Pillar 6.1 - Tier 3)
# Standard: AMD Xilinx Vivado Batch Tcl Flow
# Output: scim_pynq_dma.bit and scim_pynq_dma.hwh ready for PYNQ Python Overlay
# ============================================================================
# Pedagogical & Silicon Rationale:
#
# 1. Autonomous Hardware Line-Rate Streaming:
#    - Instantiates Xilinx AXI DMA in Simple Register Direct Mode (no SG descriptors).
#    - Connects DMA MM2S and S2MM channels directly to scim_axis_stream_feeder.
#    - Feeds 256-bit weights and activation bursts to frozen tt_um_scim_core.
#
# 2. Multi-Tier Coexistence (Zero-Disruption Architecture):
#    - Also instantiates tt_scim_axi_wrapper (scim_core_0) on M_AXI_GP0 (0x43C00000).
#    - Enables Tier 1 (Pure Python MMIO), Tier 2 (Compiled C MMIO), and Tier 3 (DMA)
#      to run simultaneously on the exact same physical bitstream!
#
# 3. High-Performance AXI Memory Hierarchy:
#    - Control (AXI-Lite): M_AXI_GP0 @ 50 MHz for DMA and MMIO configuration registers.
#    - Data (AXI-HP): S_AXI_HP0 @ 50 MHz for high-throughput DMA transfers to/from DDR.
# ============================================================================

set script_dir  [file dirname [file normalize [info script]]]
set pynq_dir    [file normalize "$script_dir/.."]
set proj_root   [file normalize "$pynq_dir/../.."]
set build_dir   "$pynq_dir/build_dma"
set overlay_dir "$pynq_dir/overlay"

file mkdir $overlay_dir
file mkdir $build_dir

set project_name "scim_pynq_dma"
set top_entity   "scim_dma_bd_wrapper"
set target_part  "xc7z020clg400-1"

puts "================================================================="
puts " Starting CIMTinyTO PYNQ-Z2 DMA Overlay Build Flow (Pillar 6.1 - Tier 3)"
puts " Target Part:      $target_part"
puts " Project Root:     $proj_root"
puts " Build Directory:  $build_dir"
puts " Overlay Output:   $overlay_dir"
puts "================================================================="

# 1. Create Project
create_project -force $project_name $build_dir -part $target_part

# 2. Add Source RTL Files
add_files "$pynq_dir/rtl/scim_axis_stream_feeder.v"
add_files "$pynq_dir/rtl/tt_scim_axi_wrapper.v"
add_files "$proj_root/src/tt_um_scim_core.v"
add_files "$proj_root/src/lfsr8_galois.v"
add_files "$proj_root/src/scim_sng_bank.v"
add_files "$proj_root/src/scim_pe.v"
add_files "$proj_root/src/scim_compressor_42.v"
add_files "$proj_root/src/scim_wallace_tree.v"
add_files "$proj_root/src/scim_accumulator.v"
add_files "$proj_root/src/scim_weight_mem.v"
update_compile_order -fileset sources_1

# 3. Add Constraints
add_files -fileset constrs_1 "$pynq_dir/constrs/pynq_z2.xdc"

# 4. Construct Block Design
puts "\n>>> [1/5] Constructing Block Design (scim_dma_bd)..."
create_bd_design "scim_dma_bd"

# 4.1 Instantiate Processing System 7
set ps7 [create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:* ps7]
set_property -dict [list \
    CONFIG.PCW_USE_M_AXI_GP0 {1} \
    CONFIG.PCW_USE_S_AXI_HP0 {1} \
    CONFIG.PCW_USE_S_AXI_HP1 {1} \
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {50.0} \
] $ps7

# 4.2 Instantiate AXI-Lite MMIO Core (scim_core_0 for Tier 1 & 2)
set scim_core [create_bd_cell -type module -reference tt_scim_axi_wrapper scim_core_0]

# 4.3 Instantiate AXI-Stream Hardware Feeder (scim_feeder_0 for Tier 3 DMA)
set scim_feeder [create_bd_cell -type module -reference scim_axis_stream_feeder scim_feeder_0]

# 4.4 Instantiate AXI DMA in Simple Direct Register Mode
set axi_dma [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_dma:* axi_dma_0]
set_property -dict [list \
    CONFIG.c_include_sg {0} \
    CONFIG.c_sg_include_stscntrl_strm {0} \
    CONFIG.c_include_mm2s {1} \
    CONFIG.c_m_axis_mm2s_tdata_width {32} \
    CONFIG.c_mm2s_burst_size {16} \
    CONFIG.c_include_s2mm {1} \
    CONFIG.c_s_axis_s2mm_tdata_width {32} \
    CONFIG.c_s2mm_burst_size {16} \
] $axi_dma

# 4.5 Connect AXI4-Stream Interfaces
connect_bd_intf_net [get_bd_intf_pins axi_dma_0/M_AXIS_MM2S] [get_bd_intf_pins scim_feeder_0/s_axis]
connect_bd_intf_net [get_bd_intf_pins scim_feeder_0/m_axis] [get_bd_intf_pins axi_dma_0/S_AXIS_S2MM]

# 4.6 Connect Clocks
connect_bd_net [get_bd_pins ps7/FCLK_CLK0] [get_bd_pins scim_feeder_0/aclk]
connect_bd_net [get_bd_pins ps7/FCLK_CLK0] [get_bd_pins scim_core_0/ext_pll_clk]
connect_bd_net [get_bd_pins ps7/FCLK_CLK0] [get_bd_pins ps7/S_AXI_HP0_ACLK]
connect_bd_net [get_bd_pins ps7/FCLK_CLK0] [get_bd_pins ps7/S_AXI_HP1_ACLK]

# 4.7 Connect AXI Bus Automation (GP0 Master to MMIO + DMA Control; HP0 Slave from DMA Read; HP1 Slave from DMA Write)
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master "/ps7/M_AXI_GP0" Clk "Auto"} [get_bd_intf_pins scim_core_0/s_axi]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master "/ps7/M_AXI_GP0" Clk "Auto"} [get_bd_intf_pins axi_dma_0/S_AXI_LITE]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master "/axi_dma_0/M_AXI_MM2S" Clk "Auto"} [get_bd_intf_pins ps7/S_AXI_HP0]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master "/axi_dma_0/M_AXI_S2MM" Clk "Auto"} [get_bd_intf_pins ps7/S_AXI_HP1]

# Obtain the peripheral reset line created by automation and connect to feeder
set rst_pins [get_bd_pins -hierarchical peripheral_aresetn]
if {[llength $rst_pins] > 0} {
    connect_bd_net [lindex $rst_pins 0] [get_bd_pins scim_feeder_0/aresetn]
}

# 4.8 Break out External PMOD Snooping Headers
make_bd_pins_external [get_bd_pins scim_feeder_0/pmod_a] -name "pmod_a"
make_bd_pins_external [get_bd_pins scim_feeder_0/pmod_b] -name "pmod_b"

assign_bd_address
validate_bd_design
save_bd_design

# 5. Generate Block Design Targets & Top Wrapper
puts "\n>>> [2/5] Generating Block Design Targets & Top Wrapper..."
set_property synth_checkpoint_mode None [get_files scim_dma_bd.bd]
generate_target all [get_files scim_dma_bd.bd] -force

set wrapper_path [make_wrapper -files [get_files scim_dma_bd.bd] -top]
add_files -norecurse $wrapper_path
set_property top $top_entity [current_fileset]
update_compile_order -fileset sources_1

# 6. Launch Synthesis and Implementation Flow
puts "\n>>> [3/5] Launching Synthesis, Placement & Routing (impl_1)..."
launch_runs impl_1 -to_step write_bitstream -jobs 8
wait_on_run impl_1

set run_status [get_property STATUS [get_runs impl_1]]
puts "Implementation Run Status: $run_status"

if {[get_property PROGRESS [get_runs impl_1]] != "100%"} {
    puts "ERROR: Implementation flow did not complete successfully!"
    exit 1
}

# 7. Generate Timing & Utilization Reports
puts "\n>>> [4/5] Extracting Physical Sign-Off Reports..."
open_run impl_1
report_utilization -file "$overlay_dir/utilization_dma.rpt"
report_timing_summary -file "$overlay_dir/timing_summary_dma.rpt"

# 8. Export Bitstream & Hardware Handoff (.hwh)
puts "\n>>> [5/5] Exporting Deliverables to $overlay_dir..."
set bit_file [glob -nocomplain "$build_dir/$project_name.runs/impl_1/$top_entity.bit"]
set hwh_file [glob -nocomplain "$build_dir/$project_name.gen/sources_1/bd/scim_dma_bd/hw_handoff/scim_dma_bd.hwh"]

if {[file exists $bit_file]} {
    file copy -force $bit_file "$overlay_dir/scim_pynq_dma.bit"
    puts " Exported Bitstream: $overlay_dir/scim_pynq_dma.bit"
} else {
    puts "ERROR: Bitstream file not found at $bit_file"
    exit 1
}

if {[file exists $hwh_file]} {
    file copy -force $hwh_file "$overlay_dir/scim_pynq_dma.hwh"
    puts " Exported HWH:       $overlay_dir/scim_pynq_dma.hwh"
} else {
    puts "ERROR: Hardware handoff file not found at $hwh_file"
    exit 1
}

close_project

puts "\n================================================================="
puts " PYNQ-Z2 DMA OVERLAY BUILD COMPLETED SUCCESSFULLY!"
puts " Output Bitstream: $overlay_dir/scim_pynq_dma.bit"
puts " Output Handoff:   $overlay_dir/scim_pynq_dma.hwh"
puts "================================================================="
