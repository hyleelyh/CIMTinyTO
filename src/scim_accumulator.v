// ============================================================================
// Module: scim_accumulator
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: SkyWater 130nm / IHP SG13G2 (Tiny Tapeout)
// Standard: IEEE 1364-2001 Verilog
// ============================================================================
// Pedagogical & Silicon Rationale:
//
// 1. Bit-Growth Sizing (13-Bit Signed Range [-4096, +4095]):
//    - In Stochastic Computing with N = 256 cycles across 16 PE rows:
//        Worst-case positive sum: +16 * 256 = +4096
//        Worst-case negative sum: -16 * 256 = -4096
//    - Standard 12-bit signed accumulators (range [-2048, +2047]) would suffer
//      destructive arithmetic overflow/wrap-around distortion on saturation.
//    - A 13-bit two's complement register guarantees exact full-scale coverage.
//
// 2. Saturation Clamping & Sticky Flag:
//    - To prevent catastrophic wrap-around (where +4096 wraps to -4096 in two's
//      complement), internal addition uses a 14-bit sign-extended datapath.
//    - Values exceeding +4095 clamp at +4095 (13'h0FFF).
//    - Values below -4096 clamp at -4096 (13'h1000).
//    - sat_flag is a sticky indicator that remains high until clr/rst_n.
// ============================================================================

`default_nettype none

module scim_accumulator #(
    parameter integer WIDTH = 13
)(
    input  wire                    clk,       // Master clock (rising edge)
    input  wire                    rst_n,     // Synchronous active-low reset
    input  wire                    clr,       // Synchronous clear to 0
    input  wire                    en,        // Accumulate enable
    input  wire signed [5:0]       delta,     // Single-cycle column delta [-16, +16]
    output reg  signed [WIDTH-1:0] acc_val,   // Accumulated 13-bit signed result
    output reg                     sat_flag   // Sticky saturation indicator
);

    // 14-bit extended sum to detect overflow beyond 13-bit signed limits
    wire signed [WIDTH:0] sum_ext;
    assign sum_ext = {acc_val[WIDTH-1], acc_val} + {{ (WIDTH-5){delta[5]} }, delta};

    // Limits for 13-bit signed: Max = +4095, Min = -4096
    localparam signed [WIDTH:0] MAX_POS =  14'sd4095;
    localparam signed [WIDTH:0] MIN_NEG = -14'sd4096;

    always @(posedge clk) begin
        if (!rst_n) begin
            acc_val  <= {WIDTH{1'b0}};
            sat_flag <= 1'b0;
        end else if (clr) begin
            acc_val  <= {WIDTH{1'b0}};
            sat_flag <= 1'b0;
        end else if (en) begin
            if (sum_ext > MAX_POS) begin
                acc_val  <= 13'sd4095;
                sat_flag <= 1'b1;
            end else if (sum_ext < MIN_NEG) begin
                acc_val  <= -13'sd4096;
                sat_flag <= 1'b1;
            end else begin
                acc_val  <= sum_ext[WIDTH-1:0];
                sat_flag <= sat_flag;
            end
        end
    end

endmodule

`default_nettype wire
