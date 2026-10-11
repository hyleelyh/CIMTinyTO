// ============================================================================
// Module: debounce
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: Terasic DE10-Lite FPGA (Intel MAX 10 10M50DAF484C7G)
// Standard: IEEE 1364-2001 Verilog
// Description: Glitch-free mechanical pushbutton debouncer & single-cycle pulser.
// ============================================================================
// Pedagogical & Silicon Rationale:
//
// 1. Mechanical Contact Bounce & The "Hair-Trigger" Hazard:
//    - Physical momentary switches (KEY0, KEY1) bounce mechanically for 5-20 ms
//      upon contact closure and release.
//    - Feeding an unconditioned button directly to a clock or enable input
//      causes dozens of spurious clock edges per human press, corrupting
//      internal state and advancing accumulators uncontrollably.
//
// 2. Metastability Prevention (2-Stage Synchronizer):
//    - Asynchronous button transitions violate flip-flop setup/hold timing (tsu/th).
//    - We cascade two D-flip-flops (sync_d1, sync_d2) to resolve metastable states
//      before sampling by the digital filter, maximizing MTBF (> 100 years).
//
// 3. Digital Integrating Low-Pass Filter:
//    - A synchronous counter verifies that the incoming state remains constant
//      for a continuous integration window (default: ~10 ms @ 50 MHz = 500,000 cycles).
//    - Any transient glitch resets the counter, rejecting contact noise.
//
// 4. Edge Detection & Single-Cycle Pulse Generation:
//    - Generates a guaranteed single-cycle pulse ('pulse_press') on button depression
//      for manual clock stepping and strobe triggers.
// ============================================================================

`default_nettype none

module debounce #(
    // Clock cycles to verify stable input before updating output
    // At 50 MHz (20 ns period), 500_000 cycles = 10.0 ms integration filter.
    // For simulation, override parameter to smaller value (e.g. 5 to 10).
    parameter integer CLKS_FOR_STABLE = 500_000
)(
    input  wire clk,          // 50 MHz master oscillator
    input  wire rst_n,        // Active-low synchronous reset
    input  wire async_in,     // Raw asynchronous mechanical input

    output reg  debounced_out = 1'b1, // Filtered steady-state level
    output reg  pulse_press = 1'b0,   // 1-cycle active-high pulse on button PRESS (falling edge of active-low button)
    output reg  pulse_release = 1'b0  // 1-cycle active-high pulse on button RELEASE (rising edge of active-low button)
);

    // ========================================================================
    // 1. TWO-STAGE METASTABILITY SYNCHRONIZER
    // ========================================================================
    reg sync_d1 = 1'b1;
    reg sync_d2 = 1'b1;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sync_d1 <= 1'b1; // Default to inactive high (active-low button pulled up)
            sync_d2 <= 1'b1;
        end else begin
            sync_d1 <= async_in;
            sync_d2 <= sync_d1;
        end
    end

    // ========================================================================
    // 2. STABILITY INTEGRATOR COUNTER
    // ========================================================================
    // 32-bit counter accommodates integration window up to seconds
    reg [31:0] stable_cnt = 32'd0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stable_cnt    <= 32'd0;
            debounced_out <= 1'b1;
            pulse_press   <= 1'b0;
            pulse_release <= 1'b0;
        end else begin
            // Reset edge pulses by default
            pulse_press   <= 1'b0;
            pulse_release <= 1'b0;

            if (sync_d2 != debounced_out) begin
                // Input is attempting to transition; count consecutive matching cycles
                if (stable_cnt >= ((CLKS_FOR_STABLE > 0) ? (CLKS_FOR_STABLE - 1) : 0)) begin
                    debounced_out <= sync_d2;
                    stable_cnt    <= 32'd0;

                    // Generate single-cycle pulse on confirmed state transition
                    // DE10-Lite buttons are active-low (1 = unpressed, 0 = pressed)
                    if (debounced_out == 1'b1 && sync_d2 == 1'b0) begin
                        pulse_press <= 1'b1; // Press detected
                    end else if (debounced_out == 1'b0 && sync_d2 == 1'b1) begin
                        pulse_release <= 1'b1; // Release detected
                    end
                end else begin
                    stable_cnt <= stable_cnt + 32'd1;
                end
            end else begin
                // Input matches current debounced state; hold counter at 0
                stable_cnt <= 32'd0;
            end
        end
    end

endmodule

`default_nettype wire
