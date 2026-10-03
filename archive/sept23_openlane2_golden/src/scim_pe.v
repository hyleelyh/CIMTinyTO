// ============================================================================
// Module: scim_pe
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: SkyWater 130nm / IHP SG13G2 (Tiny Tapeout)
// Standard: IEEE 1364-2001 Verilog
// ============================================================================
// Pedagogical & Silicon Rationale:
//
// 1. Single-Wire Unified PE Arithmetic:
//    - Naive ternary implementations require dual wires (pe_pos, pe_neg) per PE,
//      which doubles the number of Wallace trees across the macro (32 trees,
//      exceeding the Tiny Tapeout area budget by >1,000 cells).
//    - By formulating the column delta as:
//        * Mode 0 (Unipolar):    Δ = P                (where P = Σ (a & w))
//        * Mode 1 (Bipolar):     Δ = 2X - 16          (where X = Σ XNOR(a, w))
//        * Mode 2 (Hybrid ReLU): Δ = 2P - A           (where A = Σ a)
//      every PE in the array outputs a SINGLE BINARY BIT to the column tree!
//
// 2. Logic Sharing & Footprint Optimization:
//    - Mode 0 and Mode 2 share the exact same Boolean sub-expression: (a_bit & w_bit).
//    - Mode 1 uses: ~(a_bit ^ w_bit).
//    - Total PE logic is simply a 2-input AND, a 2-input XNOR, and a 2:1 MUX:
//        pe_out = (mode == 2'b01) ? xnor_out : and_out;
//    - Fits into ~2-3 standard cells (~10-15 μm² in Sky130).
//
// 3. Zero Dynamic Multiplexer Power:
//    - The mode[1:0] signal is static throughout the 256-cycle compute phase.
//    - The MUX select pin activity factor α = 0, consuming ZERO dynamic power!
// ============================================================================

`default_nettype none

module scim_pe (
    input  wire       a_bit,              // 1-bit stochastic activation from SNG row
    input  wire       w_bit,              // 1-bit weight from local memory DFF
    input  wire [1:0] mode,               // Operating mode:
                                          //   2'b00: Mode 0 (Unipolar AND)
                                          //   2'b01: Mode 1 (Bipolar XNOR)
                                          //   2'b10: Mode 2 (Hybrid ReLU)
                                          //   2'b11: Reserved (default to AND)
    output wire       pe_out              // Single binary bit feeding column Wallace tree
);

    wire and_res  = a_bit & w_bit;
    wire xnor_res = ~(a_bit ^ w_bit);

    // Mode 1 selects XNOR; Mode 0, Mode 2, and default select AND
    assign pe_out = (mode == 2'b01) ? xnor_res : and_res;

endmodule

`default_nettype wire
