// ==============================================================================
// tb.v — Standard Tiny Tapeout Testbench Wrapper for CIMTinyTO
// Target: Icarus Verilog + Cocotb (RTL & Gate-Level Simulation)
// ==============================================================================

`default_nettype none
`timescale 1ns / 1ps

module tb (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       ena,
    input  wire [7:0] ui_in,
    input  wire [7:0] uio_in,
    output wire [7:0] uo_out,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe
);

`ifdef WAVES
  reg [1023:0] dump_filename;
  initial begin
    if ($value$plusargs("DUMPFILE=%s", dump_filename)) begin
      $dumpfile(dump_filename);
    end else begin
      $dumpfile("tb.vcd");
    end
    $dumpvars(0, tb);
  end
`endif

`ifdef GL_TEST
  wire VPWR = 1'b1;
  wire VGND = 1'b0;
`endif

  tt_um_scim_core user_project (
`ifdef GL_TEST
      .VPWR   (VPWR),
      .VGND   (VGND),
`endif
      .clk    (clk),
      .rst_n  (rst_n),
      .ena    (ena),
      .ui_in  (ui_in),
      .uio_in (uio_in),
      .uo_out (uo_out),
      .uio_out(uio_out),
      .uio_oe (uio_oe)
  );

endmodule
