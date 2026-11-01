`timescale 1ns / 1ps

module tb_scim_feeder_2tiles;
    reg aclk = 0;
    reg aresetn = 0;
    reg [31:0] s_axis_tdata = 0;
    reg s_axis_tvalid = 0;
    wire s_axis_tready;
    reg s_axis_tlast = 0;
    wire [31:0] m_axis_tdata;
    wire m_axis_tvalid;
    reg m_axis_tready = 1;
    wire m_axis_tlast;
    wire [7:0] pmod_a, pmod_b;

    scim_axis_stream_feeder dut (
        .aclk(aclk), .aresetn(aresetn),
        .s_axis_tdata(s_axis_tdata), .s_axis_tvalid(s_axis_tvalid),
        .s_axis_tready(s_axis_tready), .s_axis_tlast(s_axis_tlast),
        .m_axis_tdata(m_axis_tdata), .m_axis_tvalid(m_axis_tvalid),
        .m_axis_tready(m_axis_tready), .m_axis_tlast(m_axis_tlast),
        .pmod_a(pmod_a), .pmod_b(pmod_b)
    );

    always #10 aclk = ~aclk; // 50 MHz

    integer w;

    initial begin
        #100; aresetn = 1; #40;

        // 1. Load weights
        @(posedge aclk);
        s_axis_tdata <= 32'h01000000; s_axis_tvalid <= 1;
        @(posedge aclk); while (!s_axis_tready) @(posedge aclk);
        for (w = 0; w < 8; w = w + 1) begin
            s_axis_tdata <= 32'hFFFFFFFF; s_axis_tvalid <= 1;
            @(posedge aclk); while (!s_axis_tready) @(posedge aclk);
        end
        s_axis_tvalid <= 0;
        while (dut.state != 0) @(posedge aclk);
        $display("[%0t ns] Weights shifted!", $time);

        #100;
        // 2. Send CMD_MVM_BATCH for 2 tiles
        @(posedge aclk);
        s_axis_tdata <= 32'h03000002; s_axis_tvalid <= 1; // 2 tiles!
        @(posedge aclk); while (!s_axis_tready) @(posedge aclk);

        // Tile 0 activations: 4 words
        for (w = 0; w < 4; w = w + 1) begin
            s_axis_tdata <= 32'h80808080; s_axis_tvalid <= 1;
            @(posedge aclk); while (!s_axis_tready) @(posedge aclk);
        end

        // Tile 1 activations: 4 words
        for (w = 0; w < 4; w = w + 1) begin
            s_axis_tdata <= 32'h40404040; s_axis_tvalid <= 1;
            s_axis_tlast <= (w == 3);
            @(posedge aclk); while (!s_axis_tready) @(posedge aclk);
        end
        s_axis_tvalid <= 0; s_axis_tlast <= 0;
        $display("[%0t ns] Sent all 9 words for 2 tiles. Waiting for completion...", $time);

        for (w = 0; w < 1000; w = w + 1) begin
            @(posedge aclk);
            if (m_axis_tvalid) begin
                $display("[%0t ns] M_AXIS: data=0x%08h, tlast=%b, word_idx=%0d", 
                         $time, m_axis_tdata, m_axis_tlast, dut.out_word_idx);
            end
            if (m_axis_tvalid && m_axis_tlast) begin
                $display("[%0t ns] TLAST DETECTED! TEST PASSED!", $time);
                #100;
                $finish;
            end
        end

        $display("[%0t ns] TIMEOUT! Stuck in state: %0d", $time, dut.state);
        $finish;
    end

    always @(dut.state) begin
        $display("[%0t ns] State: %0d (core_busy=%b, core_done=%b, batch_rem=%0d)", 
                 $time, dut.state, dut.core_busy, dut.core_done, dut.batch_tiles_rem);
    end
endmodule
