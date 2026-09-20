# Project Progress: CIMTinyTO

## Last Execution Run: 2026-09-19 20:50
### [Built & Hardened]
- `src/tt_um_scim_core.v`: Applied all Phase 4 defensive hardening patches:
  - **Hole #1 (High):** Replaced 6-bit delta subtraction with 7-bit zero-extended signed arithmetic (`delta_mode1_7b`, `delta_mode2_7b`), eliminating intermediate negative overflow wrap-around when $P=16$ and tool-dependent sign-extension risks.
  - **Hole #3 (Medium):** Added a standard 2-stage DFF reset synchronizer (`rst_sync_0`, `rst_sync_1` $\implies$ `core_rst_n`) to eliminate board-level reset release metastability and prevent clock-skewed partial reset releases across LFSR/accumulator flip-flops.
  - **Hole #4 (Medium):** Added strict mutual exclusion between `ctrl_strobe` and `wr_act` using `else if`, preventing bus collisions and corrupted non-blocking assignments on the internal address register (`addr`).
- `test/test_scim_core.py`: Updated `reset_core(dut)` to wait 2 clock cycles after releasing `rst_n`, allowing the 2-stage synchronizer to cleanly deassert `core_rst_n` before test vector transactions begin.
- `src/scim_sng_bank.v`: Parameterized 16-channel SNG bank with a 128-bit compile-time seed vector (`SNG_SEEDS`), replacing hardwired local constants with zero silicon area overhead.
- `src/scim_accumulator.v`: Applied Hole #5 hardening patch wrapping concatenation operands in `$signed(...)` per IEEE 1364-2001 rules.

### [Architecture Decisions]
- **Phase 4 Review in Progress:** Paired architectural walkthrough of top-level wrapper with in-line defensive hardening. Completed inspection of control register mapping, FSM control, and reset synchronization. Phase 5 is held off until the user completes the full Phase 4 review.
- **2-Stage Synchronizer Timing Discipline:** Acknowledged the physical 2-cycle latency of `core_rst_n` deassertion, aligning testbench drivers and host SPI firmware protocols with physical silicon behavior.
- **Compile-Time SNG Seed Parameterization (Zero Silicon Cost):** Parameterized `SNG_SEEDS` [127:0] across `scim_sng_bank.v` and `tt_um_scim_core.v`. Evaluated during elaboration by Yosys with 0 extra transistors.
- **Hole #5 Signed Addition Enforcement:** Wrapped concatenation terms in `$signed(...)` in `src/scim_accumulator.v`.

### [Current Pipeline State]
- **Pillar 1 (Gate 0) Fully Complete, Verified & Frozen.**
- **Pillar 2 (Gate 1 Parameterized Verilog RTL & Simulation): 100% COMPLETE, HARDENED & PASSING.**
  - Static linting: `verilator --lint-only -Wall` passed with **0 warnings and 0 errors**.
  - Submodule unit tests (`test_lfsr`, `test_compressor`, `test_wallace`): **ALL PASS**.
  - Master end-to-end regression (`test_scim_core`): **8/8 golden vectors PASS with 100.00% bit-exact equivalence**.
  - "Tour & Harden" Progress: **Phase 1, 2, 3 complete. Phase 4 review currently in progress by user. Phase 5 on hold.**

### [Next Steps: Resuming Tomorrow with Phase 4 Continuation]
1. **Continue Phase 4 Review of `src/tt_um_scim_core.v`:**
   - Address any remaining user questions regarding readback multiplexer, FSM control, and top-level routing.
2. **Phase 5 (Verification Closure & Coverage Expansion - ON HOLD):**
   - Await user approval before adding the 2 non-trivial Mode 1 test vectors in `model/sim_scim.py` and expanding Cocotb regression to 10/10 vectors.
