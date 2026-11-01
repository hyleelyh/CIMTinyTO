`timescale 1ns / 1ps

module tb_scim_feeder;

    reg aclk;
    reg aresetn;

    // S_AXIS
    reg  [31:0] s_axis_tdata;
    reg         s_axis_tvalid;
    wire        s_axis_tready;
    reg         s_axis_tlast;

    // M_AXIS
    wire [31:0] m_axis_tdata;
    wire        m_axis_tvalid;
    reg         m_axis_tready;
    wire        m_axis_tlast;

    wire [7:0] pmod_a;
    wire [7:0] pmod_b;

    // Instantiate DUT
    scim_axis_stream_feeder dut (
        .aclk(aclk),
        .aresetn(aresetn),
        .s_axis_tdata(s_axis_tdata),
        .s_axis_tvalid(s_axis_tvalid),
        .s_axis_tready(s_axis_tready),
        .s_axis_tlast(s_axis_tlast),
        .m_axis_tdata(m_axis_tdata),
        .m_axis_tvalid(m_axis_tvalid),
        .m_axis_tready(m_axis_tready),
        .m_axis_tlast(m_axis_tlast),
        .pmod_a(pmod_a),
        .pmod_b(pmod_b)
    );

    // 50 MHz clock (20ns period)
    always #10 aclk = ~aclk;

    integer word_cnt;

    initial begin
        aclk = 0;
        aresetn = 0;
        s_axis_tdata = 0;
        s_axis_tvalid = 0;
        s_axis_tlast = 0;
        m_axis_tready = 1;

        // Reset for 100ns
        #100;
        aresetn = 1;
        #40;

        $display("[%0t ns] Reset released. Testing CMD_LOAD_WEIGHTS...", $time);

        // Send Header: CMD_LOAD_WEIGHTS (0x01 << 24)
        @(posedge aclk);
        s_axis_tdata <= 32'h01000000;
        s_axis_tvalid <= 1'b1;
        s_axis_tlast <= 1'b0;
        @(posedge aclk);
        while (!s_axis_tready) @(posedge aclk);

        // Send 8 weight words
        for (word_cnt = 0; word_cnt < 8; word_cnt = word_cnt + 1) begin
            s_axis_tdata <= 32'hFFFFFFFF;
            s_axis_tvalid <= 1'b1;
            s_axis_tlast <= (word_cnt == 7) ? 1'b1 : 1'b0;
            @(posedge aclk);
            while (!s_axis_tready) @(posedge aclk);
        end
        s_axis_tvalid <= 1'b0;
        s_axis_tlast <= 1'b0;

        $display("[%0t ns] Weight packet transmitted. Waiting for shifting...", $time);
        while (dut.state != 0) @(posedge aclk);
        $display("[%0t ns] Weights shifted successfully! State returned to IDLE.", $time);

        #100;
        $display("[%0t ns] Testing CMD_MVM_BATCH (1 tile)...", $time);
        @(posedge aclk);
        // Header: CMD_MVM_BATCH | 1 tile
        s_axis_tdata <= 32'h03000001;
        s_axis_tvalid <= 1'b1;
        s_axis_tlast <= 1'b0;
        @(posedge aclk);
        while (!s_axis_tready) @(posedge aclk);

        // Send 4 activation words (16 activations of 128 = 0x80)
        for (word_cnt = 0; word_cnt < 4; word_cnt = word_cnt + 1) begin
            s_axis_tdata <= 32'h80808080;
            s_axis_tvalid <= 1'b1;
            s_axis_tlast <= (word_cnt == 3) ? 1'b1 : 1'b0;
            @(posedge aclk);
            while (!s_axis_tready) @(posedge aclk);
        end
        s_axis_tvalid <= 1'b0;
        s_axis_tlast <= 1'b0;

        $display("[%0t ns] Activation words sent. Monitoring feeder state...", $time);
        for (word_cnt = 0; word_cnt < 350; word_cnt = word_cnt + 1) begin
            @(posedge aclk);
            if (m_axis_tvalid) begin
                $display("[%0t ns] M_AXIS OUT: data=0x%08h, tlast=%b, word_idx=%0d", 
                         $time, m_axis_tdata, m_axis_tlast, dut.out_word_idx);
            end
        end

        $finish;
    end

    // Monitor State Changes
    always @(dut.state) begin
        $display("[%0t ns] Feeder State: %0d (core_busy=%b, core_done=%b)", 
                 $time, dut.state, dut.core_busy, dut.core_done);
    end

endmodule
