// ============================================================================
// Module: scim_weight_mem
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: SkyWater 130nm / IHP SG13G2 (Tiny Tapeout)
// Standard: IEEE 1364-2001 Verilog
// ============================================================================
// Pedagogical & Silicon Rationale:
//
// 1. Standard-Cell DFF Storage vs. Custom SRAM:
//    - Custom 6T SRAM bitcells require complex DRC/LVS boundary cells,
//      custom sense amplifiers, and write drivers that are incompatible
//      with pure standard-cell ASIC flows in OpenLane.
//    - Implementing the 256-bit weight matrix using 256 standard-cell DFFs
//      (sky130_fd_sc_hd__dfxtp_1) enables 100% automated synthesis, CTS,
//      and placement within the standard OpenLane flow.
//
// 2. DFT Serial Shift & Readback Loopback:
//    - Loading 256 weights in parallel would require 256 input pads (impossible
//      under Tiny Tapeout's 8-pin limit).
//    - Arranging the 256 DFFs as a serial shift chain requires only TWO pins:
//      w_din (data) and w_shift_en (shift strobe).
//    - The MSB is exposed as w_dout: connecting w_dout back to the host SPI
//      MISO enables 100% non-destructive readback verification (DFT)
//      without a single extra pin.
//
// 3. Dynamic Power Quiescence:
//    - During the 256-cycle compute phase, w_shift_en is held low.
//    - All 256 weight DFF outputs remain static, drawing zero dynamic
//      switching power (P_dyn = C * V^2 * f = 0).
// ============================================================================

`default_nettype none

module scim_weight_mem #(
    parameter integer ROWS = 16,
    parameter integer COLS = 16,
    parameter integer TOTAL_BITS = ROWS * COLS // 256 bits
)(
    input  wire                  clk,         // Master clock (rising edge)
    input  wire                  rst_n,       // Synchronous active-low reset
    input  wire                  w_shift_en,  // Serial shift enable
    input  wire                  w_din,       // Serial weight bit input
    output wire                  w_dout,      // Serial weight bit output (MSB loopback)
    output wire [TOTAL_BITS-1:0] weights_out  // Parallel 256-bit weight bus to PE array
);

    reg [TOTAL_BITS-1:0] shift_reg;

    always @(posedge clk) begin
        if (!rst_n) begin
            shift_reg <= {TOTAL_BITS{1'b0}};
        end else if (w_shift_en) begin
            // Shift in from LSB, shift out to MSB
            shift_reg <= {shift_reg[TOTAL_BITS-2:0], w_din};
        end
    end

    // MSB serves as the serial output for DFT loopback
    assign w_dout = shift_reg[TOTAL_BITS-1];

    // Parallel broadcast to the 16x16 PE array
    assign weights_out = shift_reg;

endmodule

`default_nettype wire
