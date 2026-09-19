// ============================================================================
// Module: tt_um_scim_core
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: SkyWater 130nm / IHP SG13G2 (Tiny Tapeout)
// Standard: IEEE 1364-2001 Verilog
// Top-Level Wrapper conforming to Tiny Tapeout pinout specifications
// ============================================================================
// Pedagogical & Silicon Rationale:
//
// 1. Unified Column Delta Reduction Architecture:
//    - Naive implementations require two Wallace trees per column (32 trees total)
//      to separately sum positive and negative PE pulses, exceeding the tile budget.
//    - This core uses the proven mathematical transformation:
//        * Mode 0 (Unipolar):    Δ_col = P_col
//        * Mode 1 (Bipolar):     Δ_col = 2 * X_col - 16
//        * Mode 2 (Hybrid ReLU): Δ_col = 2 * P_col - A
//      where:
//        * P_col / X_col is computed by the column's 16-to-5 Wallace tree.
//        * A = Σ a_i is computed ONCE by a single shared activation Wallace tree
//          and broadcast to all 16 column subtractors.
//      This cuts macro tree count from 32 down to 17, saving ~855 standard cells!
//
// 2. Hardware Guardrails & Strict Synchronous Discipline:
//    - Single synchronous clock domain (posedge clk).
//    - Synchronous active-low reset (rst_n).
//    - No internal clock dividers or unvetted clock gates.
//    - Zero internal tri-states (tri-state pads only on external uio_oe).
//    - No inferred latches: all state transitions and multiplexers are fully
//      specified in combinational / synchronous blocks.
//
// 3. Pinout Budget (Tiny Tapeout 8 in, 8 out, 8 bidir):
//    - ui_in[7:0]:   8-bit Data Bus (Activation bytes & configuration values).
//    - uio_in[7:4]:  Control inputs (w_din, w_shift_en, wr_act, ctrl_strobe).
//    - uio_out[3:0]: Status outputs (busy, done, w_dout loopback, overflow flag).
//    - uio_oe[7:0]:  Pad direction (uio_oe[3:0] = 4'b1111 out, uio_oe[7:4] = 4'b0000 in).
//    - uo_out[7:0]:  8-bit Multiplexed Accumulator Readback Data.
// ============================================================================

`default_nettype none

module tt_um_scim_core #(
    // Stride-15 Galois trajectory seeds (precomputed from x^8 + x^6 + x^5 + x^4 + 1)
    // Channel 0 is LSB byte (bits [7:0]); Channel 15 is MSB byte (bits [127:120]).
    parameter [127:0] SNG_SEEDS = {
        8'hDF, 8'h6A, 8'hBB, 8'hEA,  // Ch 15..12 (Steps 226, 211, 196, 181)
        8'h8F, 8'hCE, 8'h15, 8'hE8,  // Ch 11..8  (Steps 166, 151, 136, 121)
        8'h7C, 8'h61, 8'hD6, 8'hF4,  // Ch 7..4   (Steps 106,  91,  76,  61)
        8'h0A, 8'hAC, 8'hF1, 8'h5C   // Ch 3..0   (Steps  46,  31,  16,   1)
    }
)(
    input  wire [7:0] ui_in,              // Dedicated inputs: 8-bit Data / Config bus
    output wire [7:0] uo_out,             // Dedicated outputs: 8-bit Accumulator readback
    input  wire [7:0] uio_in,             // IOs: Input path
    output wire [7:0] uio_out,            // IOs: Output path
    output wire [7:0] uio_oe,             // IOs: Enable path (1=output, 0=input)
    input  wire       ena,                // Design enable (always 1 when powered)
    input  wire       clk,                // Master clock
    input  wire       rst_n               // Synchronous active-low reset
);

    // ========================================================================
    // 1. PINOUT MAPPING & BIDIRECTIONAL PAD DIRECTIONS
    // ========================================================================
    // uio[3:0] configured as outputs; uio[7:4] configured as inputs
    assign uio_oe = 8'b0000_1111;

    wire w_din       = uio_in[4];         // Serial weight input
    wire w_shift_en  = uio_in[5];         // Serial weight shift enable
    wire wr_act      = uio_in[6];         // Activation register write strobe
    wire ctrl_strobe = uio_in[7];         // Control / Command strobe

    // Tie off unused top-level signals to prevent lint warnings
    wire _unused_top_signals = &{ena, uio_in[3:0], 1'b0};

    wire w_dout;                          // Serial weight output for DFT loopback
    reg  busy;                            // Compute phase active
    reg  done;                            // Compute phase complete
    wire any_overflow;                    // OR reduction of all 16 sat_flags

    assign uio_out[0] = busy;
    assign uio_out[1] = done;
    assign uio_out[2] = w_dout;
    assign uio_out[3] = any_overflow;
    assign uio_out[7:4] = 4'b0000;

    // ========================================================================
    // 2. CONTROL REGISTERS & FSM
    // ========================================================================
    reg [3:0] addr;                       // Channel/Column address [0..15]
    reg [1:0] mode;                       // 0: Unipolar, 1: Bipolar, 2: Hybrid ReLU
    reg       byte_sel;                   // 0: Acc lower byte [7:0], 1: upper byte [12:8]

    // 16x 8-bit activation storage registers (128 bits total)
    reg [7:0] act_regs [15:0];

    // FSM States
    localparam FSM_IDLE    = 2'b00;
    localparam FSM_CLEAR   = 2'b01;
    localparam FSM_COMPUTE = 2'b10;
    localparam FSM_DONE    = 2'b11;

    reg [1:0] state;
    reg [7:0] cycle_cnt;                  // 0 to 255 (256 cycles)
    reg       acc_clr;                    // Pulse to clear accumulators
    reg       acc_en;                     // Accumulator clock enable
    reg       sng_en;                     // SNG LFSR step enable
    reg       start_req;                  // Compute start trigger

    integer k;

    always @(posedge clk) begin
        if (!rst_n) begin
            addr      <= 4'd0;
            mode      <= 2'b00;
            byte_sel  <= 1'b0;
            start_req <= 1'b0;
            for (k = 0; k < 16; k = k + 1) begin
                act_regs[k] <= 8'd0;
            end
        end else begin
            // Default: clear single-cycle start pulse
            start_req <= 1'b0;

            // Handle Control Strobe (Command write)
            if (ctrl_strobe && !busy) begin
                addr      <= ui_in[3:0];
                mode      <= ui_in[5:4];
                byte_sel  <= ui_in[6];
                start_req <= ui_in[7];
            end

            // Handle Activation Write Strobe
            if (wr_act && !busy) begin
                act_regs[addr] <= ui_in;
                // Auto-increment address to simplify sequential loading
                addr <= addr + 4'd1;
            end
        end
    end

    // FSM Compute Controller
    always @(posedge clk) begin
        if (!rst_n) begin
            state     <= FSM_IDLE;
            cycle_cnt <= 8'd0;
            busy      <= 1'b0;
            done      <= 1'b0;
            acc_clr   <= 1'b0;
            acc_en    <= 1'b0;
            sng_en    <= 1'b0;
        end else begin
            case (state)
                FSM_IDLE: begin
                    acc_clr <= 1'b0;
                    acc_en  <= 1'b0;
                    sng_en  <= 1'b0;
                    busy    <= 1'b0;
                    if (start_req) begin
                        state   <= FSM_CLEAR;
                        busy    <= 1'b1;
                        done    <= 1'b0;
                        acc_clr <= 1'b1;  // Synchronous clear accumulators
                    end
                end

                FSM_CLEAR: begin
                    // 1 cycle in clear state to zero accumulator registers
                    acc_clr   <= 1'b0;
                    acc_en    <= 1'b1;    // Enable accumulation
                    sng_en    <= 1'b1;    // Enable SNG progression
                    cycle_cnt <= 8'd0;
                    state     <= FSM_COMPUTE;
                end

                FSM_COMPUTE: begin
                    // Step SNG and Accumulate for exactly 256 cycles (0..255)
                    if (cycle_cnt == 8'd255) begin
                        acc_en <= 1'b0;
                        sng_en <= 1'b0;
                        busy   <= 1'b0;
                        done   <= 1'b1;
                        state  <= FSM_DONE;
                    end else begin
                        cycle_cnt <= cycle_cnt + 8'd1;
                    end
                end

                FSM_DONE: begin
                    acc_en <= 1'b0;
                    sng_en <= 1'b0;
                    busy   <= 1'b0;
                    done   <= 1'b1;
                    if (start_req) begin
                        state   <= FSM_CLEAR;
                        busy    <= 1'b1;
                        done    <= 1'b0;
                        acc_clr <= 1'b1;
                    end
                end

                default: begin
                    state <= FSM_IDLE;
                end
            endcase
        end
    end

    // Flatten activation registers for SNG bank
    wire [127:0] act_bus;
    genvar a_i;
    generate
        for (a_i = 0; a_i < 16; a_i = a_i + 1) begin : gen_act_bus
            assign act_bus[a_i*8 +: 8] = act_regs[a_i];
        end
    endgenerate

    // ========================================================================
    // 3. WEIGHT MEMORY (256-Bit Shift Register)
    // ========================================================================
    wire [255:0] weight_matrix;

    scim_weight_mem u_weight_mem (
        .clk(clk),
        .rst_n(rst_n),
        .w_shift_en(w_shift_en),
        .w_din(w_din),
        .w_dout(w_dout),
        .weights_out(weight_matrix)
    );

    // ========================================================================
    // 4. STOCHASTIC NUMBER GENERATOR (SNG) BANK
    // ========================================================================
    wire [15:0] sng_activations;

    scim_sng_bank #(
        .SNG_SEEDS(SNG_SEEDS)
    ) u_sng_bank (
        .clk(clk),
        .rst_n(rst_n),
        .en(sng_en),
        .act_in(act_bus),
        .sng_out(sng_activations)
    );

    // ========================================================================
    // 5. CENTRAL SHARED ACTIVATION WALLACE TREE (A = Σ a_i)
    // ========================================================================
    // A is identical across all 16 columns! Computed ONCE centrally.
    wire [4:0] shared_act_sum;

    scim_wallace_tree u_shared_act_tree (
        .in_bits(sng_activations),
        .count(shared_act_sum)
    );

    // ========================================================================
    // 6. 16x16 PROCESSING ELEMENT ARRAY & COLUMN REDUCTION
    // ========================================================================
    wire [15:0] pe_col_out [15:0];        // pe_col_out[col][row]
    wire [4:0]  col_sum    [15:0];        // 16-to-5 tree output for each column
    wire signed [5:0] col_delta [15:0];   // Single-cycle signed delta [-16..+16]

    genvar col, row;
    generate
        for (col = 0; col < 16; col = col + 1) begin : gen_columns
            // Instantiate 16 PEs for this column
            for (row = 0; row < 16; row = row + 1) begin : gen_pes
                // Weight mapping: row i, column col
                wire w_cell = weight_matrix[row*16 + col];
                scim_pe u_pe (
                    .a_bit(sng_activations[row]),
                    .w_bit(w_cell),
                    .mode(mode),
                    .pe_out(pe_col_out[col][row])
                );
            end

            // Column 16-to-5 Wallace Tree Compressor
            scim_wallace_tree u_col_tree (
                .in_bits(pe_col_out[col]),
                .count(col_sum[col])
            );

            // Column Delta Arithmetic:
            // Mode 0 (Unipolar):    Δ = P                (Range [0, 16])
            // Mode 1 (Bipolar):     Δ = 2X - 16          (Range [-16, +16])
            // Mode 2 (Hybrid ReLU): Δ = 2P - A           (Range [-16, +16])
            // Where 2*P is implemented as a hardwired 1-bit shift {col_sum, 1'b0}
            wire signed [5:0] delta_mode0 = $signed({1'b0, col_sum[col]});
            wire signed [5:0] delta_mode1 = $signed({col_sum[col], 1'b0}) - 6'sd16;
            wire signed [5:0] delta_mode2 = $signed({col_sum[col], 1'b0}) - $signed({1'b0, shared_act_sum});

            assign col_delta[col] = (mode == 2'b00) ? delta_mode0 :
                                    (mode == 2'b01) ? delta_mode1 : delta_mode2;
        end
    endgenerate

    // ========================================================================
    // 7. 16x 13-BIT ACCUMULATORS
    // ========================================================================
    wire signed [12:0] acc_val [15:0];
    wire [15:0] sat_flags;

    genvar c_acc;
    generate
        for (c_acc = 0; c_acc < 16; c_acc = c_acc + 1) begin : gen_accumulators
            scim_accumulator #(.WIDTH(13)) u_acc (
                .clk(clk),
                .rst_n(rst_n),
                .clr(acc_clr),
                .en(acc_en),
                .delta(col_delta[c_acc]),
                .acc_val(acc_val[c_acc]),
                .sat_flag(sat_flags[c_acc])
            );
        end
    endgenerate

    assign any_overflow = |sat_flags;

    // ========================================================================
    // 8. ACCUMULATOR READBACK MULTIPLEXER (uo_out[7:0])
    // ========================================================================
    // Multiplexes 16 columns based on 'addr' and 'byte_sel'
    wire signed [12:0] selected_acc = acc_val[addr];

    // byte_sel == 0: Lower 8 bits [7:0]
    // byte_sel == 1: Sign-extended upper bits {{3{sign}}, [12:8]}
    wire [7:0] acc_byte_low  = selected_acc[7:0];
    wire [7:0] acc_byte_high = {{3{selected_acc[12]}}, selected_acc[12:8]};

    assign uo_out = (byte_sel) ? acc_byte_high : acc_byte_low;

endmodule

`default_nettype wire
