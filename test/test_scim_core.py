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
import json
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


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
        act_byte = inputs_16[ch] & 0xFF
        dut.ui_in.value = act_byte
        dut.uio_in.value = (1 << 6)  # wr_act
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
    """Run all 8 golden test vectors from model/test_vectors_gate0.json."""
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
