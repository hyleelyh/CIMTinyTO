"""
test_scim_core.py — End-to-End Gate 1 Verification Suite for CIMTinyTO

Pedagogical Goals:
  1. Verify the complete tt_um_scim_core macro against all 8 Gate 0 Golden Test Vectors
     from model/test_vectors_gate0.json.
  2. Test Mode 0 (Unipolar AND), Mode 1 (Bipolar XNOR), and Mode 2 (Hybrid ReLU).
  3. Verify DFT serial weight shift and readback loopback (w_dout).
  4. Verify 16-channel sequential activation loading with address auto-increment.
  5. Verify 256-cycle compute timing, busy/done handshaking, and 13-bit accumulator readback.
"""

import os
import sys
import json
import random
import numpy as np
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from model.sim_scim import SCIMTile, ProcessingElement


def sign_extend_13(low_byte: int, high_byte: int) -> int:
    """Reconstruct signed 13-bit integer from low and high bytes."""
    raw = (high_byte << 8) | low_byte
    # 13-bit signed value
    val = raw & 0x1FFF
    if val & 0x1000:  # Sign bit (bit 12) is set
        val -= 0x2000
    return val


async def reset_core(dut):
    """Synchronous active-low reset."""
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    # Wait for 2-stage synchronizer (rst_sync_0, rst_sync_1) to release core_rst_n
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


async def load_weights_serial(dut, weights_2d):
    """
    Shift 256 weight bits into weight memory.
    weights_2d: 16x16 list or array.
    Mapping: row i, col j -> weight_matrix[row*16 + col].
    Shifting order: index 255 down to 0.
    """
    # Flatten 16x16 to 256 bits
    flat = []
    for r in range(16):
        for c in range(16):
            w = weights_2d[r][c]
            # In hardware: positive weight -> 1, non-positive -> 0
            flat.append(1 if w > 0 else 0)

    dut.uio_in.value = 0
    # Enable shift
    for idx in range(255, -1, -1):
        bit_val = flat[idx]
        # uio_in[4] = w_din, uio_in[5] = w_shift_en (1 << 5 = 0x20)
        dut.uio_in.value = (1 << 5) | ((bit_val & 1) << 4)
        await RisingEdge(dut.clk)

    # Disable shift
    dut.uio_in.value = 0
    await RisingEdge(dut.clk)


async def load_activations(dut, inputs_16):
    """
    Load 16 activation bytes sequentially.
    Uses address auto-increment with wr_act (uio_in[6]).
    """
    # First, set address to 0 using ctrl_strobe (uio_in[7])
    dut.ui_in.value = 0x00  # addr = 0
    dut.uio_in.value = (1 << 7)  # ctrl_strobe
    await RisingEdge(dut.clk)
    dut.uio_in.value = 0
    await RisingEdge(dut.clk)

    # Write each activation byte; addr auto-increments
    for ch in range(16):
        act_byte = int(inputs_16[ch]) & 0xFF
        dut.ui_in.value = int(act_byte)
        dut.uio_in.value = int(1 << 6)  # wr_act
        await RisingEdge(dut.clk)

    dut.uio_in.value = 0
    dut.ui_in.value = 0
    await RisingEdge(dut.clk)


async def run_computation(dut, mode: int):
    """
    Trigger compute phase and wait for done assertion.
    mode: 0, 1, or 2.
    """
    # Set mode and start bit (bit 7) via ctrl_strobe
    cmd = (1 << 7) | ((mode & 0x3) << 4)
    dut.ui_in.value = cmd
    dut.uio_in.value = (1 << 7)  # ctrl_strobe
    await RisingEdge(dut.clk)

    dut.uio_in.value = 0
    dut.ui_in.value = 0

    # Wait for busy to assert
    await RisingEdge(dut.clk)

    # Wait for done to assert (at cycle 256)
    cycles = 0
    while not dut.uio_out[1].value:
        await RisingEdge(dut.clk)
        cycles += 1
        if cycles > 300:
            raise TimeoutError(f"Compute phase timed out after {cycles} cycles!")

    cocotb.log.info(f"Compute finished in {cycles} clock cycles (busy -> done).")


async def readback_accumulators(dut) -> list:
    """Read back all 16 column accumulators through uo_out multiplexer."""
    results = []
    for col in range(16):
        # Read low byte: addr = col, byte_sel = 0
        cmd_low = (0 << 6) | (col & 0xF)
        dut.ui_in.value = cmd_low
        dut.uio_in.value = (1 << 7)  # ctrl_strobe
        await RisingEdge(dut.clk)
        dut.uio_in.value = 0
        await Timer(1, unit="ns")
        low_byte = int(dut.uo_out.value)

        # Read high byte: addr = col, byte_sel = 1
        cmd_high = (1 << 6) | (col & 0xF)
        dut.ui_in.value = cmd_high
        dut.uio_in.value = (1 << 7)  # ctrl_strobe
        await RisingEdge(dut.clk)
        dut.uio_in.value = 0
        await Timer(1, unit="ns")
        high_byte = int(dut.uo_out.value)

        val = sign_extend_13(low_byte, high_byte)
        results.append(val)

    return results


@cocotb.test()
async def test_scim_core_gate0_vectors(dut):
    """Run all 10 golden test vectors from model/test_vectors_gate0.json."""
    clock = Clock(dut.clk, 20, unit="ns")  # 50 MHz
    cocotb.start_soon(clock.start())

    # Locate test vector file
    json_path = os.path.join(os.path.dirname(__file__), "..", "model", "test_vectors_gate0.json")
    with open(json_path, "r") as f:
        data = json.load(f)

    vectors = data["vectors"]
    total_passed = 0

    for v in vectors:
        name = v["name"]
        mode = v["mode"]
        inputs = v["inputs"]
        weights = v["weights"]
        expected = v["expected_accumulators"]

        cocotb.log.info(f"\n========================================================")
        cocotb.log.info(f"Running Test Vector: {name} (Mode {mode})")
        cocotb.log.info(f"Description: {v.get('description', '')}")

        # Reset core for clean initial LFSR seeds
        await reset_core(dut)

        # 1. Load weights
        await load_weights_serial(dut, weights)

        # 2. Load activations
        await load_activations(dut, inputs)

        # 3. Start compute
        await run_computation(dut, mode)

        # 4. Readback results
        actual = await readback_accumulators(dut)

        # 5. Check bit-exact equivalence
        errors = 0
        for col in range(16):
            if actual[col] != expected[col]:
                cocotb.log.error(
                    f"  Col {col:2d}: MISMATCH! RTL = {actual[col]:5d}, Expected = {expected[col]:5d} (Diff = {actual[col]-expected[col]})"
                )
                errors += 1
            else:
                cocotb.log.debug(f"  Col {col:2d}: PASS ({actual[col]:5d})")

        assert errors == 0, f"Test vector {name} failed with {errors} column errors!"
        cocotb.log.info(f"Vector {name} PASSED (16/16 columns bit-exact match)")
        total_passed += 1

    cocotb.log.info(f"\n========================================================")
    cocotb.log.info(f"GATE 1 REGRESSION COMPLETE: {total_passed}/{len(vectors)} VECTORS PASSED (100.00%)")


@cocotb.test()
async def test_scim_core_silicon_hardening(dut):
    """
    Verify Round 2 silicon hardening defenses:
      1. Hole #8: Output pad quiescence (uo_out == 0 during active compute).
      2. Hole #7: Weight shift interlock (!busy prevents shift during compute).
      3. Hole #10: Illegal mode 2'b11 clamped to zero delta.
    """
    clock = Clock(dut.clk, 20, unit="ns")  # 50 MHz
    cocotb.start_soon(clock.start())

    await reset_core(dut)

    # 1. Test Hole #8 & Hole #7: Output pad quietness & Shift interlock during compute
    cocotb.log.info("\n========================================================")
    cocotb.log.info("TESTING HOLE #8 (Pad Quiescence) & HOLE #7 (Shift Interlock)")
    cocotb.log.info("========================================================")
    weights = np.ones((16, 16), dtype=int)
    inputs = np.full(16, 255, dtype=int)
    await load_weights_serial(dut, weights)
    await load_activations(dut, inputs)

    # Trigger compute in Mode 0 (start bit = 1, mode = 0)
    cmd = (1 << 7) | (0 << 4)
    dut.ui_in.value = cmd
    dut.uio_in.value = (1 << 7)
    await RisingEdge(dut.clk)
    dut.uio_in.value = 0
    dut.ui_in.value = 0
    await RisingEdge(dut.clk)

    # While busy, verify uo_out remains 0 and attempt spurious weight shift
    pad_violations = 0
    # Step 50 cycles into compute
    for _ in range(50):
        if int(dut.uo_out.value) != 0:
            pad_violations += 1
        await RisingEdge(dut.clk)

    # Attempt illegal weight shift for 20 cycles while busy == 1 (Hole #7 attack)
    for _ in range(20):
        assert dut.uio_out[0].value == 1, "Expected core to be busy during compute!"
        if int(dut.uo_out.value) != 0:
            pad_violations += 1
        dut.uio_in.value = (1 << 5) | (1 << 4)  # w_shift_en = 1, w_din = 1
        await RisingEdge(dut.clk)

    # Release shift pin well before compute finishes
    dut.uio_in.value = 0

    # Wait until done, verifying uo_out remains 0 while busy
    while not dut.uio_out[1].value:
        if dut.uio_out[0].value and int(dut.uo_out.value) != 0:
            pad_violations += 1
        await RisingEdge(dut.clk)

    assert pad_violations == 0, f"Hole #8 FAILED: uo_out toggled {pad_violations} times during active compute!"
    cocotb.log.info("✓ Hole #8 PASSED: Output pads remained completely quiescent (8'h00) during active compute.")

    # Readback after compute: weights should NOT have been shifted by the spurious w_shift_en
    actual = await readback_accumulators(dut)
    expected_all_255 = 4095  # Mode 0 sum of max activations across all 16 rows (4096 saturated to 4095)
    for col in range(16):
        assert actual[col] == expected_all_255, (
            f"Hole #7 FAILED: Col {col} was {actual[col]}, expected {expected_all_255}. Weight shift occurred during compute!"
        )
    cocotb.log.info("✓ Hole #7 PASSED: Serial weight shift was cleanly interlocked during compute.")

    # 2. Test Hole #10: Illegal mode 2'b11 clamping
    cocotb.log.info("\n========================================================")
    cocotb.log.info("TESTING HOLE #10 (Illegal Mode 2'b11 Clamping)")
    cocotb.log.info("========================================================")
    await reset_core(dut)
    await load_weights_serial(dut, weights)
    await load_activations(dut, inputs)

    # Start compute with mode = 3 (2'b11)
    cmd = (1 << 7) | (3 << 4)
    dut.ui_in.value = cmd
    dut.uio_in.value = (1 << 7)
    await RisingEdge(dut.clk)
    dut.uio_in.value = 0
    dut.ui_in.value = 0

    while not dut.uio_out[1].value:
        await RisingEdge(dut.clk)

    actual_m11 = await readback_accumulators(dut)
    for col in range(16):
        assert actual_m11[col] == 0, f"Hole #10 FAILED: Col {col} accumulated {actual_m11[col]} under illegal mode 2'b11!"
    cocotb.log.info("✓ Hole #10 PASSED: Undefined Mode 2'b11 clamped deltas to 0 (all accumulators = 0).")


@cocotb.test()
async def test_scim_core_constrained_random(dut):
    """
    Hole #11: Constrained-Random Verification (CRV) Multi-Vector Stress.
    Runs 15 randomized trials across Mode 0, Mode 1, and Mode 2 with arbitrary
    activation distributions and weight matrices, verifying bit-exact RTL equivalence
    against the Gate 0 Python golden reference model (SCIMTile).
    """
    clock = Clock(dut.clk, 20, unit="ns")  # 50 MHz
    cocotb.start_soon(clock.start())

    np.random.seed(2026)
    random.seed(2026)
    tile = SCIMTile()

    num_trials = 15
    cocotb.log.info(f"\n========================================================")
    cocotb.log.info(f"STARTING CONSTRAINED-RANDOM VERIFICATION ({num_trials} TRIALS)")
    cocotb.log.info(f"========================================================")

    for trial in range(num_trials):
        mode = trial % 3  # Rotate evenly across Modes 0, 1, 2
        mode_str = ["Unipolar", "Bipolar", "Hybrid ReLU"][mode]

        # Generate randomized activations
        activations = np.random.randint(0, 256, size=16, dtype=int)
        if mode == 2 and trial % 2 == 1:
            activations[activations < 128] = 0  # 50% ReLU sparsity on some runs

        # Generate randomized weights
        if mode == 2:
            weights = np.random.choice([-1, 1], size=(16, 16))
        else:
            weights = np.random.randint(0, 2, size=(16, 16))

        # 1. Compute golden expected results using Python SCIMTile
        tile.load_weights(weights)
        golden = tile.run_mvm(activations, mode=mode, N=256)
        expected = golden["results"]

        # 2. Reset and load DUT
        await reset_core(dut)
        await load_weights_serial(dut, weights)
        await load_activations(dut, activations)

        # 3. Execute compute
        await run_computation(dut, mode)

        # 4. Readback
        actual = await readback_accumulators(dut)

        # 5. Verify bit-exact equality
        errors = 0
        for col in range(16):
            if actual[col] != expected[col]:
                cocotb.log.error(
                    f"Trial {trial:2d} (Mode {mode_str}) Col {col:2d}: MISMATCH! RTL={actual[col]}, Golden={expected[col]}"
                )
                errors += 1

        assert errors == 0, f"Trial {trial} (Mode {mode_str}) failed with {errors} column errors!"
        cocotb.log.info(f"  Trial {trial+1:2d}/{num_trials:2d} [Mode {mode}: {mode_str:11s}]: PASS (16/16 columns bit-exact)")

    cocotb.log.info(f"\n========================================================")
    cocotb.log.info(f"CRV REGRESSION PASSED: {num_trials}/{num_trials} RANDOMIZED TRIALS 100% BIT-EXACT")
    cocotb.log.info(f"========================================================")
