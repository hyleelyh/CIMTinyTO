"""
test_compressor.py — Cocotb Unit Test for 4:2 Compressor & 16-to-5 Wallace Tree

Pedagogical Goals:
  1. Exhaustively verify all 32 input combinations for scim_compressor_42.
  2. Prove zero horizontal carry propagation (cout independent of cin).
  3. Verify 16-to-5 Wallace Tree reduction matches exact bit sum.
"""

import cocotb
from cocotb.triggers import Timer
import random


@cocotb.test()
async def test_compressor_42_exhaustive(dut):
    """Exhaustively verify all 32 combinations of (x1, x2, x3, x4, cin)."""
    # If the DUT is scim_compressor_42
    if not hasattr(dut, "x1"):
        cocotb.log.info("Skipping compressor_42 test on different DUT")
        return

    for x1 in [0, 1]:
        for x2 in [0, 1]:
            for x3 in [0, 1]:
                for x4 in [0, 1]:
                    for cin in [0, 1]:
                        dut.x1.value = x1
                        dut.x2.value = x2
                        dut.x3.value = x3
                        dut.x4.value = x4
                        dut.cin.value = cin
                        await Timer(1, unit="ns")

                        s = int(dut.sum.value)
                        c = int(dut.carry.value)
                        co = int(dut.cout.value)

                        # Check arithmetic identity:
                        # x1 + x2 + x3 + x4 + cin = sum + 2 * (carry + cout)
                        input_sum = x1 + x2 + x3 + x4 + cin
                        output_sum = s + 2 * (c + co)
                        assert input_sum == output_sum, (
                            f"Mismatch for ({x1},{x2},{x3},{x4}, cin={cin}): "
                            f"in={input_sum} != out={output_sum} (s={s}, c={c}, co={co})"
                        )

                        # Check that cout is independent of cin
                        expected_co = x3 if (x1 ^ x2) else x1
                        assert co == expected_co, f"Cout dependency violation: {co} != {expected_co}"


@cocotb.test()
async def test_wallace_tree_reduction(dut):
    """Verify 16-to-5 Wallace Tree reduction on corner cases and random patterns."""
    if not hasattr(dut, "in_bits"):
        cocotb.log.info("Skipping wallace_tree test on different DUT")
        return

    # Corner case 1: All zeros
    dut.in_bits.value = 0
    await Timer(1, units="ns")
    assert int(dut.count.value) == 0, f"Expected 0, got {int(dut.count.value)}"

    # Corner case 2: All ones (16)
    dut.in_bits.value = 0xFFFF
    await Timer(1, units="ns")
    assert int(dut.count.value) == 16, f"Expected 16, got {int(dut.count.value)}"

    # Corner case 3: Single bit high (one-hot, exactly 1)
    for b in range(16):
        dut.in_bits.value = (1 << b)
        await Timer(1, unit="ns")
        assert int(dut.count.value) == 1, f"One-hot bit {b} failed: got {int(dut.count.value)}"

    # Corner case 4: Alternating bits
    dut.in_bits.value = 0x5555  # 8 ones
    await Timer(1, units="ns")
    assert int(dut.count.value) == 8, f"Expected 8, got {int(dut.count.value)}"

    dut.in_bits.value = 0xAAAA  # 8 ones
    await Timer(1, units="ns")
    assert int(dut.count.value) == 8, f"Expected 8, got {int(dut.count.value)}"

    # 1,000 random vectors
    random.seed(42)
    for _ in range(1000):
        val = random.randint(0, 0xFFFF)
        expected = bin(val).count("1")
        dut.in_bits.value = val
        await Timer(1, unit="ns")
        actual = int(dut.count.value)
        assert actual == expected, f"Mismatch for 0x{val:04X}: expected {expected}, got {actual}"
