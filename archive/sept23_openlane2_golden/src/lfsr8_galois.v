// ============================================================================
// Module: lfsr8_galois
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: SkyWater 130nm / IHP SG13G2 (Tiny Tapeout)
// Standard: IEEE 1364-2001 Verilog
// ============================================================================
// Pedagogical & Silicon Rationale:
//
// 1. Galois vs. Fibonacci LFSR Topology:
//    - Fibonacci LFSR: Feedback taps are tapped from multiple flip-flops and
//      propagated through an external cascade of XOR gates before entering MSB.
//      For an 8-bit polynomial, this creates a long combinational chain
//      (T_xor * log2(taps)), worsening setup timing margin.
//    - Galois LFSR (implemented here): XOR gates are distributed internally
//      between flip-flops. In each clock cycle, every state bit either shifts
//      or undergoes at most ONE XOR gate delay (~0.25 ns in Sky130).
//      The critical path delay is strictly O(1), independent of polynomial order!
//
// 2. Maximal-Length GF(2) Primitive Polynomial:
//    - Polynomial: P(x) = x^8 + x^6 + x^5 + x^4 + 1 (Mask: 8'hB8 = 8'b1011_1000).
//    - Generates a maximal pseudo-random sequence of 2^8 - 1 = 255 non-zero states
//      before deterministically repeating.
//
// 3. Silicon Trap & Guardrail (Zero-State Lockup):
//    - If all 8 flip-flops power up or glitch into 8'h00:
//      8'h00 >> 1 = 0, LSB = 0 -> no XOR applied -> next state = 8'h00.
//      The LFSR is permanently locked in the all-zero dead zone!
//    - Guardrail: Synchronous active-low reset (rst_n) forces the LFSR to
//      a guaranteed non-zero SEED (falling back to 8'h01 if SEED is 0).
// ============================================================================

`default_nettype none

module lfsr8_galois #(
    parameter [7:0] SEED = 8'h01,         // Initial non-zero seed state
    parameter [7:0] POLY = 8'hB8          // x^8 + x^6 + x^5 + x^4 + 1
)(
    input  wire       clk,                // Master clock (rising edge)
    input  wire       rst_n,              // Synchronous active-low reset
    input  wire       en,                 // Clock enable (active-high during compute)
    output reg  [7:0] state               // 8-bit pseudo-random state output
);

    always @(posedge clk) begin
        if (!rst_n) begin
            // Guardrail: Guarantee non-zero state on reset release
            state <= (SEED == 8'h00) ? 8'h01 : SEED;
        end else if (en) begin
            // Galois shift & feedback logic (right shift)
            if (state[0]) begin
                state <= (state >> 1) ^ POLY;
            end else begin
                state <= (state >> 1);
            end
        end
    end

endmodule

`default_nettype wire
