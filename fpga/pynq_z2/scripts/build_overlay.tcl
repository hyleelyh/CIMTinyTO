# ============================================================================
# Script: build_overlay.tcl
# Project: CIMTinyTO PYNQ-Z2 (Zynq-7020) Pre-Silicon Emulation (Pillar 6)
# Standard: AMD Xilinx Vivado Batch Tcl Flow
# Output: scim_pynq.bit and scim_pynq.hwh ready for PYNQ Python Overlay
# ============================================================================

set script_dir  [file dirname [file normalize [info script]]]
set pynq_dir    [file normalize "$script_dir/.."]
set proj_root   [file normalize "$pynq_dir/../.."]
set build_dir   "$pynq_dir/build"
set overlay_dir "$pynq_dir/overlay"

file mkdir $overlay_dir
file mkdir $build_dir

set project_name "scim_pynq"
set top_entity   "scim_bd_wrapper"
set target_part  "xc7z020clg400-1"

puts "================================================================="
puts " Starting CIMTinyTO PYNQ-Z2 Overlay Build Flow"
puts " Target Part:      $target_part"
puts " Project Root:     $proj_root"
puts " Overlay Output:   $overlay_dir"
puts "================================================================="

# 1. Create Project
create_project -force $project_name $build_dir -part $target_part

# 2. Add Source RTL Files
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
puts "\n>>> [1/5] Constructing Block Design (scim_bd)..."
create_bd_design "scim_bd"

set scim_cell [create_bd_cell -type module -reference tt_scim_axi_wrapper scim_core_0]
set ps7       [create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:* ps7]

# Configure PS7: 50 MHz FCLK0, M_AXI_GP0 enabled
set_property -dict [list \
    CONFIG.PCW_USE_M_AXI_GP0 {1} \
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {50.0} \
] $ps7

# Connect AXI4-Lite slave to PS7 master
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master "/ps7/M_AXI_GP0" Clk "Auto"} [get_bd_intf_pins scim_core_0/s_axi]

# Connect core PLL clock input to PS7 FCLK_CLK0
connect_bd_net [get_bd_pins scim_core_0/ext_pll_clk] [get_bd_pins ps7/FCLK_CLK0]

# Break out external PMOD snooping headers
make_bd_pins_external [get_bd_pins scim_core_0/pmod_a] -name "pmod_a"
make_bd_pins_external [get_bd_pins scim_core_0/pmod_b] -name "pmod_b"

assign_bd_address
validate_bd_design
save_bd_design

# 5. Generate Block Design Targets & Top Wrapper
puts "\n>>> [2/5] Generating Block Design Targets & Top Wrapper..."
set_property synth_checkpoint_mode None [get_files scim_bd.bd]
generate_target all [get_files scim_bd.bd] -force

set wrapper_path [make_wrapper -files [get_files scim_bd.bd] -top]
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
report_utilization -file "$overlay_dir/utilization.rpt"
report_timing_summary -file "$overlay_dir/timing_summary.rpt"

# 8. Export Bitstream & Hardware Handoff (.hwh)
puts "\n>>> [5/5] Exporting Deliverables to $overlay_dir..."
set bit_file [glob -nocomplain "$build_dir/$project_name.runs/impl_1/$top_entity.bit"]
set hwh_file [glob -nocomplain "$build_dir/$project_name.gen/sources_1/bd/scim_bd/hw_handoff/scim_bd.hwh"]

if {[file exists $bit_file]} {
    file copy -force $bit_file "$overlay_dir/scim_pynq.bit"
    puts " Exported Bitstream: $overlay_dir/scim_pynq.bit"
} else {
    puts "ERROR: Bitstream file not found at $bit_file"
    exit 1
}

if {[file exists $hwh_file]} {
    file copy -force $hwh_file "$overlay_dir/scim_pynq.hwh"
    puts " Exported HWH:       $overlay_dir/scim_pynq.hwh"
} else {
    puts "ERROR: Hardware handoff file not found at $hwh_file"
    exit 1
}

close_project

puts "\n================================================================="
puts " PYNQ-Z2 OVERLAY BUILD COMPLETED SUCCESSFULLY!"
puts " Output Bitstream: $overlay_dir/scim_pynq.bit"
puts " Output Handoff:   $overlay_dir/scim_pynq.hwh"
puts "================================================================="
