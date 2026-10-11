// ============================================================================
// Module: hex7seg_decoder
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: Terasic DE10-Lite FPGA (Intel MAX 10 10M50DAF484C7G)
// Standard: IEEE 1364-2001 Verilog
// Description: Active-low 7-segment hex decoder with blanking control.
// ============================================================================
// Pedagogical & Silicon Rationale:
//
// 1. Common-Anode Display Polarity:
//    - The DE10-Lite onboard 7-segment displays (HEX0 - HEX5) use common-anode
//      LEDs. Setting a pin to LOW (1'b0) sinks current, illuminating the segment.
//      Setting a pin to HIGH (1'b1) turns off the segment.
//
// 2. Segment Mapping:
//           -- a (0) --
//          |           |
//        f (5)       b (1)
//          |           |
//           -- g (6) --
//          |           |
//        e (4)       c (2)
//          |           |
//           -- d (3) --    . dp (7)
//
// 3. Glitch-Free Combinatorial Mapping:
//    - Fully specified 16-case truth table ensures zero unintended latches.
//    - Optional blanking input enables leading-zero suppression.
// ============================================================================

`default_nettype none

module hex7seg_decoder (
    input  wire [3:0] hex_digit,  // 4-bit nibble (0x0 to 0xF)
    input  wire       blank,      // When 1, all segments turned off (111_1111)
    output reg  [6:0] seg         // Active-low segments: {g, f, e, d, c, b, a}
);

    always @(*) begin
        if (blank) begin
            seg = 7'b111_1111; // All segments OFF
        end else begin
            case (hex_digit)
                //               gfe_dcba
                4'h0: seg = 7'b100_0000; // 0
                4'h1: seg = 7'b111_1001; // 1
                4'h2: seg = 7'b010_0100; // 2
                4'h3: seg = 7'b011_0000; // 3
                4'h4: seg = 7'b001_1001; // 4
                4'h5: seg = 7'b001_0010; // 5
                4'h6: seg = 7'b000_0010; // 6
                4'h7: seg = 7'b111_1000; // 7
                4'h8: seg = 7'b000_0000; // 8
                4'h9: seg = 7'b001_0000; // 9
                4'hA: seg = 7'b000_1000; // A
                4'hB: seg = 7'b000_0011; // b
                4'hC: seg = 7'b100_0110; // C
                4'hD: seg = 7'b010_0001; // d
                4'hE: seg = 7'b000_0110; // E
                4'hF: seg = 7'b000_1110; // F
                default: seg = 7'b111_1111;
            endcase
        end
    end

endmodule

`default_nettype wire
