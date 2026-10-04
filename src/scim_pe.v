// ============================================================================
// Module: scim_pe
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: SkyWater 130nm / IHP SG13G2 (Tiny Tapeout)
// Standard: IEEE 1364-2001 Verilog
// ============================================================================
// Pedagogical & Silicon Rationale (Path B Streamlined):
//
// 1. Pure Single-Gate AND Processing Element:
//    - By pruning Mode 1 (Bipolar XNOR mode), both supported modes:
//        * Mode 0 (Unipolar):    Δ = P                (where P = Σ (a & w))
//        * Mode 1 (Hybrid ReLU): Δ = 2P - A           (where A = Σ a)
//      share the EXACT identical Boolean product: P_i = a_bit & w_bit.
//    - Every PE simplifies to a single 2-input AND gate (sky130_fd_sc_hd__and2_1),
//      eliminating 256 XNOR gates and 256 2:1 multiplexers (~512 standard cells).
//
// 2. Eradication of Global Mode Wire Broadcast:
//    - Previously, a global 2-bit mode wire had to be routed across all 256 PEs,
//      causing severe micro-level pin crowding and detailed routing congestion.
//    - Eliminating mode from the PE completely frees local routing tracks on
//      met1 and met2, allowing TritonRoute detailed routing to converge cleanly.
// ============================================================================

`default_nettype none

module scim_pe (
    input  wire a_bit,              // 1-bit stochastic activation from SNG row
    input  wire w_bit,              // 1-bit weight from local memory DFF
    output wire pe_out              // Single binary bit feeding column Wallace tree
);

    assign pe_out = a_bit & w_bit;

endmodule

`default_nettype wire
