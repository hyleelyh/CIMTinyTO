// ============================================================================
// Module: de10_lite_top
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: Terasic DE10-Lite FPGA (Intel MAX 10 10M50DAF484C7G)
// Standard: IEEE 1364-2001 Verilog
// Description: Tactile hardware evaluation console mapping switches, buttons,
//              LEDs, and 6x 7-segment hex displays to tt_um_scim_core.
// ============================================================================
// Pedagogical & Silicon Rationale:
//
// 1. Hands-On Hardware Tactile Console:
//    - Directly bridges human tactile interaction with silicon microarchitecture.
//    - Allows manual single-stepping via KEY0 pushbutton to observe internal
//      LFSR bitstream generation and Wallace tree accumulation cycle-by-cycle.
//
// 2. Glitch-Free Dual-Mode Clock Generation:
//    - SW[9] = 0 (Manual Step): KEY0 generates a clean 1-cycle clock pulse.
//    - SW[9] = 1 (Auto-Clock @ 5 Hz): Clock ticks at human visual speed so
//      accumulators and status LEDs can be observed progressing in real time.
//
// 3. Status Display & Hex Readout:
//    - LEDR[3:0]: Hardware status flags: busy (0), done (1), w_dout (2), any_overflow (3).
//    - LEDR[9:6]: Current selected accumulator channel index (0 to 15).
//    - HEX5-HEX4: Selected accumulator channel index (00 to 0F).
//    - HEX3-HEX0: 16-bit live display (cycle count during compute, or 13-bit
//      signed accumulator readout upon done assertion).
// ============================================================================

`default_nettype none

module de10_lite_top #(
    parameter integer CLK_DIV_LIMIT = 4_999_999
)(
    // 50 MHz Master Clock
    input  wire        MAX10_CLK1_50,

    // Pushbuttons (Active-Low)
    input  wire [1:0]  KEY,

    // Slide Switches (Active-High)
    input  wire [9:0]  SW,

    // 10 User LEDs (Active-High)
    output wire [9:0]  LEDR,

    // 6 Common-Anode 7-Segment Displays (Active-Low)
    // Bit 7 is decimal point (dp), Bits [6:0] are segments {g, f, e, d, c, b, a}
    output wire [7:0]  HEX0,
    output wire [7:0]  HEX1,
    output wire [7:0]  HEX2,
    output wire [7:0]  HEX3,
    output wire [7:0]  HEX4,
    output wire [7:0]  HEX5
);

    // ========================================================================
    // 1. DEBOUNCERS & SYNCHRONIZERS
    // ========================================================================
    wire key0_debounced;
    wire key0_press_pulse;
    wire key0_rel_pulse;
    /* verilator lint_off SYNCASYNCNET */
    wire key1_debounced;
    /* verilator lint_on SYNCASYNCNET */
    wire key1_press_pulse;
    wire key1_rel_pulse;

    // KEY0: Clock Stepping / Action Button
    debounce #(.CLKS_FOR_STABLE(500_000)) u_deb_key0 (
        .clk           (MAX10_CLK1_50),
        .rst_n         (1'b1),
        .async_in      (KEY[0]),
        .debounced_out (key0_debounced),
        .pulse_press   (key0_press_pulse),
        .pulse_release (key0_rel_pulse)
    );

    // KEY1: Master Active-Low Reset
    debounce #(.CLKS_FOR_STABLE(500_000)) u_deb_key1 (
        .clk           (MAX10_CLK1_50),
        .rst_n         (1'b1),
        .async_in      (KEY[1]),
        .debounced_out (key1_debounced),
        .pulse_press   (key1_press_pulse),
        .pulse_release (key1_rel_pulse)
    );

    // master_rst_n is a debounced synchronous FPGA signal driving both local
    // synchronous logic and the frozen ASIC core's asynchronous pad reset synchronizer.
    /* verilator lint_off SYNCASYNCNET */
    wire master_rst_n = key1_debounced;
    /* verilator lint_on SYNCASYNCNET */

    // ========================================================================
    // 2. DUAL-MODE GLITCH-FREE CLOCK ENGINE
    // ========================================================================
    // SW[9] selects clocking mode:
    //   0 = Manual single-step (KEY0 generates a 1-cycle high pulse)
    //   1 = Auto slow clock (5 Hz: 50 MHz / 10,000,000)
    reg [23:0] clk_div_cnt     = 24'd0;
    reg        auto_clk_5hz    = 1'b0;
    reg [3:0]  step_pulse_hold = 4'd0;
    reg        manual_clk      = 1'b0;

    always @(posedge MAX10_CLK1_50) begin
        if (!master_rst_n) begin
            clk_div_cnt     <= 24'd0;
            auto_clk_5hz    <= 1'b0;
            step_pulse_hold <= 4'd0;
            manual_clk      <= 1'b0;
        end else begin
            // Clock divider (toggles every CLK_DIV_LIMIT cycles)
            if (clk_div_cnt >= CLK_DIV_LIMIT[23:0]) begin
                clk_div_cnt  <= 24'd0;
                auto_clk_5hz <= ~auto_clk_5hz;
            end else begin
                clk_div_cnt  <= clk_div_cnt + 24'd1;
            end

            // Manual clock pulse stretcher (stretches single press into clean pulse)
            if (key0_press_pulse) begin
                step_pulse_hold <= 4'd8; // Hold high for 8 cycles of 50 MHz (160 ns)
                manual_clk      <= 1'b1;
            end else if (step_pulse_hold > 4'd0) begin
                step_pulse_hold <= step_pulse_hold - 4'd1;
                if (step_pulse_hold == 4'd1) begin
                    manual_clk <= 1'b0;
                end
            end
        end
    end

    // Selected Core Clock: Clean multiplexer
    // When in reset (!master_rst_n), run from 50 MHz so all synchronous flip-flops initialize reliably.
    wire core_clk = (!master_rst_n) ? MAX10_CLK1_50 :
                    (SW[9])         ? auto_clk_5hz  : manual_clk;

    // ========================================================================
    // 3. SWITCH INTERPRETATION & CONTROL MAPPING
    // ========================================================================
    // SW[8] chooses functional page:
    //   0: Data Input Mode (SW[7:0] drives ui_in[7:0])
    //   1: Command / Control Mode:
    //      SW[0]: w_din
    //      SW[1]: w_shift_en
    //      SW[2]: wr_act
    //      SW[3]: ctrl_strobe
    //      SW[7:4]: Selected accumulator channel for display readout (0 to 15)

    // CDC Pulse Stretcher: Stretches 1-cycle KEY0 press to span multiple slow auto_clk_5hz edges
    reg [23:0] strobe_hold = 24'd0;
    always @(posedge MAX10_CLK1_50) begin
        if (!master_rst_n) begin
            strobe_hold <= 24'd0;
        end else begin
            if (key0_press_pulse && SW[9]) begin
                strobe_hold <= (CLK_DIV_LIMIT[23:0] << 2) + 24'd10;
            end else if (strobe_hold > 24'd0) begin
                strobe_hold <= strobe_hold - 24'd1;
            end
        end
    end
    wire auto_strobe = (strobe_hold > 24'd0);

    wire [7:0] core_ui_in = SW[7:0];

    wire core_w_din       = (SW[8]) ? SW[0] : 1'b0;
    wire core_w_shift_en  = (SW[8]) ? SW[1] : 1'b0;
    wire core_wr_act      = (SW[8]) ? SW[2] : 1'b0;
    wire core_ctrl_strobe = (SW[8]) ? SW[3] : auto_strobe;

    wire [7:0] core_uio_in = {core_ctrl_strobe, core_wr_act, core_w_shift_en, core_w_din, 4'b0000};

    // Core outputs
    wire [7:0] core_uo_out;
    wire [7:0] core_uio_out;
    wire [7:0] core_uio_oe;

    // ========================================================================
    // 4. INSTANTIATE IMMUTABLE TINY TAPEOUT CORE
    // ========================================================================
    tt_um_scim_core u_scim_core (
        .ui_in   (core_ui_in),
        .uo_out  (core_uo_out),
        .uio_in  (core_uio_in),
        .uio_out (core_uio_out),
        .uio_oe  (core_uio_oe),
        .ena     (1'b1),
        .clk     (core_clk),
        .rst_n   (master_rst_n)
    );

    // ========================================================================
    // 5. CYCLE COUNTER & ACCUMULATOR MONITOR
    // ========================================================================
    reg [15:0] cycle_cnt = 16'd0;
    wire core_busy = core_uio_out[0];

    always @(posedge core_clk) begin
        if (!master_rst_n) begin
            cycle_cnt <= 16'd0;
        end else begin
            if (core_busy) begin
                cycle_cnt <= cycle_cnt + 16'd1;
            end else if (core_ctrl_strobe) begin
                cycle_cnt <= 16'd0;
            end
        end
    end

    // ========================================================================
    // 6. 7-SEGMENT DISPLAY VALUE FORMATTER
    // ========================================================================
    // Channel selection:
    // If SW[8]=1, channel is selected by SW[7:4].
    // If SW[8]=0, channel is selected by SW[3:0].
    wire [3:0] disp_channel = (SW[8]) ? SW[7:4] : SW[3:0];

    // What to display on HEX3..HEX0:
    // While busy: display live cycle count
    // When idle/done: display the current uo_out output byte
    wire [15:0] disp_data = (core_busy) ? cycle_cnt : {8'h00, core_uo_out};

    // 7-Segment Decoders
    wire [6:0] seg0, seg1, seg2, seg3, seg4, seg5;

    // HEX0 - HEX3: Data Display
    hex7seg_decoder u_dec0 (.hex_digit(disp_data[3:0]),   .blank(1'b0), .seg(seg0));
    hex7seg_decoder u_dec1 (.hex_digit(disp_data[7:4]),   .blank(1'b0), .seg(seg1));
    hex7seg_decoder u_dec2 (.hex_digit(disp_data[11:8]),  .blank(!core_busy), .seg(seg2));
    hex7seg_decoder u_dec3 (.hex_digit(disp_data[15:12]), .blank(!core_busy), .seg(seg3));

    // HEX4 - HEX5: Channel Index Display
    hex7seg_decoder u_dec4 (.hex_digit(disp_channel[3:0]),.blank(1'b0), .seg(seg4));
    hex7seg_decoder u_dec5 (.hex_digit(4'h0),             .blank(1'b0), .seg(seg5));

    assign HEX0 = {1'b1, seg0}; // Decimal point OFF (1'b1)
    assign HEX1 = {1'b1, seg1};
    assign HEX2 = {1'b1, seg2};
    assign HEX3 = {1'b1, seg3};
    assign HEX4 = {1'b1, seg4};
    assign HEX5 = {1'b1, seg5};

    // ========================================================================
    // 7. STATUS LED MAPPING
    // ========================================================================
    assign LEDR[0]   = core_uio_out[0]; // busy
    assign LEDR[1]   = core_uio_out[1]; // done
    assign LEDR[2]   = core_uio_out[2]; // w_dout (serial loopback)
    assign LEDR[3]   = core_uio_out[3]; // any_overflow (sticky alarm)
    assign LEDR[4]   = SW[8];           // Function Mode (0 = Data, 1 = Control)
    assign LEDR[5]   = core_clk;        // Core Clock Monitor
    assign LEDR[9:6] = disp_channel;    // Active Channel Index

    // Tie-off unused core output signals to ensure 0 Verilator warnings
    wire _unused_ok = &{1'b0,
                        core_uio_out[7:4],
                        core_uio_oe,
                        key0_debounced,
                        key0_rel_pulse,
                        key1_press_pulse,
                        key1_rel_pulse,
                        1'b0};

endmodule

`default_nettype wire
