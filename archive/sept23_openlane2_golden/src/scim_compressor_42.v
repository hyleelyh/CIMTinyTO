// ============================================================================
// Module: scim_compressor_42
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: SkyWater 130nm / IHP SG13G2 (Tiny Tapeout)
// Standard: IEEE 1364-2001 Verilog
// ============================================================================
// Pedagogical & Silicon Rationale:
//
// 1. 4:2 Compressor Arithmetic Identity:
//    - Compresses 5 binary inputs (weight 2^0) into 3 outputs:
//        x1 + x2 + x3 + x4 + cin = sum + 2 * (carry + cout)
//      where:
//        * sum:   Output bit of weight 2^0 in current column.
//        * carry: Output bit of weight 2^1 in current column.
//        * cout:  Horizontal carry-out of weight 2^1 feeding to next column.
//
// 2. Zero Horizontal Carry Propagation (The Silicon Breakthrough):
//    - In a classical adder, carry-out ripples across bits: cout = f(cin).
//    - In this optimized 4:2 compressor:
//        cout = (x1 ^ x2) ? x3 : x1;
//      cout depends STRICTLY on primary inputs (x1, x2, x3) and is COMPLETELY
//      INDEPENDENT of cin!
//    - Therefore, across an array of 4:2 compressors, ALL cout bits are
//      evaluated in parallel simultaneously with zero horizontal rippling delay.
// ============================================================================

`default_nettype none

module scim_compressor_42 (
    input  wire x1,                       // Primary input bit 1 (weight 2^0)
    input  wire x2,                       // Primary input bit 2 (weight 2^0)
    input  wire x3,                       // Primary input bit 3 (weight 2^0)
    input  wire x4,                       // Primary input bit 4 (weight 2^0)
    input  wire cin,                      // Carry-in from adjacent column (weight 2^0)
    output wire sum,                      // Sum bit (weight 2^0)
    output wire carry,                    // Vertical carry bit (weight 2^1)
    output wire cout                      // Horizontal carry-out (weight 2^1, independent of cin)
);

    wire x12   = x1 ^ x2;
    wire x1234 = x12 ^ x3 ^ x4;

    // Sum output: Parity of all 5 inputs
    assign sum = x1234 ^ cin;

    // Cout output: 2:1 MUX controlled by x12 (independent of cin!)
    assign cout = x12 ? x3 : x1;

    // Carry output: 2:1 MUX controlled by x1234
    assign carry = x1234 ? cin : x4;

endmodule

`default_nettype wire
