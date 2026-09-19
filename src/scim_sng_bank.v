// ============================================================================
// Module: scim_sng_bank
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: SkyWater 130nm / IHP SG13G2 (Tiny Tapeout)
// Standard: IEEE 1364-2001 Verilog
// ============================================================================
// Pedagogical & Silicon Rationale:
//
// 1. Compile-Time Parameterized SNG Seeds (Zero Silicon Cost):
//    - SNG_SEEDS is a 128-bit compile-time parameter holding initial seeds for
//      all 16 LFSR channels (Channel 0 at [7:0] up to Channel 15 at [127:120]).
//    - Compile-time parameterization enables researchers to study alternative
//      seed families (e.g. coprime strides, Weyl sequences, trained seeds)
//      with ZERO silicon area overhead (0 extra transistors / 0 dynamic power).
//
// 2. Default Stride-15 Galois Trajectory Spacing (|r_ij| < 0.026):
//    - The default seeds (8'h5C, 8'hF1, 8'hAC...) are spaced by 15 cycles
//      along the 255-state trajectory (Steps 1, 16, 31, 46...).
//    - Guarantees near-perfect spatial orthogonality (|r_ij| < 0.0259)
//      and bit-exact equivalence with Gate 0 golden reference vectors.
//
// 3. Digital Magnitude Comparator (act >= LFSR):
//    - For an 8-bit unsigned activation act in [0, 255], comparing (act >= LFSR)
//      yields exactly 'act' ones over the 255 non-zero LFSR states:
//      * act = 0   -> 0 ones (never >= 1..255)
//      * act = 255 -> 255 ones (always >= 1..255)
//      * act = K   -> exactly K ones -> probability P = K / 255.
// ============================================================================

`default_nettype none

module scim_sng_bank #(
    // Stride-15 Galois trajectory seeds (precomputed from x^8 + x^6 + x^5 + x^4 + 1)
    // Channel 0 is LSB byte (bits [7:0]); Channel 15 is MSB byte (bits [127:120]).
    parameter [127:0] SNG_SEEDS = {
        8'hDF, 8'h6A, 8'hBB, 8'hEA,  // Ch 15..12 (Steps 226, 211, 196, 181)
        8'h8F, 8'hCE, 8'h15, 8'hE8,  // Ch 11..8  (Steps 166, 151, 136, 121)
        8'h7C, 8'h61, 8'hD6, 8'hF4,  // Ch 7..4   (Steps 106,  91,  76,  61)
        8'h0A, 8'hAC, 8'hF1, 8'h5C   // Ch 3..0   (Steps  46,  31,  16,   1)
    }
)(
    input  wire         clk,              // Master clock (rising edge)
    input  wire         rst_n,            // Synchronous active-low reset
    input  wire         en,               // Clock enable during compute
    input  wire [127:0] act_in,           // 16 channels x 8-bit activations
    output wire [15:0]  sng_out           // 16-channel 1-bit stochastic output
);

    // Internal LFSR states
    wire [7:0] lfsr_state [15:0];

    // Instantiate 16 parallel Galois LFSRs using parameterized seed vector
    genvar i;
    generate
        for (i = 0; i < 16; i = i + 1) begin : gen_lfsr
            lfsr8_galois #(
                .SEED(SNG_SEEDS[i*8 +: 8])
            ) u_lfsr (
                .clk(clk),
                .rst_n(rst_n),
                .en(en),
                .state(lfsr_state[i])
            );
        end
    endgenerate

    // 16 parallel digital magnitude comparators
    generate
        for (i = 0; i < 16; i = i + 1) begin : gen_sng_comp
            wire [7:0] act_ch = act_in[i*8 +: 8];
            assign sng_out[i] = (act_ch >= lfsr_state[i]);
        end
    endgenerate

endmodule

`default_nettype wire
