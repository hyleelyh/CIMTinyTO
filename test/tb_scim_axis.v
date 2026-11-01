// ==============================================================================
// tb_scim_axis.v — AXI4-Stream Testbench Wrapper for Pre-Synthesis Verification
// Target: Icarus Verilog + Cocotb
// ==============================================================================

`default_nettype none
`timescale 1ns / 1ps

module tb_scim_axis (
    input  wire        aclk,
    input  wire        aresetn,
    input  wire [31:0] s_axis_tdata,
    input  wire        s_axis_tvalid,
    output wire        s_axis_tready,
    input  wire        s_axis_tlast,
    output wire [31:0] m_axis_tdata,
    output wire        m_axis_tvalid,
    input  wire        m_axis_tready,
    output wire        m_axis_tlast,
    output wire [7:0]  pmod_a,
    output wire [7:0]  pmod_b
);

  initial begin
    $dumpfile("tb_scim_axis.vcd");
    $dumpvars(0, tb_scim_axis);
  end

  scim_axis_stream_feeder #(
      .C_AXIS_DATA_WIDTH(32)
  ) dut (
      .aclk          (aclk),
      .aresetn       (aresetn),
      .s_axis_tdata  (s_axis_tdata),
      .s_axis_tvalid (s_axis_tvalid),
      .s_axis_tready (s_axis_tready),
      .s_axis_tlast  (s_axis_tlast),
      .m_axis_tdata  (m_axis_tdata),
      .m_axis_tvalid (m_axis_tvalid),
      .m_axis_tready (m_axis_tready),
      .m_axis_tlast  (m_axis_tlast),
      .pmod_a        (pmod_a),
      .pmod_b        (pmod_b)
  );

endmodule
`default_nettype wire
