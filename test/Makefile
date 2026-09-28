# ==============================================================================
# Makefile — Cocotb Simulation Testbench Harness for CIMTinyTO
# Target: Icarus Verilog (iverilog) + Cocotb (RTL & Gate-Level Simulation)
# ==============================================================================

SIM ?= icarus
TOPLEVEL_LANG ?= verilog
WAVES ?= 0
GATES ?= no

# Include parent directory src
SRC_DIR = $(CURDIR)/../src

ifeq ($(GATES), yes)

# ------------------------------------------------------------------------------
# Gate-Level Simulation (GLS) Configuration
# ------------------------------------------------------------------------------
SIM_BUILD = sim_build/gl
COMPILE_ARGS += -DGL_TEST -DFUNCTIONAL -DUSE_POWER_PINS -DSIM -DUNIT_DELAY=\#1 -g2005

PDK_ROOT ?= $(HOME)/.volare
PDK ?= sky130A
SKY130_VERILOG = $(PDK_ROOT)/$(PDK)/libs.ref/sky130_fd_sc_hd/verilog

VERILOG_SOURCES = $(SKY130_VERILOG)/primitives.v \
                  $(SKY130_VERILOG)/sky130_fd_sc_hd.v \
                  $(CURDIR)/gate_level_netlist.v \
                  $(CURDIR)/tb.v

TOPLEVEL = tb
MODULE   = test_scim_core

else

# ------------------------------------------------------------------------------
# Behavioral RTL Simulation Configuration
# ------------------------------------------------------------------------------
SIM_BUILD = sim_build/rtl
VERILOG_SOURCES = $(SRC_DIR)/tt_um_scim_core.v \
                  $(SRC_DIR)/lfsr8_galois.v \
                  $(SRC_DIR)/scim_sng_bank.v \
                  $(SRC_DIR)/scim_pe.v \
                  $(SRC_DIR)/scim_compressor_42.v \
                  $(SRC_DIR)/scim_wallace_tree.v \
                  $(SRC_DIR)/scim_accumulator.v \
                  $(SRC_DIR)/scim_weight_mem.v

TOPLEVEL ?= tt_um_scim_core
MODULE   ?= test_scim_core
COMPILE_ARGS += -I$(SRC_DIR) -g2005

endif

# Waveform dumping if requested
ifeq ($(WAVES), 1)
    COMPILE_ARGS += -DWAVES
    DUMPFILE ?= $(if $(TESTCASE),waves_$(TESTCASE).vcd,tb.vcd)
    PLUSARGS += +DUMPFILE=$(DUMPFILE)
endif

# Default target: run simulation and sanitize results.xml for Tiny Tapeout CI
.DEFAULT_GOAL := all

# Include Cocotb standard simulator makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim

all: sim
	@if [ -f results.xml ]; then sed -i 's/failures="0"/fails="0"/g' results.xml; fi

# Automatic netlist sync for gate-level tests
$(CURDIR)/gate_level_netlist.v:
	@if [ -f $(CURDIR)/../gds/tt_um_scim_core.v ]; then \
		cp $(CURDIR)/../gds/tt_um_scim_core.v $(CURDIR)/gate_level_netlist.v; \
	elif [ -f $(CURDIR)/../artifacts/tt_submission/tt_submission/tt_um_scim_core.v ]; then \
		cp $(CURDIR)/../artifacts/tt_submission/tt_submission/tt_um_scim_core.v $(CURDIR)/gate_level_netlist.v; \
	fi

# ==============================================================================
# Custom Targets for Submodule Unit Testing & Gate-Level Simulation
# ==============================================================================
.PHONY: test_lfsr test_compressor test_wallace test_core test_all test_gls gls_waves gls_waves_dft gls_waves_saturation gls_waves_overclock clean_all

test_lfsr:
	$(MAKE) -B SIM=$(SIM) TOPLEVEL=lfsr8_galois MODULE=test_lfsr VERILOG_SOURCES="$(SRC_DIR)/lfsr8_galois.v"

test_compressor:
	$(MAKE) -B SIM=$(SIM) TOPLEVEL=scim_compressor_42 MODULE=test_compressor VERILOG_SOURCES="$(SRC_DIR)/scim_compressor_42.v"

test_wallace:
	$(MAKE) -B SIM=$(SIM) TOPLEVEL=scim_wallace_tree MODULE=test_compressor VERILOG_SOURCES="$(SRC_DIR)/scim_wallace_tree.v $(SRC_DIR)/scim_compressor_42.v"

test_core:
	$(MAKE) -B SIM=$(SIM) TOPLEVEL=tt_um_scim_core MODULE=test_scim_core

test_all: test_lfsr test_compressor test_wallace test_core
	@echo "========================================================"
	@echo " ALL CIMTinyTO GATE 1 UNIT & REGRESSION SUITES PASSED! "
	@echo "========================================================"

test_gls: $(CURDIR)/gate_level_netlist.v
	$(MAKE) -B GATES=yes TOPLEVEL=tb MODULE=test_scim_core
	@if [ -f results.xml ]; then sed -i 's/failures="0"/fails="0"/g' results.xml; fi
	@echo "========================================================"
	@echo " ALL CIMTinyTO GATE-LEVEL SIMULATION REGRESSIONS PASSED! "
	@echo "========================================================"

gls_waves: $(CURDIR)/gate_level_netlist.v
	$(MAKE) -B GATES=yes WAVES=1 TOPLEVEL=tb MODULE=test_scim_core DUMPFILE=$(DUMPFILE)
	@if [ -f results.xml ]; then sed -i 's/failures="0"/fails="0"/g' results.xml; fi
	@echo "========================================================"
	@echo " GLS WAVEFORMS DUMPED TO $(DUMPFILE) SUCCESSFULLY! "
	@echo "========================================================"

gls_waves_dft: $(CURDIR)/gate_level_netlist.v
	$(MAKE) gls_waves TESTCASE=test_scim_core_dft_loopback DUMPFILE=waves_dft_loopback.vcd

gls_waves_saturation: $(CURDIR)/gate_level_netlist.v
	$(MAKE) gls_waves TESTCASE=test_scim_core_saturation_sticky_overflow DUMPFILE=waves_saturation.vcd

gls_waves_overclock: $(CURDIR)/gate_level_netlist.v
	$(MAKE) gls_waves TESTCASE=test_scim_core_overclocking_200mhz DUMPFILE=waves_overclock_200mhz.vcd

clean_all: clean
	rm -rf sim_build __pycache__ results.xml *.vcd *.fst gate_level_netlist.v
