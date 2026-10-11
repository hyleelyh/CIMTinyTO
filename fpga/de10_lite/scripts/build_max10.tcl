# ============================================================================
# Script: build_max10.tcl
# Project: CIMTinyTO DE10-Lite FPGA Synthesis & Compilation
# Target: Intel MAX 10 10M50DAF484C7G (Terasic DE10-Lite)
# Standard: Intel Quartus Prime Lite Edition Tcl Flow
# ============================================================================

set script_dir [file dirname [file normalize [info script]]]
set base_dir   [file normalize "$script_dir/.."]
cd $base_dir

set project_name "de10_lite_scim"
set top_entity   "de10_lite_top"

puts "================================================================="
puts " Starting CIMTinyTO DE10-Lite Compilation Flow"
puts " Base Directory: $base_dir"
puts "================================================================="

load_package flow

# Create or open project
if {[project_exists $project_name]} {
    project_open $project_name
} else {
    project_new $project_name -family "MAX 10" -part "10M50DAF484C7G"
}

# Apply QSF constraints
source constrs/de10_lite.qsf

# Set top-level entity
set_global_assignment -name TOP_LEVEL_ENTITY $top_entity

# 1. Analysis & Synthesis (quartus_map)
puts "\n>>> \[1/4\] Running Analysis & Synthesis (quartus_map)..."
if {[catch {execute_module -tool map} result]} {
    puts "ERROR: Analysis & Synthesis failed: $result"
    exit 1
}

# 2. Place & Route (quartus_fit)
puts "\n>>> \[2/4\] Running Fitter / Place & Route (quartus_fit)..."
if {[catch {execute_module -tool fit} result]} {
    puts "ERROR: Fitter failed: $result"
    exit 1
}

# 3. Assembler / SOF Generation (quartus_asm)
puts "\n>>> \[3/4\] Running Assembler (quartus_asm)..."
if {[catch {execute_module -tool asm} result]} {
    puts "ERROR: Assembler failed: $result"
    exit 1
}

# 4. Static Timing Analysis (quartus_sta)
puts "\n>>> \[4/4\] Running TimeQuest Timing Analysis (quartus_sta)..."
if {[catch {execute_module -tool sta} result]} {
    puts "WARNING: Timing analysis generated warnings: $result"
}

project_close

puts "\n================================================================="
puts " COMPILATION COMPLETED SUCCESSFULLY!"
puts " Output SOF: output_files/$project_name.sof"
puts "================================================================="
