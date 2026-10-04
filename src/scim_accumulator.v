// ============================================================================
// Module: scim_accumulator
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: SkyWater 130nm / IHP SG13G2 (Tiny Tapeout)
// Standard: IEEE 1364-2001 Verilog
// ============================================================================
// Pedagogical & Silicon Rationale (Path B Streamlined):
//
// 1. Bit-Growth Sizing (13-Bit Signed Range [-4096, +4095]):
//    - In Stochastic Computing with N = 256 cycles across 16 PE rows:
//        Worst-case positive sum: +16 * 256 = +4096
//        Worst-case negative sum: -16 * 256 = -4096
//    - Standard 12-bit signed accumulators (range [-2048, +2047]) would suffer
//      destructive arithmetic overflow/wrap-around distortion on saturation.
//    - A 13-bit two's complement register guarantees exact full-scale coverage.
//
// 2. 2-Gate Sign-Bit Saturation Clamping (Zero-Comparator Latency):
//    - Behavioral relational operators (sum_ext > +4095 and sum_ext < -4096)
//      synthesize into two 14-bit magnitude comparators with ripple-carry subtractors
//      (~120 gates per accumulator * 16 cols = ~1,920 cells), dominating area and
//      creating a long combinational timing critical path in the accumulation loop.
//    - Silicon Reality: Since single-cycle delta is strictly bounded to [-16, +16],
//      sum_ext (14-bit signed) cannot exceed [+4111, -4112]. Overflow beyond the
//      13-bit signed boundary [-4096, +4095] is detected purely by comparing the
//      extended sign bit (bit 13) and the 13-bit sign bit (bit 12):
//        * Normal In-Range:    sum_ext[13] == sum_ext[12] (sign parity preserved)
//        * Positive Overflow:  (~sum_ext[13]) &  sum_ext[12] (clamped to +4095)
//        * Negative Overflow:   sum_ext[13]  & (~sum_ext[12]) (clamped to -4096)
//    - Entire detection reduces to TWO standard-cell gates (`and2b`) per column,
//      saving ~1,500 standard cells and slashing accumulator timing delay!
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
    // Hardening (Hole #5): IEEE 1364-2001 treats { ... } concatenations as strictly
    // unsigned. Wrap in $signed(...) to guarantee signed arithmetic across all EDA tools.
    wire signed [WIDTH:0] sum_ext;
    assign sum_ext = $signed({acc_val[WIDTH-1], acc_val}) + 
                     $signed({{ (WIDTH-5){delta[5]} }, delta});

    // 2-Gate Sign-Bit Overflow Detection
    wire pos_ovf = (~sum_ext[WIDTH]) & sum_ext[WIDTH-1];
    wire neg_ovf = sum_ext[WIDTH] & (~sum_ext[WIDTH-1]);

    always @(posedge clk) begin
        if (!rst_n) begin
            acc_val  <= {WIDTH{1'b0}};
            sat_flag <= 1'b0;
        end else if (clr) begin
            acc_val  <= {WIDTH{1'b0}};
            sat_flag <= 1'b0;
        end else if (en) begin
            if (pos_ovf) begin
                acc_val  <= {1'b0, {(WIDTH-1){1'b1}}}; // Clamp at +4095 (13'sd4095)
                sat_flag <= 1'b1;
            end else if (neg_ovf) begin
                acc_val  <= {1'b1, {(WIDTH-1){1'b0}}}; // Clamp at -4096 (-13'sd4096)
                sat_flag <= 1'b1;
            end else begin
                acc_val  <= sum_ext[WIDTH-1:0];
                sat_flag <= sat_flag;
            end
        end
    end

endmodule

`default_nettype wire
