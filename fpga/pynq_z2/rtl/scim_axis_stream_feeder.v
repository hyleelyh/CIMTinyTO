// ============================================================================
// Module: scim_axis_stream_feeder
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) FPGA Emulation (Pillar 6.1 - Tier 3)
// Standard: IEEE 1364-2001 Verilog
// Description: AMBA AXI4-Stream Autonomous Feeder FSM wrapping tt_um_scim_core.
// ============================================================================
// Pedagogical & Silicon Rationale:
//
// 1. Autonomous Hardware Line-Rate Streaming:
//    - Replaces CPU-polled MMIO loops with a hardware FSM operating at 50 MHz.
//    - Decodes incoming 32-bit AXI-Stream packets from DMA MM2S and drives the
//      underlying ASIC core's activation registers and control strobes directly.
//
// 2. High-Performance Batching Protocol:
//    - CMD_LOAD_WEIGHTS (0x01): Shifts 256 bits into stationary DFF memory.
//    - CMD_MVM_SINGLE   (0x02): Feeds 16 activation bytes, executes 256-cycle MVM,
//                               streams 16 accumulators back with TLAST=1.
//    - CMD_MVM_BATCH    (0x03): Streams N tiles back-to-back at wire speed without
//                               software intervention. TLAST asserted on final word.
//
// 3. Cycle-Accurate Latency (50 MHz, T_clk = 20 ns):
//    - Activation Load: 16 cycles = 320 ns
//    - Start Strobe:     1 cycle  =  20 ns
//    - Stochastic Core: 256 cycles = 5,120 ns (5.12 us)
//    - Readback Multiplex: 32 cycles = 640 ns
//    - Stream Output:    8 cycles = 160 ns
//    - Total Tile Latency: ~313 cycles = 6.26 us -> 44.6 FPS sustained line rate!
// ============================================================================

`default_nettype none

module scim_axis_stream_feeder #(
    parameter integer C_AXIS_DATA_WIDTH = 32
)(
    // Global Clock & Synchronous Reset
    input  wire                             aclk,
    input  wire                             aresetn,

    // AXI4-Stream Slave Interface (MM2S: From Host DDR to Accelerator)
    input  wire [C_AXIS_DATA_WIDTH-1:0]     s_axis_tdata,
    input  wire                             s_axis_tvalid,
    output reg                              s_axis_tready,
    input  wire                             s_axis_tlast,

    // AXI4-Stream Master Interface (S2MM: From Accelerator to Host DDR)
    output reg  [C_AXIS_DATA_WIDTH-1:0]     m_axis_tdata,
    output reg                              m_axis_tvalid,
    input  wire                             m_axis_tready,
    output wire                             m_axis_tlast,

    // External PMOD Hardware Snooping Breakout (for Logic Analyzers)
    output wire [7:0]                       pmod_a,
    output wire [7:0]                       pmod_b
);

    // Suppress unused signal warnings
    wire _unused_tlast = s_axis_tlast;

    // ========================================================================
    // 1. PACKET PROTOCOL COMMAND DEFINITIONS
    // ========================================================================
    localparam [7:0] CMD_LOAD_WEIGHTS = 8'h01;
    localparam [7:0] CMD_MVM_SINGLE   = 8'h02;
    localparam [7:0] CMD_MVM_BATCH    = 8'h03;

    // ========================================================================
    // 2. FSM STATE DEFINITIONS
    // ========================================================================
    localparam [3:0] ST_IDLE          = 4'd0;
    localparam [3:0] ST_WEIGHT_WORD   = 4'd1;
    localparam [3:0] ST_WEIGHT_SHIFT  = 4'd2;
    localparam [3:0] ST_ACT_WORD      = 4'd3;
    localparam [3:0] ST_ACT_BYTE      = 4'd4;
    localparam [3:0] ST_START_MVM     = 4'd5;
    localparam [3:0] ST_WAIT_COMPUTE  = 4'd6;
    localparam [3:0] ST_STROBE_LOW    = 4'd7;
    localparam [3:0] ST_LATCH_LOW     = 4'd8;
    localparam [3:0] ST_STROBE_HIGH   = 4'd9;
    localparam [3:0] ST_LATCH_HIGH    = 4'd10;
    localparam [3:0] ST_STREAM_OUT    = 4'd11;

    reg [3:0]  state;
    reg [7:0]  pkt_cmd;
    reg [15:0] batch_tiles_rem;
    reg        is_batch;

    // Weight Shifting Registers
    reg [31:0] shift_reg;
    reg [2:0]  weight_word_idx; // 0..7 (8 words = 256 bits)
    reg [4:0]  bit_shift_cnt;   // 0..31

    // Activation Loading Registers
    reg [1:0]  act_word_idx;    // 0..3 (4 words = 16 bytes)
    reg [1:0]  act_byte_idx;    // 0..3 (4 bytes per 32-bit word)
    reg [31:0] act_latch_word;

    // Readback Accumulator Storage
    reg [7:0]  acc_low_byte;
    reg [15:0] acc_results [15:0];
    reg [3:0]  read_col_idx;    // 0..15 columns
    reg [2:0]  out_word_idx;    // 0..7 output words

    // Frozen Core Signals
    reg  [7:0] core_ui_in;
    wire [7:0] core_uo_out;
    reg        core_ctrl_strobe;
    reg        core_wr_act;
    reg        core_w_shift_en;
    reg        core_w_din;
    wire [7:0] core_uio_in = {core_ctrl_strobe, core_wr_act, core_w_shift_en, core_w_din, 4'b0000};
    wire [7:0] core_uio_out;
    wire [7:0] core_uio_oe;

    wire core_busy = core_uio_out[0];
    wire core_done = core_uio_out[1];

    // Tie-off unused signals
    wire _unused_core = &{1'b0, core_uio_out[7:2], core_uio_oe, _unused_tlast, pkt_cmd, 1'b0};

    // ========================================================================
    // 3. MAIN HARDWARE STREAMING FINITE STATE MACHINE (FSM)
    // ========================================================================
    integer i;

    always @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            state            <= ST_IDLE;
            s_axis_tready    <= 1'b0;
            m_axis_tvalid    <= 1'b0;
            pkt_cmd          <= 8'd0;
            batch_tiles_rem  <= 16'd0;
            is_batch         <= 1'b0;
            weight_word_idx  <= 3'd0;
            bit_shift_cnt    <= 5'd0;
            shift_reg        <= 32'd0;
            act_word_idx     <= 2'd0;
            act_byte_idx     <= 2'd0;
            act_latch_word   <= 32'd0;
            read_col_idx     <= 4'd0;
            out_word_idx     <= 3'd0;
            acc_low_byte     <= 8'd0;
            core_ui_in       <= 8'd0;
            core_ctrl_strobe <= 1'b0;
            core_wr_act      <= 1'b0;
            core_w_shift_en  <= 1'b0;
            core_w_din       <= 1'b0;
            for (i = 0; i < 16; i = i + 1) begin
                acc_results[i] <= 16'd0;
            end
        end else begin
            // Defaults: single-cycle pulses reset every clock
            core_ctrl_strobe <= 1'b0;
            core_wr_act      <= 1'b0;
            core_w_shift_en  <= 1'b0;

            case (state)
                // ------------------------------------------------------------
                // State 0: Wait for Command Packet Header
                // ------------------------------------------------------------
                ST_IDLE: begin
                    s_axis_tready <= 1'b1;
                    m_axis_tvalid <= 1'b0;

                    if (s_axis_tvalid && s_axis_tready) begin
                        pkt_cmd <= s_axis_tdata[31:24];

                        case (s_axis_tdata[31:24])
                            CMD_LOAD_WEIGHTS: begin
                                weight_word_idx <= 3'd0;
                                s_axis_tready   <= 1'b1;
                                state           <= ST_WEIGHT_WORD;
                            end

                            CMD_MVM_SINGLE: begin
                                is_batch        <= 1'b0;
                                batch_tiles_rem <= 16'd1;
                                act_word_idx    <= 2'd0;
                                act_byte_idx    <= 2'd0;
                                // Reset activation address in core to 0
                                core_ui_in       <= 8'h00; // addr = 0
                                core_ctrl_strobe <= 1'b1;
                                s_axis_tready    <= 1'b1;
                                state            <= ST_ACT_WORD;
                            end

                            CMD_MVM_BATCH: begin
                                is_batch        <= 1'b1;
                                batch_tiles_rem <= s_axis_tdata[15:0];
                                act_word_idx    <= 2'd0;
                                act_byte_idx    <= 2'd0;
                                // Reset activation address in core to 0
                                core_ui_in       <= 8'h00; // addr = 0
                                core_ctrl_strobe <= 1'b1;
                                s_axis_tready    <= 1'b1;
                                state            <= ST_ACT_WORD;
                            end

                            default: begin
                                // Invalid header, stay in IDLE
                                state <= ST_IDLE;
                            end
                        endcase
                    end
                end

                // ------------------------------------------------------------
                // State 1: Receive 32-bit Weight Word from Stream
                // ------------------------------------------------------------
                ST_WEIGHT_WORD: begin
                    s_axis_tready <= 1'b1;
                    if (s_axis_tvalid && s_axis_tready) begin
                        shift_reg     <= s_axis_tdata;
                        bit_shift_cnt <= 5'd0;
                        s_axis_tready <= 1'b0; // Halt stream while shifting 32 bits
                        state         <= ST_WEIGHT_SHIFT;
                    end
                end

                // ------------------------------------------------------------
                // State 2: Serial Shift 32 bits into DFF Weight Memory
                // ------------------------------------------------------------
                ST_WEIGHT_SHIFT: begin
                    core_w_din      <= shift_reg[0];
                    core_w_shift_en <= 1'b1;
                    shift_reg       <= {1'b0, shift_reg[31:1]};
                    bit_shift_cnt   <= bit_shift_cnt + 5'd1;

                    if (bit_shift_cnt == 5'd31) begin
                        if (weight_word_idx == 3'd7) begin
                            // All 8 words (256 bits) shifted! Return to IDLE
                            s_axis_tready <= 1'b1;
                            state         <= ST_IDLE;
                        end else begin
                            weight_word_idx <= weight_word_idx + 3'd1;
                            s_axis_tready   <= 1'b1;
                            state           <= ST_WEIGHT_WORD;
                        end
                    end
                end

                // ------------------------------------------------------------
                // State 3: Receive 32-bit Activation Word (4 Bytes)
                // ------------------------------------------------------------
                ST_ACT_WORD: begin
                    s_axis_tready <= 1'b1;
                    if (s_axis_tvalid && s_axis_tready) begin
                        act_latch_word <= s_axis_tdata;
                        act_byte_idx   <= 2'd0;
                        s_axis_tready  <= 1'b0; // Deassert during 4-byte unpacking
                        state          <= ST_ACT_BYTE;
                    end
                end

                // ------------------------------------------------------------
                // State 4: Unpack & Pulse wr_act for each byte sequentially
                // ------------------------------------------------------------
                ST_ACT_BYTE: begin
                    case (act_byte_idx)
                        2'd0: core_ui_in <= act_latch_word[7:0];
                        2'd1: core_ui_in <= act_latch_word[15:8];
                        2'd2: core_ui_in <= act_latch_word[23:16];
                        2'd3: core_ui_in <= act_latch_word[31:24];
                    endcase
                    core_wr_act <= 1'b1; // Auto-increments address in core!

                    if (act_byte_idx == 2'd3) begin
                        if (act_word_idx == 2'd3) begin
                            // All 16 bytes loaded! Trigger MVM
                            state <= ST_START_MVM;
                        end else begin
                            act_word_idx  <= act_word_idx + 2'd1;
                            s_axis_tready <= 1'b1;
                            state         <= ST_ACT_WORD;
                        end
                    end else begin
                        act_byte_idx <= act_byte_idx + 2'd1;
                    end
                end

                // ------------------------------------------------------------
                // State 5: Trigger Mode 1 Hybrid ReLU Computation
                // ------------------------------------------------------------
                ST_START_MVM: begin
                    // ui_in[7] = 1 (start_req), ui_in[4] = 1 (Mode 1), addr = 0
                    core_ui_in       <= 8'h90;
                    core_ctrl_strobe <= 1'b1;
                    state            <= ST_WAIT_COMPUTE;
                end

                // ------------------------------------------------------------
                // State 6: Wait 256 Cycles for Stochastic MVM to Complete
                // ------------------------------------------------------------
                ST_WAIT_COMPUTE: begin
                    // Core asserts busy for 256 cycles then raises done
                    if (core_done && !core_busy) begin
                        read_col_idx     <= 4'd0;
                        // Prepare address for column 0, byte_sel = 0 (low byte)
                        core_ui_in       <= {1'b0, 1'b0, 2'b00, 4'd0};
                        core_ctrl_strobe <= 1'b1;
                        state            <= ST_STROBE_LOW;
                    end
                end

                // ------------------------------------------------------------
                // State 7: Strobe Low Byte into Core
                // ------------------------------------------------------------
                ST_STROBE_LOW: begin
                    // Core latches addr & byte_sel=0 at the upcoming posedge
                    core_ctrl_strobe <= 1'b0;
                    state            <= ST_LATCH_LOW;
                end

                // ------------------------------------------------------------
                // State 8: Latch Low Byte from Core uo_out & Strobe High Byte
                // ------------------------------------------------------------
                ST_LATCH_LOW: begin
                    // Core's uo_out is now stable low byte
                    acc_low_byte     <= core_uo_out;
                    // Prepare high byte strobe
                    core_ui_in       <= {1'b0, 1'b1, 2'b00, read_col_idx};
                    core_ctrl_strobe <= 1'b1;
                    state            <= ST_STROBE_HIGH;
                end

                // ------------------------------------------------------------
                // State 9: Strobe High Byte into Core
                // ------------------------------------------------------------
                ST_STROBE_HIGH: begin
                    // Core latches addr & byte_sel=1 at the upcoming posedge
                    core_ctrl_strobe <= 1'b0;
                    state            <= ST_LATCH_HIGH;
                end

                // ------------------------------------------------------------
                // State 10: Latch High Byte & Reconstruct 16-bit Signed Value
                // ------------------------------------------------------------
                ST_LATCH_HIGH: begin
                    // Core's uo_out is now stable high byte
                    acc_results[read_col_idx] <= {core_uo_out, acc_low_byte};

                    if (read_col_idx == 4'd15) begin
                        out_word_idx  <= 3'd0;
                        m_axis_tvalid <= 1'b1;
                        state         <= ST_STREAM_OUT;
                    end else begin
                        read_col_idx     <= read_col_idx + 4'd1;
                        // Strobe low byte of next column
                        core_ui_in       <= {1'b0, 1'b0, 2'b00, read_col_idx + 4'd1};
                        core_ctrl_strobe <= 1'b1;
                        state            <= ST_STROBE_LOW;
                    end
                end

                // ------------------------------------------------------------
                // State 9: Stream 8x 32-bit Words (16 Accumulators) to DMA S2MM
                // ------------------------------------------------------------
                ST_STREAM_OUT: begin
                    // Handshake on stream transfer
                    if (m_axis_tvalid && m_axis_tready) begin
                        if (out_word_idx == 3'd7) begin
                            m_axis_tvalid <= 1'b0;

                            if (is_batch && (batch_tiles_rem > 16'd1)) begin
                                // More tiles in this DMA burst!
                                batch_tiles_rem  <= batch_tiles_rem - 16'd1;
                                act_word_idx     <= 2'd0;
                                act_byte_idx     <= 2'd0;
                                // Reset activation address in core to 0
                                core_ui_in       <= 8'h00;
                                core_ctrl_strobe <= 1'b1;
                                s_axis_tready    <= 1'b1;
                                state            <= ST_ACT_WORD;
                            end else begin
                                // Completed! Return to IDLE
                                s_axis_tready <= 1'b1;
                                state         <= ST_IDLE;
                            end
                        end else begin
                            out_word_idx <= out_word_idx + 3'd1;
                        end
                    end
                end

                default: begin
                    state <= ST_IDLE;
                end
            endcase
        end
    end

    // ========================================================================
    // 4. INSTANTIATION OF FROZEN ASIC CORE
    // ========================================================================
    tt_um_scim_core u_scim_core (
        .ui_in   (core_ui_in),
        .uo_out  (core_uo_out),
        .uio_in  (core_uio_in),
        .uio_out (core_uio_out),
        .uio_oe  (core_uio_oe),
        .ena     (1'b1),
        .clk     (aclk),
        .rst_n   (aresetn)
    );

    // Combinational stream multiplexer: out_word_idx selects which accumulator pair to drive
    always @(*) begin
        case (out_word_idx)
            3'd0: m_axis_tdata = {acc_results[1],  acc_results[0]};
            3'd1: m_axis_tdata = {acc_results[3],  acc_results[2]};
            3'd2: m_axis_tdata = {acc_results[5],  acc_results[4]};
            3'd3: m_axis_tdata = {acc_results[7],  acc_results[6]};
            3'd4: m_axis_tdata = {acc_results[9],  acc_results[8]};
            3'd5: m_axis_tdata = {acc_results[11], acc_results[10]};
            3'd6: m_axis_tdata = {acc_results[13], acc_results[12]};
            3'd7: m_axis_tdata = {acc_results[15], acc_results[14]};
            default: m_axis_tdata = 32'd0;
        endcase
    end

    // Continuous AXI-Stream TLAST Generation (asserted on final word of final tile)
    assign m_axis_tlast = (state == ST_STREAM_OUT) && (out_word_idx == 3'd7) && (batch_tiles_rem <= 16'd1);

    // ========================================================================
    // 5. EXTERNAL PMOD SNOOPING BREAKOUT
    // ========================================================================
    assign pmod_a = core_uo_out;
    assign pmod_b[0] = aclk;
    assign pmod_b[1] = aresetn;
    assign pmod_b[2] = core_busy;
    assign pmod_b[3] = core_done;
    assign pmod_b[4] = core_uio_out[2]; // w_dout
    assign pmod_b[5] = core_uio_out[3]; // any_overflow
    assign pmod_b[6] = core_ctrl_strobe;
    assign pmod_b[7] = core_wr_act;

endmodule

`default_nettype wire
