// ============================================================================
// Module: tt_scim_axi_wrapper
// Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
// Target: Xilinx Zynq-7020 (PYNQ-Z2) FPGA Emulation (Pillar 6)
// Standard: IEEE 1364-2001 Verilog
// Description: AMBA AXI4-Lite 32-bit slave MMIO bridge wrapping tt_um_scim_core.
// ============================================================================
// Pedagogical & Silicon Rationale:
//
// 1. Zero-Deadlock Single-Cycle AXI4-Lite Handshake:
//    - Both AWREADY and WREADY assert simultaneously with BVALID on matching
//      request, completing the write in a single deterministic cycle.
//    - Single-cycle read response with zero wait-states.
//
// 2. Guaranteed Single-Cycle Synchronous Pulse:
//    - In free-running mode (clk_mode = 0 @ 50 MHz), strobe signals (wr_act,
//      ctrl_strobe, w_shift_en) are active for EXACTLY ONE clock cycle,
//      guaranteeing 1 shift per write and 1 strobe per write without race conditions.
//    - In single-step mode (clk_mode = 1), level signals are driven directly
//      and advanced cycle-by-cycle via REG_STEP_PULSE writes.
//
// 3. Cycle Latency Counter:
//    - Hardware timer starts on core busy assertion and freezes on done assertion,
//      reporting precise hardware cycle counts in REG_STATUS[31:16].
//
// 4. External PMOD Snooping Breakout:
//    - Routes all 24 Tiny Tapeout pins to PMOD connectors for logic analyzer verification.
// ============================================================================

`default_nettype none

module tt_scim_axi_wrapper #(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 6
)(
    // AXI4-Lite Clock and Active-Low Synchronous Reset
    input  wire                                  s_axi_aclk,
    input  wire                                  s_axi_aresetn,

    // AXI4-Lite Write Address Channel
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]        s_axi_awaddr,
    input  wire [2:0]                            s_axi_awprot,
    input  wire                                  s_axi_awvalid,
    output reg                                   s_axi_awready,

    // AXI4-Lite Write Data Channel
    input  wire [C_S_AXI_DATA_WIDTH-1:0]        s_axi_wdata,
    input  wire [(C_S_AXI_DATA_WIDTH/8)-1:0]    s_axi_wstrb,
    input  wire                                  s_axi_wvalid,
    output reg                                   s_axi_wready,

    // AXI4-Lite Write Response Channel
    output reg  [1:0]                            s_axi_bresp,
    output reg                                   s_axi_bvalid,
    input  wire                                  s_axi_bready,

    // AXI4-Lite Read Address Channel
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]        s_axi_araddr,
    input  wire [2:0]                            s_axi_arprot,
    input  wire                                  s_axi_arvalid,
    output reg                                   s_axi_arready,

    // AXI4-Lite Read Data Channel
    output reg  [C_S_AXI_DATA_WIDTH-1:0]        s_axi_rdata,
    output reg  [1:0]                            s_axi_rresp,
    output reg                                   s_axi_rvalid,
    input  wire                                  s_axi_rready,

    // External High-Speed PLL Clock Input (optional)
    input  wire                                  ext_pll_clk,

    // Physical Hardware PMOD Snooping Breakout (for DSLogic / Saleae Logic Analyzers)
    output wire [7:0]                            pmod_a, // uo_out[7:0] accumulator readback byte
    output wire [7:0]                            pmod_b  // [0]=clk, [1]=rst_n, [2]=busy, [3]=done, [4]=w_dout, [5]=ovf, [6]=ctrl_strobe, [7]=wr_act
);

    // Suppress unused AXI signals warnings
    wire _unused_axi = &{s_axi_awprot, s_axi_arprot, s_axi_wstrb, ext_pll_clk, 1'b0};

    // ========================================================================
    // 1. REGISTER ADDRESS MAP (32-Bit Word Offsets)
    // ========================================================================
    localparam [C_S_AXI_ADDR_WIDTH-1:0] ADDR_REG_CTRL       = 6'h00; // 0x00: Control register
    localparam [C_S_AXI_ADDR_WIDTH-1:0] ADDR_REG_DATA_IN    = 6'h04; // 0x04: ui_in data register
    localparam [C_S_AXI_ADDR_WIDTH-1:0] ADDR_REG_STATUS     = 6'h08; // 0x08: Status & cycle counter
    localparam [C_S_AXI_ADDR_WIDTH-1:0] ADDR_REG_DATA_OUT   = 6'h0C; // 0x0C: uo_out readback
    localparam [C_S_AXI_ADDR_WIDTH-1:0] ADDR_REG_STEP_PULSE = 6'h10; // 0x10: Software single-step strobe

    // Internal MMIO Static Registers
    reg [7:0] reg_ctrl;
    reg [7:0] reg_data_in;
    reg       soft_clk_reg;

    // Single-cycle synchronous strobes
    reg       wr_act_pulse;
    reg       ctrl_strobe_pulse;
    reg       w_shift_pulse;

    // ========================================================================
    // 2. DUAL-MODE CLOCK GENERATION & MULTIPLEXING
    // ========================================================================
    wire clk_mode   = reg_ctrl[2];
    wire free_clk   = s_axi_aclk;
    wire core_clk   = (clk_mode) ? soft_clk_reg : free_clk;
    wire core_rst_n = reg_ctrl[0];
    wire core_ena   = reg_ctrl[1];

    // In single-step mode (clk_mode = 1), use direct level from reg_ctrl
    // In free-running mode (clk_mode = 0), use guaranteed single-cycle pulse
    wire core_wr_act      = (clk_mode) ? reg_ctrl[6] : wr_act_pulse;
    wire core_ctrl_strobe = (clk_mode) ? reg_ctrl[7] : ctrl_strobe_pulse;
    wire core_w_shift_en  = (clk_mode) ? reg_ctrl[5] : w_shift_pulse;
    wire core_w_din       = reg_ctrl[4];

    wire [7:0] core_ui_in  = reg_data_in;
    wire [7:0] core_uio_in = {core_ctrl_strobe, core_wr_act, core_w_shift_en, core_w_din, 4'b0000};
    wire [7:0] core_uo_out;
    wire [7:0] core_uio_out;
    wire [7:0] core_uio_oe;

    // Tie-off unused signals to eliminate Verilator lint warnings
    wire _unused_ok = &{1'b0,
                        s_axi_wdata[31:10],
                        core_uio_out[7:4],
                        core_uio_oe,
                        1'b0};

    // ========================================================================
    // 3. CYCLE LATENCY COUNTER
    // ========================================================================
    reg [15:0] latency_cnt;

    always @(posedge core_clk or negedge core_rst_n) begin
        if (!core_rst_n) begin
            latency_cnt <= 16'd0;
        end else begin
            if (core_uio_out[0]) begin
                // Increment during active computation
                latency_cnt <= latency_cnt + 16'd1;
            end else if (core_ctrl_strobe) begin
                // Reset counter on command strobe
                latency_cnt <= 16'd0;
            end
        end
    end

    // ========================================================================
    // 4. AXI4-LITE WRITE CHANNEL
    // ========================================================================
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            s_axi_awready     <= 1'b0;
            s_axi_wready      <= 1'b0;
            s_axi_bvalid      <= 1'b0;
            s_axi_bresp       <= 2'b00;
            reg_ctrl          <= 8'h03; // rst_n=1, ena=1
            reg_data_in       <= 8'h00;
            soft_clk_reg      <= 1'b0;
            wr_act_pulse      <= 1'b0;
            ctrl_strobe_pulse <= 1'b0;
            w_shift_pulse     <= 1'b0;
        end else begin
            // Default: clear single-cycle strobes every clock
            wr_act_pulse      <= 1'b0;
            ctrl_strobe_pulse <= 1'b0;
            w_shift_pulse     <= 1'b0;

            // Single-cycle write acceptance
            if (!s_axi_bvalid && s_axi_awvalid && s_axi_wvalid && !s_axi_awready) begin
                s_axi_awready <= 1'b1;
                s_axi_wready  <= 1'b1;
                s_axi_bvalid  <= 1'b1;
                s_axi_bresp   <= 2'b00; // OKAY

                case (s_axi_awaddr[C_S_AXI_ADDR_WIDTH-1:0])
                    ADDR_REG_CTRL: begin
                        reg_ctrl          <= s_axi_wdata[7:0];
                        ctrl_strobe_pulse <= s_axi_wdata[7];
                        wr_act_pulse      <= s_axi_wdata[6];
                        w_shift_pulse     <= s_axi_wdata[5];
                    end
                    ADDR_REG_DATA_IN: begin
                        reg_data_in       <= s_axi_wdata[7:0];
                        wr_act_pulse      <= s_axi_wdata[8];
                        ctrl_strobe_pulse <= s_axi_wdata[9];
                    end
                    ADDR_REG_STEP_PULSE: begin
                        soft_clk_reg <= ~soft_clk_reg;
                    end
                    default: begin
                        // No-op
                    end
                endcase
            end else begin
                s_axi_awready <= 1'b0;
                s_axi_wready  <= 1'b0;
            end

            // Clear response handshake
            if (s_axi_bvalid && s_axi_bready) begin
                s_axi_bvalid <= 1'b0;
            end
        end
    end

    // ========================================================================
    // 5. AXI4-LITE READ CHANNEL
    // ========================================================================
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            s_axi_arready <= 1'b0;
            s_axi_rvalid  <= 1'b0;
            s_axi_rresp   <= 2'b00;
            s_axi_rdata   <= {C_S_AXI_DATA_WIDTH{1'b0}};
        end else begin
            if (!s_axi_rvalid && s_axi_arvalid && !s_axi_arready) begin
                s_axi_arready <= 1'b1;
                s_axi_rvalid  <= 1'b1;
                s_axi_rresp   <= 2'b00;

                case (s_axi_araddr[C_S_AXI_ADDR_WIDTH-1:0])
                    ADDR_REG_CTRL: begin
                        s_axi_rdata <= {24'd0, reg_ctrl};
                    end
                    ADDR_REG_DATA_IN: begin
                        s_axi_rdata <= {24'd0, reg_data_in};
                    end
                    ADDR_REG_STATUS: begin
                        // bit[0]: busy (uio_out[0])
                        // bit[1]: done (uio_out[1])
                        // bit[2]: w_dout (uio_out[2])
                        // bit[3]: any_overflow (uio_out[3])
                        // bits[31:16]: latency cycle counter
                        s_axi_rdata <= {latency_cnt, 12'd0, core_uio_out[3:0]};
                    end
                    ADDR_REG_DATA_OUT: begin
                        s_axi_rdata <= {24'd0, core_uo_out};
                    end
                    default: begin
                        s_axi_rdata <= 32'hDEADBEEF;
                    end
                endcase
            end else begin
                s_axi_arready <= 1'b0;
            end

            if (s_axi_rvalid && s_axi_rready) begin
                s_axi_rvalid <= 1'b0;
            end
        end
    end

    // ========================================================================
    // 6. INSTANTIATION OF FROZEN ASIC CORE
    // ========================================================================
    tt_um_scim_core u_scim_core (
        .ui_in   (core_ui_in),
        .uo_out  (core_uo_out),
        .uio_in  (core_uio_in),
        .uio_out (core_uio_out),
        .uio_oe  (core_uio_oe),
        .ena     (core_ena),
        .clk     (core_clk),
        .rst_n   (core_rst_n)
    );

    // ========================================================================
    // 7. EXTERNAL PMOD BREAKOUT (Hardware Logic Analyzer Snooping)
    // ========================================================================
    assign pmod_a = core_uo_out;

    assign pmod_b[0] = core_clk;
    assign pmod_b[1] = core_rst_n;
    assign pmod_b[2] = core_uio_out[0]; // busy
    assign pmod_b[3] = core_uio_out[1]; // done
    assign pmod_b[4] = core_uio_out[2]; // w_dout
    assign pmod_b[5] = core_uio_out[3]; // any_overflow
    assign pmod_b[6] = core_ctrl_strobe;
    assign pmod_b[7] = core_wr_act;

endmodule

`default_nettype wire
