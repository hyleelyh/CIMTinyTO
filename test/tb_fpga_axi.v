// ==============================================================================
// tb_fpga_axi.v — AXI4-Lite Testbench Wrapper for Pre-Synthesis Verification
// Target: Icarus Verilog + Cocotb
// ==============================================================================

`default_nettype none
`timescale 1ns / 1ps

module tb_fpga_axi (
    input  wire        s_axi_aclk,
    input  wire        s_axi_aresetn,
    input  wire [5:0]  s_axi_awaddr,
    input  wire [2:0]  s_axi_awprot,
    input  wire        s_axi_awvalid,
    output wire        s_axi_awready,
    input  wire [31:0] s_axi_wdata,
    input  wire [3:0]  s_axi_wstrb,
    input  wire        s_axi_wvalid,
    output wire        s_axi_wready,
    output wire [1:0]  s_axi_bresp,
    output wire        s_axi_bvalid,
    input  wire        s_axi_bready,
    input  wire [5:0]  s_axi_araddr,
    input  wire [2:0]  s_axi_arprot,
    input  wire        s_axi_arvalid,
    output wire        s_axi_arready,
    output wire [31:0] s_axi_rdata,
    output wire [1:0]  s_axi_rresp,
    output wire        s_axi_rvalid,
    input  wire        s_axi_rready,
    input  wire        ext_pll_clk,
    output wire [7:0]  pmod_a,
    output wire [7:0]  pmod_b
);

  initial begin
    $dumpfile("tb_fpga_axi.vcd");
    $dumpvars(0, tb_fpga_axi);
  end

  tt_scim_axi_wrapper #(
      .C_S_AXI_DATA_WIDTH(32),
      .C_S_AXI_ADDR_WIDTH(6)
  ) dut (
      .s_axi_aclk    (s_axi_aclk),
      .s_axi_aresetn (s_axi_aresetn),
      .s_axi_awaddr  (s_axi_awaddr),
      .s_axi_awprot  (s_axi_awprot),
      .s_axi_awvalid (s_axi_awvalid),
      .s_axi_awready (s_axi_awready),
      .s_axi_wdata   (s_axi_wdata),
      .s_axi_wstrb   (s_axi_wstrb),
      .s_axi_wvalid  (s_axi_wvalid),
      .s_axi_wready  (s_axi_wready),
      .s_axi_bresp   (s_axi_bresp),
      .s_axi_bvalid  (s_axi_bvalid),
      .s_axi_bready  (s_axi_bready),
      .s_axi_araddr  (s_axi_araddr),
      .s_axi_arprot  (s_axi_arprot),
      .s_axi_arvalid (s_axi_arvalid),
      .s_axi_arready (s_axi_arready),
      .s_axi_rdata   (s_axi_rdata),
      .s_axi_rresp   (s_axi_rresp),
      .s_axi_rvalid  (s_axi_rvalid),
      .s_axi_rready  (s_axi_rready),
      .ext_pll_clk   (ext_pll_clk),
      .pmod_a        (pmod_a),
      .pmod_b        (pmod_b)
  );

endmodule

`default_nettype wire
