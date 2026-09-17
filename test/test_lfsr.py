"""
test_lfsr.py — Cocotb Unit Test for 8-bit Galois LFSR (lfsr8_galois.v)

Pedagogical Goals:
  1. Verify maximal-length 255-state trajectory (GF(2) primitive polynomial 0xB8).
  2. Verify synchronous active-low reset restores seed.
  3. Verify zero-state lockup prevention (fallback to 0x01).
  4. Verify clock enable gating.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


@cocotb.test()
async def test_lfsr_255_cycle_period(dut):
    """Verify that LFSR cycles through exactly 255 unique non-zero states."""
    clock = Clock(dut.clk, 20, unit="ns")  # 50 MHz
    cocotb.start_soon(clock.start())

    # Synchronous Reset
    dut.rst_n.value = 0
    dut.en.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    # Initial state should be non-zero (default SEED or 8'h01)
    initial_state = int(dut.state.value)
    assert initial_state != 0, "LFSR cannot start at zero!"

    # Enable LFSR and collect 255 states
    dut.en.value = 1
    seen_states = set()
    current_state = initial_state
    seen_states.add(current_state)

    for cycle in range(1, 255):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        state_val = int(dut.state.value)
        cocotb.log.info(f"Cycle {cycle}: clk={dut.clk.value}, rst_n={dut.rst_n.value}, en={dut.en.value}, state=0x{state_val:02X}")
        assert state_val != 0, f"LFSR entered zero state at cycle {cycle}!"
        assert state_val not in seen_states, f"Cycle {cycle}: State 0x{state_val:02X} repeated early!"
        seen_states.add(state_val)

    # After 255 cycles, next cycle must wrap back to initial state
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    wrap_state = int(dut.state.value)
    assert wrap_state == initial_state, f"LFSR failed to wrap to 0x{initial_state:02X} after 255 cycles (got 0x{wrap_state:02X})!"
    assert len(seen_states) == 255, f"Expected 255 unique states, got {len(seen_states)}!"


@cocotb.test()
async def test_lfsr_clock_enable(dut):
    """Verify clock enable holds state when disabled."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.en.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    state_before = int(dut.state.value)

    # Clock with en = 0 for 10 cycles
    for _ in range(10):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        assert int(dut.state.value) == state_before, "State changed while en=0!"

    # Clock with en = 1
    dut.en.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert int(dut.state.value) != state_before, "State did not advance when en=1!"
