#!/usr/bin/env python3
"""
scripts/gls_power_audit.py — Gate-Level Simulation (GLS) & VCD-Driven Dynamic Power Audit Engine

Pedagogical ASIC Principles:
  1. Static Power vs. Dynamic Workload Power:
     Static STA in OpenROAD (Pillar 4) computes power assuming uniform, synthetic switching
     probabilities (alpha ~= 0.1 to 0.2). In reality, neural network workloads exhibit wide
     dynamic variations driven by activation sparsity (ReLU), mode selection (AND vs XNOR),
     and stochastic bitstream correlation.
  2. The Physics of Dynamic CMOS Power:
     P_dyn = P_switch + P_internal
     P_switch = 0.5 * V_DD^2 * f_clk * SUM(alpha_i * C_i)
     where:
       - V_DD = 1.80 V (nominal core supply rail)
       - f_clk = 50.0 MHz (20.0 ns cycle period)
       - C_i = physical net wire & pin capacitance extracted from post-route SPEF
       - alpha_i = transition density (transitions / clock cycles) extracted from VCD
  3. Pad Quiescence & PCB Energy Conservation (Hole #8):
     External pad capacitance (C_pad ~= 5 pF) is ~500x larger than internal standard-cell
     wire capacitance (C_wire ~= 10 fF). Toggling 8 output pins at 50 MHz dissipates:
       P_pad = 8 * 0.5 * (5 pF) * (3.3 V)^2 * (50 MHz) * alpha ~= 10.8 mW * alpha!
     Gating uo_out to 8'h00 during the 256-cycle compute phase saves significant power and
     eliminates package ground bounce (L * di/dt).

Author: Antigravity & Julius Li
Date: 2026-09-26
"""

import os
import sys
import argparse
import subprocess
import json
from typing import Dict, Tuple, List, Optional


class SPEFParser:
    """Parses OpenROAD post-routing SPEF to extract net-by-net lumped capacitances."""

    def __init__(self, spef_path: str):
        self.spef_path = spef_path
        self.name_map: Dict[str, str] = {}
        self.net_caps: Dict[str, float] = {}  # net_name -> capacitance in pF
        self.total_chip_cap_pf: float = 0.0

    def parse(self) -> Dict[str, float]:
        if not os.path.exists(self.spef_path):
            raise FileNotFoundError(f"SPEF file not found: {self.spef_path}")

        in_name_map = False
        with open(self.spef_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                if line == "*NAME_MAP":
                    in_name_map = True
                    continue
                elif line.startswith("*PORTS") or line.startswith("*D_NET"):
                    in_name_map = False

                if in_name_map and line.startswith("*"):
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        self.name_map[parts[0]] = parts[1]

                if line.startswith("*D_NET"):
                    parts = line.split()
                    if len(parts) >= 3:
                        net_id = parts[1]
                        cap_pf = float(parts[2])
                        raw_name = self.name_map.get(net_id, net_id)
                        clean_name = self._sanitize_name(raw_name)
                        self.net_caps[clean_name] = cap_pf

        self.total_chip_cap_pf = sum(self.net_caps.values())
        return self.net_caps

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Strip escape backslashes and trailing spaces common in Verilog SPEF."""
        return name.replace("\\", "").rstrip()


class VCDActivityParser:
    """Streams and parses VCD or FST waveform traces to calculate transition activity."""

    def __init__(self, vcd_path: str):
        self.vcd_path = vcd_path
        self.var_map: Dict[str, str] = {}    # vcd_id -> clean_net_name
        self.toggles: Dict[str, int] = {}    # clean_net_name -> transition count
        self.sim_time_ps: int = 0
        self.clock_cycles: int = 0
        self.clock_toggles: int = 0

    def parse(self, clock_period_ns: float = 20.0) -> Dict[str, int]:
        if not os.path.exists(self.vcd_path):
            raise FileNotFoundError(f"Waveform file not found: {self.vcd_path}")

        # Check if input is FST (starts with binary header) or ASCII VCD
        is_fst = False
        with open(self.vcd_path, "rb") as f:
            header_bytes = f.read(16)
            if b"$date" not in header_bytes and b"$version" not in header_bytes:
                is_fst = True

        if is_fst:
            cmd = ["fst2vcd", self.vcd_path]
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, text=True, bufsize=262144
            )
            stream = proc.stdout
        else:
            proc = None
            stream = open(self.vcd_path, "r", encoding="utf-8", errors="ignore")

        try:
            in_header = True
            scope_stack = []
            id_to_name: Dict[str, str] = {}
            id_to_toggles: Dict[str, int] = {}

            for line in stream:
                line = line.strip()
                if not line:
                    continue

                if in_header:
                    if line.startswith("$scope"):
                        parts = line.split()
                        if len(parts) >= 3:
                            scope_stack.append(parts[2])
                    elif line.startswith("$upscope"):
                        if scope_stack:
                            scope_stack.pop()
                    elif line.startswith("$var"):
                        parts = line.split()
                        if len(parts) >= 5:
                            var_id = parts[3]
                            var_name = parts[4]
                            # Only capture nets directly declared in tb.user_project (the macro nets)
                            if scope_stack == ["tb", "user_project"]:
                                clean_name = SPEFParser._sanitize_name(var_name)
                                id_to_name[var_id] = clean_name
                                id_to_toggles[var_id] = 0
                    elif line.startswith("$enddefinitions"):
                        in_header = False
                else:
                    if line.startswith("#"):
                        self.sim_time_ps = int(line[1:])
                    elif line.startswith("b") or line.startswith("B"):
                        parts = line.split()
                        if len(parts) == 2:
                            var_id = parts[1]
                            if var_id in id_to_toggles:
                                id_to_toggles[var_id] += 1
                    else:
                        # Scalar transition like '1#' or '0#'
                        var_id = line[1:]
                        if var_id in id_to_toggles:
                            id_to_toggles[var_id] += 1

            if proc:
                proc.wait()
            else:
                stream.close()

            # Store aggregated toggles by sanitized net name
            for var_id, cnt in id_to_toggles.items():
                name = id_to_name[var_id]
                self.toggles[name] = self.toggles.get(name, 0) + cnt

            # Compute clock cycle count
            sim_time_ns = self.sim_time_ps / 1000.0
            self.clock_cycles = max(1, int(round(sim_time_ns / clock_period_ns)))
            self.clock_toggles = self.toggles.get("clk", 0)

            return self.toggles
        finally:
            if proc and proc.poll() is None:
                proc.kill()


class DynamicPowerAuditor:
    """Computes cycle-accurate dynamic switching power by correlating VCD toggles with SPEF parasitics."""

    def __init__(
        self,
        spef_caps: Dict[str, float],
        vcd_toggles: Dict[str, int],
        clock_cycles: int,
        v_dd: float = 1.80,
        freq_mhz: float = 50.0,
        openroad_metrics_path: Optional[str] = None,
    ):
        self.spef_caps = spef_caps
        self.vcd_toggles = vcd_toggles
        self.clock_cycles = max(1, clock_cycles)
        self.v_dd = v_dd
        self.freq_mhz = freq_mhz
        self.freq_hz = freq_mhz * 1e6
        self.metrics_path = openroad_metrics_path

        # Baseline OpenROAD static numbers (defaults from metrics.csv)
        self.static_p_internal_mw = 2.119
        self.static_p_switch_mw = 0.679
        self.static_p_leak_nw = 52.54
        self.static_p_total_mw = 2.798

        self._load_openroad_metrics()

    def _load_openroad_metrics(self):
        if self.metrics_path and os.path.exists(self.metrics_path):
            try:
                with open(self.metrics_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split(",")
                        if len(parts) == 2:
                            k, v = parts[0].strip(), parts[1].strip()
                            try:
                                val = float(v)
                                if k == "power__internal__total":
                                    self.static_p_internal_mw = val * 1000.0
                                elif k == "power__switching__total":
                                    self.static_p_switch_mw = val * 1000.0
                                elif k == "power__leakage__total":
                                    self.static_p_leak_nw = val * 1e9
                                elif k == "power__total":
                                    self.static_p_total_mw = val * 1000.0
                            except ValueError:
                                pass
            except Exception:
                pass

    def compute_power_breakdown(self) -> Dict:
        """
        Calculates switching power per net and functional group:
          P_switch_i = 0.5 * C_i * V_dd^2 * f_clk * alpha_i
        """
        scale_factor = 0.5 * (self.v_dd**2) * self.freq_hz  # Watts per Farad (when alpha=1)

        domain_caps_pf: Dict[str, float] = {
            "Clock Network": 0.0,
            "Reset & Synchronizers": 0.0,
            "SNG LFSR Bank": 0.0,
            "Weight Memory (256 DFFs)": 0.0,
            "PE Array (16x16)": 0.0,
            "Wallace Tree Compressors": 0.0,
            "Accumulators (16x 13-bit)": 0.0,
            "Control & IO Pads": 0.0,
            "Other Core Logic": 0.0,
        }

        domain_power_mw: Dict[str, float] = {k: 0.0 for k in domain_caps_pf}
        domain_toggles: Dict[str, int] = {k: 0 for k in domain_caps_pf}

        matched_nets = 0
        total_dyn_switch_w = 0.0
        top_power_nets = []

        avg_cap_pf = (
            (sum(self.spef_caps.values()) / len(self.spef_caps))
            if self.spef_caps
            else 0.005
        )

        for net_name, toggles in self.vcd_toggles.items():
            cap_pf = self.spef_caps.get(net_name)
            if cap_pf is not None:
                matched_nets += 1
            else:
                # Fallback for bus slices (e.g. ui_in vs ui_in[0])
                cap_pf = avg_cap_pf

            cap_f = cap_pf * 1e-12
            alpha = toggles / self.clock_cycles
            p_net_w = scale_factor * cap_f * alpha
            p_net_mw = p_net_w * 1000.0
            total_dyn_switch_w += p_net_w

            group = self._classify_net(net_name)
            domain_caps_pf[group] += cap_pf
            domain_power_mw[group] += p_net_mw
            domain_toggles[group] += toggles

            if p_net_mw > 0.0005:  # > 0.5 uW
                top_power_nets.append((net_name, cap_pf * 1000.0, alpha, p_net_mw))

        total_dyn_switch_mw = total_dyn_switch_w * 1000.0

        # Total dynamic power = OpenROAD internal cell power + VCD-driven switching power + leakage
        total_workload_power_mw = (
            self.static_p_internal_mw + total_dyn_switch_mw + (self.static_p_leak_nw * 1e-6)
        )

        # Workload Energy Calculations:
        # 16x16 MVM duration = 256 cycles * 20.0 ns = 5.12 us
        mvm_duration_s = 256 * (1.0 / self.freq_hz)
        energy_per_mvm_nj = (total_workload_power_mw * 1e-3) * mvm_duration_s * 1e9
        energy_per_mac_pj = (energy_per_mvm_nj / 256.0) * 1000.0

        # Top nets sorted by power
        top_power_nets.sort(key=lambda x: x[3], reverse=True)

        return {
            "v_dd": self.v_dd,
            "freq_mhz": self.freq_mhz,
            "clock_cycles": self.clock_cycles,
            "total_dyn_switch_mw": total_dyn_switch_mw,
            "static_p_switch_mw": self.static_p_switch_mw,
            "static_p_internal_mw": self.static_p_internal_mw,
            "static_p_leak_nw": self.static_p_leak_nw,
            "total_workload_power_mw": total_workload_power_mw,
            "switching_power_ratio": total_dyn_switch_mw / max(1e-6, self.static_p_switch_mw),
            "energy_per_mvm_nj": energy_per_mvm_nj,
            "energy_per_mac_pj": energy_per_mac_pj,
            "domain_caps_pf": domain_caps_pf,
            "domain_power_mw": domain_power_mw,
            "domain_toggles": domain_toggles,
            "top_power_nets": top_power_nets[:10],
            "matched_nets": matched_nets,
            "total_tracked_nets": len(self.vcd_toggles),
        }

    @staticmethod
    def _classify_net(name: str) -> str:
        low = name.lower()
        if "clk" in low or "net40" in low or "clkbuf" in low:
            return "Clock Network"
        elif "rst" in low or "sync" in low:
            return "Reset & Synchronizers"
        elif "sng" in low or "lfsr" in low:
            return "SNG LFSR Bank"
        elif "weight" in low or "w_din" in low or "w_shift" in low:
            return "Weight Memory (256 DFFs)"
        elif "pe" in low:
            return "PE Array (16x16)"
        elif "tree" in low or "compressor" in low or "col_sum" in low:
            return "Wallace Tree Compressors"
        elif "acc" in low or "delta" in low:
            return "Accumulators (16x 13-bit)"
        elif "ui_" in low or "uio_" in low or "uo_" in low or "addr" in low or "mode" in low:
            return "Control & IO Pads"
        else:
            return "Other Core Logic"


def print_audit_report(results: Dict):
    """Outputs a compact, pedagogically rich ASCII summary report."""
    print("\n" + "=" * 78)
    print(" CIMTinyTO PILLAR 5: GATE-LEVEL & VCD-DRIVEN DYNAMIC POWER SIGN-OFF")
    print("=" * 78)

    print(
        f" Operating Envelope : {results['v_dd']:.2f} V Core Supply  |  "
        f"{results['freq_mhz']:.1f} MHz Clock  |  "
        f"{results['clock_cycles']:,} Clock Cycles"
    )
    print(
        f" Netlist Coverage   : {results['matched_nets']:,} / "
        f"{results['total_tracked_nets']:,} Physical Nets Mapped ({results['matched_nets']/max(1, results['total_tracked_nets'])*100:.1f}%)"
    )
    print("-" * 78)

    print(" 1. DYNAMIC SWITCHING POWER BREAKDOWN BY FUNCTIONAL DOMAIN:")
    print(
        f" {'Domain':<28} | {'Cap (fF)':<10} | {'Toggles':<12} | "
        f"{'Power (mW)':<10} | {'% Switch':<8}"
    )
    print(" " + "-" * 76)

    total_switch_mw = max(1e-6, results["total_dyn_switch_mw"])
    for dom, p_mw in results["domain_power_mw"].items():
        cap_ff = results["domain_caps_pf"][dom] * 1000.0
        toggles = results["domain_toggles"][dom]
        pct = (p_mw / total_switch_mw) * 100.0
        print(
            f" {dom:<28} | {cap_ff:>9.1f} | {toggles:>11,} | "
            f"{p_mw:>9.3f} | {pct:>7.1f}%"
        )
    print(" " + "-" * 76)
    print(
        f" {'TOTAL VCD SWITCHING POWER':<28} | {'-':<10} | {'-':<12} | "
        f"{results['total_dyn_switch_mw']:>9.3f} mW | 100.0%"
    )

    print("\n 2. STATIC STA (OpenROAD) VS. WORKLOAD-DRIVEN DYNAMIC POWER COMPARISON:")
    print(
        f" • OpenROAD Static Switching Power (Assumed alpha~0.15) : {results['static_p_switch_mw']:.3f} mW"
    )
    print(
        f" • VCD-Driven Dynamic Switching Power (True Workload)  : {results['total_dyn_switch_mw']:.3f} mW "
        f"({results['switching_power_ratio']*100.0:.1f}% of static)"
    )
    print(
        f" • Internal Cell Dynamic Power (Standard-Cell Gates)   : {results['static_p_internal_mw']:.3f} mW"
    )
    print(
        f" • Sub-Threshold Leakage Power                         : {results['static_p_leak_nw']:.2f} nW"
    )
    print(
        f" • TOTAL ACCELERATOR ACTIVE POWER                      : {results['total_workload_power_mw']:.3f} mW"
    )

    print("\n 3. COMPUTATIONAL ENERGY EFFICIENCY (WORKLOAD MAC SIGN-OFF):")
    print(
        f" • 16x16 MVM Duration (256 cycles @ 50 MHz)             : 5.12 us"
    )
    print(
        f" • Dynamic Energy per 16x16 MVM                         : {results['energy_per_mvm_nj']:.2f} nJ"
    )
    print(
        f" • Energy per MAC Operation (256 MACs / MVM)           : {results['energy_per_mac_pj']:.2f} pJ / MAC"
    )
    print(
        f" • Silicon Compute Throughput                           : 50.0 MMAC/s  (195.3 kMVM/s)"
    )

    print("\n 4. TOP 5 HIGH-DYNAMIC-POWER PHYSICAL NETS:")
    print(
        f" {'Net Identifier':<42} | {'Cap (fF)':<10} | {'Toggle Rate':<11} | {'Power (uW)':<10}"
    )
    print(" " + "-" * 76)
    for name, cap_ff, alpha, p_mw in results["top_power_nets"][:5]:
        trunc_name = (name[:39] + "...") if len(name) > 42 else name
        print(
            f" {trunc_name:<42} | {cap_ff:>9.2f} | {alpha:>10.3f} | {p_mw*1000.0:>9.2f}"
        )

    print("=" * 78)
    print(" ✓ PILLAR 5 GATE-LEVEL SWITCHING & DYNAMIC POWER SIGN-OFF: COMPLETE")
    print("=" * 78 + "\n")


def verify_gls_signoff(results: Dict) -> Tuple[bool, List[str]]:
    """Evaluates the 6 formal physical sign-off gates for Pillar 5."""
    checks = []
    all_passed = True

    # Check 1: Physical netlist to SPEF mapping coverage >= 99.0%
    cov_pct = results["matched_nets"] / max(1, results["total_tracked_nets"]) * 100.0
    if cov_pct >= 99.0:
        checks.append(f"[PASS] Netlist-to-SPEF parasitics mapping >= 99.0% (Achieved: {cov_pct:.1f}%)")
    else:
        checks.append(f"[FAIL] Netlist coverage below 99.0%: {cov_pct:.1f}%")
        all_passed = False

    # Check 2: Total accelerator active power <= 5.0 mW
    p_tot = results["total_workload_power_mw"]
    if p_tot <= 5.0:
        checks.append(f"[PASS] Total active core power <= 5.0 mW budget (Measured: {p_tot:.3f} mW)")
    else:
        checks.append(f"[FAIL] Active power exceeds 5.0 mW budget: {p_tot:.3f} mW")
        all_passed = False

    # Check 3: Computational energy efficiency <= 100.0 pJ/MAC
    e_mac = results["energy_per_mac_pj"]
    if e_mac <= 100.0:
        checks.append(f"[PASS] Energy efficiency <= 100.0 pJ/MAC (Achieved: {e_mac:.2f} pJ/MAC)")
    else:
        checks.append(f"[FAIL] Energy per MAC exceeds 100 pJ target: {e_mac:.2f} pJ/MAC")
        all_passed = False

    # Check 4: VCD-driven dynamic switching power <= 1.0 mW
    p_sw = results["total_dyn_switch_mw"]
    if p_sw <= 1.0:
        checks.append(f"[PASS] Workload dynamic switching power <= 1.0 mW (Measured: {p_sw:.3f} mW)")
    else:
        checks.append(f"[FAIL] Dynamic switching power exceeds 1.0 mW: {p_sw:.3f} mW")
        all_passed = False

    # Check 5: Output pad quiescence verified (Power <= 0.005 mW)
    pad_p = results["domain_power_mw"].get("Control & IO Pads", 0.0)
    if pad_p <= 0.005:
        checks.append(f"[PASS] Output pad quiescence verified (Pad switching: {pad_p*1000.0:.2f} µW <= 5.0 µW)")
    else:
        checks.append(f"[FAIL] Excessive pad switching during active operation: {pad_p:.4f} mW")
        all_passed = False

    # Check 6: Workload switching reduction vs. static STA expectation (< 100%)
    ratio_pct = results["switching_power_ratio"] * 100.0
    if ratio_pct < 100.0:
        checks.append(f"[PASS] Workload dynamic power advantage vs. static STA (Achieved: {ratio_pct:.1f}% of static)")
    else:
        checks.append(f"[FAIL] Dynamic power exceeded static estimate: {ratio_pct:.1f}%")
        all_passed = False

    return all_passed, checks


def print_signoff_scorecard(results: Dict):
    """Outputs the formal Pillar 5 sign-off scorecard."""
    passed, checks = verify_gls_signoff(results)
    print("\n" + "=" * 78)
    print(" PILLAR 5 PHYSICAL SIGN-OFF SCORECARD & SILICON GATES")
    print("=" * 78)
    for c in checks:
        print(f" {c}")
    print("-" * 78)
    status_str = "✅ ALL 6 PHYSICAL GATES PASSED (TAPE-OUT READY)" if passed else "❌ SIGN-OFF CRITERIA FAILED"
    print(f" OVERALL VERDICT: {status_str}")
    print("=" * 78 + "\n")
    return passed


def run_self_tests():
    """Validates SPEF and power calculation formulas against mathematical references."""
    print("[TEST] Running self-test suite for gls_power_audit.py...")

    # 1. Test SPEF Name Sanitization
    raw = "\\gen_accumulators[0].u_acc.acc_val[0] "
    clean = SPEFParser._sanitize_name(raw)
    assert clean == "gen_accumulators[0].u_acc.acc_val[0]", f"Sanitize failed: {clean}"

    # 2. Test Power Formula: P = 0.5 * C * V^2 * f * alpha
    cap_f = 100e-15
    v_dd = 1.80
    f_hz = 50e6
    alpha = 0.5
    p_w = 0.5 * cap_f * (v_dd**2) * f_hz * alpha
    p_mw = p_w * 1000.0
    assert abs(p_mw - 0.00405) < 1e-6, f"Math error in power formula: {p_mw}"

    # 3. Test Net Classification
    assert DynamicPowerAuditor._classify_net("clkbuf_0_clk.X") == "Clock Network"
    assert DynamicPowerAuditor._classify_net("u_sng_bank.gen_lfsr[0]") == "SNG LFSR Bank"
    assert DynamicPowerAuditor._classify_net("u_weight_mem.shift[0]") == "Weight Memory (256 DFFs)"
    assert DynamicPowerAuditor._classify_net("u_pe.pe_out") == "PE Array (16x16)"
    assert DynamicPowerAuditor._classify_net("u_col_tree.count[0]") == "Wallace Tree Compressors"
    assert DynamicPowerAuditor._classify_net("gen_accumulators[0].u_acc") == "Accumulators (16x 13-bit)"
    assert DynamicPowerAuditor._classify_net("uo_out[0]") == "Control & IO Pads"

    # 4. Test Sign-off verification logic
    mock_results = {
        "matched_nets": 5779,
        "total_tracked_nets": 5790,
        "total_workload_power_mw": 2.895,
        "energy_per_mac_pj": 57.91,
        "total_dyn_switch_mw": 0.454,
        "domain_power_mw": {"Control & IO Pads": 0.00015},
        "switching_power_ratio": 0.563
    }
    pass_ok, checks = verify_gls_signoff(mock_results)
    assert pass_ok is True, f"Expected mock results to pass, got: {checks}"
    assert len(checks) == 6

    print("[TEST] All self-tests PASSED successfully!")


def main():
    parser = argparse.ArgumentParser(
        description="GLS & VCD-Driven Dynamic Power Audit for CIMTinyTO"
    )
    parser.add_argument(
        "--vcd",
        default="test/tb.vcd",
        help="Path to VCD or FST waveform file (default: test/tb.vcd)",
    )
    parser.add_argument(
        "--spef",
        default="artifacts/tt_submission/tt_submission/tt_um_scim_core.nom.spef",
        help="Path to post-route nominal SPEF (default: tt_um_scim_core.nom.spef)",
    )
    parser.add_argument(
        "--metrics",
        default="gds/metrics.csv",
        help="Path to OpenROAD metrics.csv (default: gds/metrics.csv)",
    )
    parser.add_argument("--v_dd", type=float, default=1.80, help="Core VDD supply voltage (V)")
    parser.add_argument("--freq", type=float, default=50.0, help="Clock frequency (MHz)")
    parser.add_argument("--test", action="store_true", help="Run embedded self-test suite")
    parser.add_argument("--check-signoff", action="store_true", help="Check sign-off gates and exit with non-zero on failure")
    parser.add_argument("--json", help="Path to write output metrics as JSON")

    args = parser.parse_args()

    if args.test:
        run_self_tests()
        sys.exit(0)

    # Resolve default paths relative to repo root if needed
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    spef_path = (
        args.spef
        if os.path.isabs(args.spef)
        else os.path.join(repo_root, args.spef)
    )
    vcd_path = (
        args.vcd
        if os.path.isabs(args.vcd)
        else os.path.join(repo_root, args.vcd)
    )
    metrics_path = (
        args.metrics
        if os.path.isabs(args.metrics)
        else os.path.join(repo_root, args.metrics)
    )

    print(f"[*] Ingesting post-route SPEF parasitics: {spef_path}...")
    spef_parser = SPEFParser(spef_path)
    spef_caps = spef_parser.parse()
    print(
        f"    Loaded {len(spef_caps):,} nets ({spef_parser.total_chip_cap_pf:.2f} pF total chip capacitance)"
    )

    print(f"[*] Streaming & parsing gate-level transitions from: {vcd_path}...")
    vcd_parser = VCDActivityParser(vcd_path)
    vcd_toggles = vcd_parser.parse(clock_period_ns=(1000.0 / args.freq))
    print(
        f"    Tracked {len(vcd_toggles):,} active nets over {vcd_parser.clock_cycles:,} clock cycles "
        f"({vcd_parser.sim_time_ps/1e6:.2f} us)"
    )

    print("[*] Computing cycle-accurate dynamic switching power...")
    auditor = DynamicPowerAuditor(
        spef_caps=spef_caps,
        vcd_toggles=vcd_toggles,
        clock_cycles=vcd_parser.clock_cycles,
        v_dd=args.v_dd,
        freq_mhz=args.freq,
        openroad_metrics_path=metrics_path,
    )
    results = auditor.compute_power_breakdown()

    print_audit_report(results)
    passed = print_signoff_scorecard(results)

    if args.json:
        out_data = {
            "v_dd": results["v_dd"],
            "freq_mhz": results["freq_mhz"],
            "clock_cycles": results["clock_cycles"],
            "total_dyn_switch_mw": results["total_dyn_switch_mw"],
            "static_p_switch_mw": results["static_p_switch_mw"],
            "total_workload_power_mw": results["total_workload_power_mw"],
            "energy_per_mvm_nj": results["energy_per_mvm_nj"],
            "energy_per_mac_pj": results["energy_per_mac_pj"],
            "domain_power_mw": results["domain_power_mw"],
            "signoff_passed": passed
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2)
        print(f"[+] Output JSON written to: {args.json}")

    if args.check_signoff and not passed:
        print("[ERROR] One or more Pillar 5 sign-off criteria failed!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

