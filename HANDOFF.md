# Session Handoff
 
- **Date:** 2026-09-21 13:30
- **Machine:** PC
- **Branch:** main
- **Sync Status:** Ready to commit & sync

---

## 1. Current State: Round 2 Audit & Hole #9 Implementation

1. **Round 2 Audit Documented ([`docs/rtl_audit_round2.md`](file:///home/juliusli/Documents/AntiG/CIMTinyTO/docs/rtl_audit_round2.md)):**
   - Hole #7 (High): Missing weight shift interlock (`w_shift_en && !busy`).
   - Hole #8 (High): Simultaneous switching output (SSO) pad gating (`uo_out` ground bounce).
   - Hole #9 (Medium): High-fanout reset network (761 DFFs) $\to$ resolved via RTL Register Cloning.
   - Hole #10 (Medium): Illegal mode (`2'b11`) negative accumulation leakage.
   - Hole #11 (Coverage): Absence of Constrained-Random Verification (CRV).

2. **Hole #9 (RTL Reset Register Cloning) Implemented & Verified:**
   - Partitioned the single `core_rst_n` into 4 dedicated domain drivers in `src/tt_um_scim_core.v`:
     - `rst_ctrl_n`: Control registers, FSM, and activation storage (~150 DFFs).
     - `rst_weight_n`: 256-bit weight memory shift chain (256 DFFs).
     - `rst_sng_n`: 16-channel Galois LFSR SNG bank (128 DFFs).
     - `rst_acc_n`: 16x 13-bit column accumulators (224 DFFs).
   - Tagged registers with `(* keep = "true" *)` to forbid synthesis merging.
   - Formalized 3-tier dictations (RTL cloning, SDC constraints, and OpenLane 2 config).
   - All 10/10 Cocotb golden vectors PASS (100.00% bit-exact).
   - Verilator static lint: 0 errors, 0 warnings.

---

## 2. Immediate Next Steps

1. Review and apply remaining Round 2 fixes:
   - Hole #7: Add `!busy` gate to `w_shift_en`.
   - Hole #8: Gate `uo_out` with `done` to eliminate 108 mW dynamic pad toggling and ground bounce.
   - Hole #10: Explicitly decode `mode == 2'b10` and tie `default` to 0.
   - Hole #11: Add 100-run Constrained-Random Verification (CRV) testbench.
2. Transition to Pillar 3 (Physical ASIC Flow / OpenLane 2).

