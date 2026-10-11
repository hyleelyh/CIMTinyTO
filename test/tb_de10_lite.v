// ============================================================================
// Testbench Harness: tb_de10_lite
// Project: CIMTinyTO
// Target: DE10-Lite Tactile Console Simulation
// Standard: IEEE 1364-2001 Verilog
// ============================================================================

`timescale 1ns / 1ps
`default_nettype none

module tb_de10_lite (
    input  wire        MAX10_CLK1_50,
    input  wire [1:0]  KEY,
    input  wire [9:0]  SW,
    output wire [9:0]  LEDR,
    output wire [7:0]  HEX0,
    output wire [7:0]  HEX1,
    output wire [7:0]  HEX2,
    output wire [7:0]  HEX3,
    output wire [7:0]  HEX4,
    output wire [7:0]  HEX5
);

    // Fast debouncer parameter for microsecond simulation
    de10_lite_top dut (
        .MAX10_CLK1_50 (MAX10_CLK1_50),
        .KEY           (KEY),
        .SW            (SW),
        .LEDR          (LEDR),
        .HEX0          (HEX0),
        .HEX1          (HEX1),
        .HEX2          (HEX2),
        .HEX3          (HEX3),
        .HEX4          (HEX4),
        .HEX5          (HEX5)
    );

    // Override debouncer and clock divider parameters for fast simulation
    defparam dut.u_deb_key0.CLKS_FOR_STABLE = 4;
    defparam dut.u_deb_key1.CLKS_FOR_STABLE = 4;
    defparam dut.CLK_DIV_LIMIT              = 4;

endmodule

`default_nettype wire
